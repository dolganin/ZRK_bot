from utils.database import get_db
from typing import Any

async def seed_products_if_empty():
    pool = await get_db()
    async with pool.acquire() as conn:
        n = await conn.fetchval("SELECT COUNT(*) FROM products")
        if n and n > 0:
            return
        await conn.execute(
            """
            INSERT INTO products(name, price_points, stock, is_active)
            VALUES
            ('Носки', 50, 100, TRUE),
            ('Трусы', 80, 50, TRUE),
            ('Пижама', 200, 20, TRUE);
            """
        )

async def get_products():
    pool = await get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, price_points, stock FROM products WHERE is_active = TRUE AND stock > 0 ORDER BY id ASC"
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
            row = await conn.fetchrow(
                """
                SELECT price_points, stock
                FROM products
                WHERE id = $1 AND is_active = TRUE
                FOR UPDATE
                """,
                product_id
            )
            if not row:
                return {"ok": False, "reason": "not_found"}

            current_qty = await conn.fetchval(
                "SELECT qty FROM order_items WHERE order_id = $1 AND product_id = $2",
                order_id, product_id
            )
            current_qty = int(current_qty or 0)
            stock = int(row["stock"] or 0)
            if current_qty >= stock:
                return {"ok": False, "reason": "out_of_stock"}

            await conn.execute(
                """
                INSERT INTO order_items(order_id, product_id, qty, points_each)
                VALUES ($1, $2, 1, $3)
                ON CONFLICT (order_id, product_id)
                DO UPDATE SET qty = order_items.qty + 1
                """,
                order_id, product_id, int(row["price_points"])
            )

            return {"ok": True}


async def remove_item(order_id: int, product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            qty = await conn.fetchval(
                "SELECT qty FROM order_items WHERE order_id = $1 AND product_id = $2 FOR UPDATE",
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
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            already = await conn.fetchval(
                """
                SELECT id
                FROM orders
                WHERE user_id = $1 AND status IN ('RESERVED', 'CHECKED_OUT')
                ORDER BY id DESC
                LIMIT 1
                FOR UPDATE
                """,
                user_id
            )
            if already:
                return {"ok": False, "reason": "already_checked_out"}

            order_id = await conn.fetchval(
                "SELECT id FROM orders WHERE user_id = $1 AND status = 'DRAFT' ORDER BY id DESC LIMIT 1 FOR UPDATE",
                user_id
            )
            if not order_id:
                return {"ok": False, "reason": "no_draft"}

            items = await conn.fetch(
                """
                SELECT oi.product_id, oi.qty, oi.points_each, p.name
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = $1
                ORDER BY oi.product_id ASC
                FOR UPDATE
                """,
                int(order_id)
            )
            if not items:
                return {"ok": False, "reason": "empty"}

            total = sum(int(it["qty"]) * int(it["points_each"]) for it in items)
            if total <= 0:
                return {"ok": False, "reason": "empty"}

            balance = await conn.fetchval(
                "SELECT balance FROM students WHERE id = $1 FOR UPDATE",
                user_id
            )
            balance = int(balance or 0)
            if balance < total:
                return {"ok": False, "reason": "not_enough", "need": int(total), "balance": int(balance)}

            lacking = []
            for it in items:
                pid = int(it["product_id"])
                need = int(it["qty"])
                have = await conn.fetchval(
                    "SELECT stock FROM products WHERE id = $1 AND is_active = TRUE FOR UPDATE",
                    pid
                )
                have = int(have or 0)
                if have < need:
                    lacking.append({"product_id": pid, "name": it["name"], "need": need, "have": have})

            if lacking:
                return {"ok": False, "reason": "out_of_stock", "items": lacking}

            for it in items:
                pid = int(it["product_id"])
                need = int(it["qty"])
                await conn.execute(
                    "UPDATE products SET stock = stock - $1 WHERE id = $2",
                    need, pid
                )

            await conn.execute(
            """
            UPDATE orders
            SET status = 'RESERVED',
                total_points = $1,
                reserved_until = NOW() + INTERVAL '1 hour'
            WHERE id = $2
            """,
            int(total), int(order_id)
)

            return {"ok": True, "order_id": int(order_id), "total": int(total)}


async def create_product(name: str, price_points: int, stock: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO products(name, price_points, stock, is_active) VALUES ($1, $2, $3, TRUE) RETURNING id",
            name.strip(), int(price_points), int(stock)
        )

async def list_products(include_inactive: bool = False):
    pool = await get_db()
    async with pool.acquire() as conn:
        if include_inactive:
            rows = await conn.fetch(
                "SELECT id, name, price_points, stock, is_active FROM products ORDER BY id ASC"
            )
        else:
            rows = await conn.fetch(
                "SELECT id, name, price_points, stock, is_active FROM products WHERE is_active = TRUE ORDER BY id ASC"
            )
        return [dict(r) for r in rows]


async def set_product_active(product_id: int, is_active: bool):
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE products SET is_active = $1 WHERE id = $2",
            bool(is_active), int(product_id)
        )

async def set_product_main_image(product_id: int, telegram_file_id: str, telegram_file_unique_id: str, storage_path: str = None, mime: str = None, size_bytes: int = None, width: int = None, height: int = None):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE product_images SET is_main = FALSE WHERE product_id = $1",
                int(product_id)
            )
            await conn.fetchval(
                """
                INSERT INTO product_images(product_id, telegram_file_id, telegram_file_unique_id, storage_path, mime, size_bytes, width, height, is_main)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,TRUE)
                RETURNING id
                """,
                int(product_id),
                telegram_file_id,
                telegram_file_unique_id,
                storage_path,
                mime,
                size_bytes,
                width,
                height
            )

