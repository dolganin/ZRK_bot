from utils.database import get_db, get_balance

async def seed_products_if_empty():
    pool = await get_db()
    async with pool.acquire() as conn:
        n = await conn.fetchval("SELECT COUNT(*) FROM products")
        if n and n > 0:
            return
        await conn.execute(
            """
            INSERT INTO products(name, price_points, is_active)
            VALUES
                ('Носки', 50, TRUE),
                ('Трусы', 80, TRUE),
                ('Пижама', 200, TRUE)
            """
        )

async def get_products():
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, price_points FROM products WHERE is_active = TRUE ORDER BY id ASC"
        )
        return [dict(r) for r in rows]

async def get_checked_out_order_id(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT id FROM orders WHERE user_id = $1 AND status = 'CHECKED_OUT' ORDER BY id DESC LIMIT 1",
            user_id
        )

async def get_or_create_draft_order(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM orders WHERE user_id = $1 AND status = 'DRAFT' ORDER BY id DESC LIMIT 1",
            user_id
        )
        if existing:
            return existing
        return await conn.fetchval(
            "INSERT INTO orders(user_id, status, total_points) VALUES ($1, 'DRAFT', 0) RETURNING id",
            user_id
        )

async def get_item_qty(order_id: int, product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        qty = await conn.fetchval(
            "SELECT qty FROM order_items WHERE order_id = $1 AND product_id = $2",
            order_id, product_id
        )
        return qty or 0

async def add_item(order_id: int, product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            price = await conn.fetchval(
                "SELECT price_points FROM products WHERE id = $1 AND is_active = TRUE",
                product_id
            )
            if price is None:
                return False
            await conn.execute(
                """
                INSERT INTO order_items(order_id, product_id, qty, points_each)
                VALUES ($1, $2, 1, $3)
                ON CONFLICT (order_id, product_id)
                DO UPDATE SET qty = order_items.qty + 1
                """,
                order_id, product_id, price
            )
            return True

async def remove_item(order_id: int, product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            qty = await conn.fetchval(
                "SELECT qty FROM order_items WHERE order_id = $1 AND product_id = $2",
                order_id, product_id
            )
            if qty is None:
                return True
            if qty <= 1:
                await conn.execute(
                    "DELETE FROM order_items WHERE order_id = $1 AND product_id = $2",
                    order_id, product_id
                )
                return True
            await conn.execute(
                "UPDATE order_items SET qty = qty - 1 WHERE order_id = $1 AND product_id = $2",
                order_id, product_id
            )
            return True

async def get_order_items(order_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.name, oi.product_id, oi.qty, oi.points_each, (oi.qty * oi.points_each) AS subtotal
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = $1
            ORDER BY p.id ASC
            """,
            order_id
        )
        return [dict(r) for r in rows]

async def calc_order_total(order_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COALESCE(SUM(qty * points_each), 0) FROM order_items WHERE order_id = $1",
            order_id
        )
        return int(total or 0)

async def checkout_order(user_id: int):
    checked_out_id = await get_checked_out_order_id(user_id)
    if checked_out_id:
        return {"ok": False, "reason": "already_checked_out"}

    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            order_id = await conn.fetchval(
                "SELECT id FROM orders WHERE user_id = $1 AND status = 'DRAFT' ORDER BY id DESC LIMIT 1",
                user_id
            )
            if not order_id:
                return {"ok": False, "reason": "no_draft"}

            total = await conn.fetchval(
                "SELECT COALESCE(SUM(qty * points_each), 0) FROM order_items WHERE order_id = $1",
                order_id
            )
            total = int(total or 0)
            if total <= 0:
                return {"ok": False, "reason": "empty"}

            balance = await conn.fetchval("SELECT balance FROM students WHERE id = $1", user_id)
            balance = int(balance or 0)
            if balance < total:
                return {"ok": False, "reason": "not_enough", "need": total, "balance": balance}

            await conn.execute(
                "UPDATE students SET balance = balance - $1 WHERE id = $2",
                total, user_id
            )
            await conn.execute(
                "UPDATE orders SET status = 'CHECKED_OUT', total_points = $1 WHERE id = $2",
                total, order_id
            )
            new_balance = balance - total
            return {"ok": True, "order_id": order_id, "total": total, "balance": new_balance}

async def create_product(name: str, price_points: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO products(name, price_points, is_active) VALUES ($1, $2, TRUE) RETURNING id",
            name.strip(), int(price_points)
        )

async def list_products(include_inactive: bool = False):
    pool = await get_db()
    async with pool.acquire() as conn:
        if include_inactive:
            rows = await conn.fetch(
                "SELECT id, name, price_points, is_active FROM products ORDER BY id ASC"
            )
        else:
            rows = await conn.fetch(
                "SELECT id, name, price_points, is_active FROM products WHERE is_active = TRUE ORDER BY id ASC"
            )
        return [dict(r) for r in rows]

async def set_product_active(product_id: int, is_active: bool):
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE products SET is_active = $1 WHERE id = $2",
            bool(is_active), int(product_id)
        )