async def get_product_main_image(product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT telegram_file_id, storage_path
            FROM product_images
            WHERE product_id = $1 AND is_main = TRUE
            ORDER BY id DESC
            LIMIT 1
            """,
            int(product_id)
        )
        return dict(row) if row else None


async def set_product_main_image(
    product_id: int,
    telegram_file_id: str,
    telegram_file_unique_id: str,
    storage_path: str | None = None,
    mime: str | None = None,
    size_bytes: int | None = None,
    width: int | None = None,
    height: int | None = None,
):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE product_images SET is_main = FALSE WHERE product_id = $1",
                int(product_id)
            )

            await conn.execute(
                """
                INSERT INTO product_images(
                    product_id,
                    telegram_file_id,
                    telegram_file_unique_id,
                    storage_path,
                    mime,
                    size_bytes,
                    width,
                    height,
                    is_main
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,TRUE)
                """,
                int(product_id),
                telegram_file_id,
                telegram_file_unique_id,
                storage_path,
                mime,
                size_bytes,
                width,
                height
            )

async def update_product(product_id: int, name: str | None = None, price_points: int | None = None, stock: int | None = None):
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE products
            SET
              name = COALESCE($2, name),
              price_points = COALESCE($3, price_points),
              stock = COALESCE($4, stock)
            WHERE id = $1
            """,
            int(product_id),
            name.strip() if name is not None else None,
            int(price_points) if price_points is not None else None,
            int(stock) if stock is not None else None
        )

async def get_product(product_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price_points, stock, is_active FROM products WHERE id = $1",
            int(product_id)
        )
        return dict(row) if row else None

async def fulfill_order_by_admin(order_id: int, admin_id: int) -> dict[str, Any]:
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            order = await conn.fetchrow(
                """
                SELECT id, user_id, status, total_points, fulfilled_at
                FROM orders
                WHERE id = $1
                FOR UPDATE
                """,
                int(order_id)
            )
            if not order:
                return {"ok": False, "reason": "not_found"}

            status = order["status"]
            if status == "FULFILLED":
                return {"ok": False, "reason": "already_fulfilled"}
            if status != "CHECKED_OUT":
                return {"ok": False, "reason": "bad_status", "status": status}

            user_id = int(order["user_id"])

            items = await conn.fetch(
                """
                SELECT oi.product_id, oi.qty, oi.points_each, p.name
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = $1
                ORDER BY oi.product_id ASC
                FOR UPDATE
                """,
                int(order_id)
            )
            if not items:
                return {"ok": False, "reason": "empty"}

            total = await conn.fetchval(
                "SELECT COALESCE(SUM(qty * points_each), 0) FROM order_items WHERE order_id = $1",
                int(order_id)
            )
            total = int(total or 0)
            if total <= 0:
                return {"ok": False, "reason": "empty"}

            balance = await conn.fetchval(
                "SELECT balance FROM students WHERE id = $1 FOR UPDATE",
                user_id
            )
            balance = int(balance or 0)
            if balance < total:
                return {"ok": False, "reason": "not_enough", "need": total, "balance": balance}

            lacking = []
            for it in items:
                pid = int(it["product_id"])
                need = int(it["qty"])
                have = await conn.fetchval(
                    "SELECT stock FROM products WHERE id = $1 FOR UPDATE",
                    pid
                )
                have = int(have or 0)
                if have < need:
                    lacking.append({"product_id": pid, "name": it["name"], "need": need, "have": have})

            if lacking:
                return {"ok": False, "reason": "out_of_stock", "items": lacking}

            for it in items:
                pid = int(it["product_id"])
                need = int(it["qty"])
                await conn.execute(
                    "UPDATE products SET stock = stock - $1 WHERE id = $2",
                    need, pid
                )

            await conn.execute(
                "UPDATE students SET balance = balance - $1 WHERE id = $2",
                total, user_id
            )

            await conn.execute(
                """
                UPDATE orders
                SET status = 'FULFILLED',
                    fulfilled_at = NOW(),
                    fulfilled_by = $2,
                    total_points = $3
                WHERE id = $1
                """,
                int(order_id), int(admin_id), total
            )

            new_balance = balance - total
            return {"ok": True, "user_id": user_id, "total": total, "new_balance": new_balance}
        
async def get_cart_qty(order_id: int) -> int:
    pool = await get_db()
    async with pool.acquire() as conn:
        v = await conn.fetchval(
            "SELECT COALESCE(SUM(qty), 0) FROM order_items WHERE order_id = $1",
            int(order_id)
        )
        return int(v or 0)

from typing import Any

async def get_order_for_issue(order_id: int) -> dict[str, Any]:
    pool = await get_db()
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            """
            SELECT id, user_id, status
            FROM orders
            WHERE id = $1
            """,
            int(order_id)
        )
        if not order:
            return {"ok": False, "reason": "not_found"}

        status = str(order["status"])
        if status == "FULFILLED":
            return {"ok": False, "reason": "already_fulfilled"}
        if status not in {"RESERVED", "CHECKED_OUT"}:
            return {"ok": False, "reason": "bad_status", "status": status}

        items = await conn.fetch(
            """
            SELECT oi.product_id, oi.qty, oi.points_each, p.name
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = $1
            ORDER BY oi.product_id ASC
            """,
            int(order_id)
        )
        if not items:
            return {"ok": False, "reason": "empty"}

        return {
            "ok": True,
            "order": {"order_id": int(order["id"]), "user_id": int(order["user_id"]), "status": status},
            "items": [dict(x) for x in items]
        }


async def issue_order_by_admin(order_id: int, admin_id: int, issued_qty: dict[int, int]) -> dict[str, Any]:
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            order = await conn.fetchrow(
                """
                SELECT id, user_id, status
                FROM orders
                WHERE id = $1
                FOR UPDATE
                """,
                int(order_id)
            )
            if not order:
                return {"ok": False, "reason": "not_found"}

            status = str(order["status"])
            if status == "FULFILLED":
                return {"ok": False, "reason": "already_fulfilled"}
            if status not in {"RESERVED", "CHECKED_OUT"}:
                return {"ok": False, "reason": "bad_status", "status": status}

            user_id = int(order["user_id"])

            items = await conn.fetch(
                """
                SELECT oi.product_id, oi.qty, oi.points_each, p.name
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id = $1
                ORDER BY oi.product_id ASC
                FOR UPDATE
                """,
                int(order_id)
            )
            if not items:
                return {"ok": False, "reason": "empty"}

            normalized = {}
            for it in items:
                pid = int(it["product_id"])
                q_ordered = int(it["qty"])
                qi = int(issued_qty.get(pid, q_ordered))
                if qi < 0:
                    qi = 0
                if qi > q_ordered:
                    qi = q_ordered
                normalized[pid] = qi

            total = 0
            for it in items:
                pid = int(it["product_id"])
                total += int(it["points_each"]) * int(normalized[pid])

            if total <= 0:
                if status == "RESERVED":
                    for it in items:
                        pid = int(it["product_id"])
                        q_ordered = int(it["qty"])
                        if q_ordered > 0:
                            await conn.execute(
                                "UPDATE products SET stock = stock + $1 WHERE id = $2",
                                q_ordered, pid
                            )
                await conn.execute(
                    """
                    UPDATE orders
                    SET status = 'FULFILLED',
                        fulfilled_at = NOW(),
                        fulfilled_by = $2,
                        total_points = 0
                    WHERE id = $1
                    """,
                    int(order_id), int(admin_id)
                )
                balance = await conn.fetchval("SELECT balance FROM students WHERE id = $1", user_id)
                return {"ok": False, "reason": "nothing_to_issue", "balance": int(balance or 0)}

            if status == "CHECKED_OUT":
                lacking = []
                for it in items:
                    pid = int(it["product_id"])
                    need = int(normalized[pid])
                    if need <= 0:
                        continue
                    have = await conn.fetchval("SELECT stock FROM products WHERE id = $1 FOR UPDATE", pid)
                    have = int(have or 0)
                    if have < need:
                        lacking.append({"product_id": pid, "name": it["name"], "need": need, "have": have})
                if lacking:
                    return {"ok": False, "reason": "out_of_stock", "items": lacking}

                for it in items:
                    pid = int(it["product_id"])
                    need = int(normalized[pid])
                    if need > 0:
                        await conn.execute("UPDATE products SET stock = stock - $1 WHERE id = $2", need, pid)

            if status == "RESERVED":
                for it in items:
                    pid = int(it["product_id"])
                    q_ordered = int(it["qty"])
                    q_issue = int(normalized[pid])
                    diff = q_ordered - q_issue
                    if diff > 0:
                        await conn.execute("UPDATE products SET stock = stock + $1 WHERE id = $2", diff, pid)

            balance = await conn.fetchval(
                "SELECT balance FROM students WHERE id = $1 FOR UPDATE",
                user_id
            )
            balance = int(balance or 0)
            if balance < total:
                return {"ok": False, "reason": "not_enough", "need": total, "balance": balance}

            await conn.execute(
                "UPDATE students SET balance = balance - $1 WHERE id = $2",
                int(total), int(user_id)
            )

            await conn.execute(
                """
                UPDATE orders
                SET status = 'FULFILLED',
                    fulfilled_at = NOW(),
                    fulfilled_by = $2,
                    total_points = $3
                WHERE id = $1
                """,
                int(order_id), int(admin_id), int(total)
            )

            return {"ok": True, "user_id": user_id, "total": int(total), "new_balance": balance - int(total)}

async def get_active_order_id(user_id: int):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT id
            FROM orders
            WHERE user_id = $1 AND status IN ('RESERVED', 'CHECKED_OUT')
            ORDER BY id DESC
            LIMIT 1
            """,
            user_id
        )


async def expire_orders(limit: int = 50) -> int:
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            order_ids = await conn.fetch(
                """
                SELECT id
                FROM orders
                WHERE status IN ('RESERVED', 'CHECKED_OUT')
                  AND reserved_until IS NOT NULL
                  AND reserved_until < NOW()
                ORDER BY reserved_until ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
                """,
                int(limit)
            )

            expired = 0
            for r in order_ids:
                oid = int(r["id"])

                items = await conn.fetch(
                    """
                    SELECT product_id, qty
                    FROM order_items
                    WHERE order_id = $1
                    FOR UPDATE
                    """,
                    oid
                )

                for it in items:
                    pid = int(it["product_id"])
                    q = int(it["qty"])
                    if q > 0:
                        await conn.execute(
                            "UPDATE products SET stock = stock + $1 WHERE id = $2",
                            q, pid
                        )

                await conn.execute("DELETE FROM order_items WHERE order_id = $1", oid)
                await conn.execute("DELETE FROM orders WHERE id = $1", oid)
                expired += 1

            return expired
