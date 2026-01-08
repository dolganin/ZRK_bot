from aiogram import Router, types, F
from aiogram.filters import Command

from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu
from utils.database import is_admin, get_db

router = Router()

BTN_TEXT = "📦 Отчёт по складу"


async def ensure_admin(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return False
    return True


@router.message(Command("inventory"))
async def inventory_cmd(message: types.Message):
    if not await ensure_admin(message):
        return
    await _send_inventory_report(message)


@router.message(F.text == BTN_TEXT)
async def inventory_btn(message: types.Message):
    if not await ensure_admin(message):
        return
    await _send_inventory_report(message)


async def _send_inventory_report(message: types.Message):
    pool = await get_db()
    async with pool.acquire() as conn:
        products = await conn.fetch(
            """
            SELECT
                p.id,
                p.name,
                p.price_points,
                p.stock,
                p.is_active,
                COALESCE(r.reserved_qty, 0) AS reserved_qty,
                COALESCE(f.fulfilled_qty, 0) AS fulfilled_qty
            FROM products p
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.qty)::int AS reserved_qty
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'RESERVED'
                GROUP BY oi.product_id
            ) r ON r.product_id = p.id
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.qty)::int AS fulfilled_qty
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'FULFILLED'
                GROUP BY oi.product_id
            ) f ON f.product_id = p.id
            ORDER BY p.id ASC
            """
        )

        reserved_orders = await conn.fetch(
            """
            SELECT id, user_id, total_points, created_at
            FROM orders
            WHERE status = 'RESERVED'
            ORDER BY created_at DESC
            LIMIT 15
            """
        )

        reserved_total_qty = await conn.fetchval(
            """
            SELECT COALESCE(SUM(oi.qty), 0)
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'RESERVED'
            """
        )
        reserved_total_qty = int(reserved_total_qty or 0)

    lines = []
    lines.append("📦 Склад / отчёт")
    lines.append("")
    lines.append("Товары (на складе / зарезервировано / выдано):")

    if not products:
        lines.append("— товаров нет")
    else:
        for p in products:
            pid = int(p["id"])
            name = str(p["name"])
            pe = int(p["price_points"])
            stock = int(p["stock"] or 0)
            active = bool(p["is_active"])
            reserved = int(p["reserved_qty"] or 0)
            fulfilled = int(p["fulfilled_qty"] or 0)

            status_badge = "✅" if active else "⛔️"
            lines.append(
                f"{status_badge} {pid}. {name} — {pe} балл.\n"
                f"   📦 склад: {stock} | 🧷 резерв: {reserved} | ✅ выдано: {fulfilled}"
            )

    lines.append("")
    lines.append(f"🧷 Всего зарезервировано (шт.): {reserved_total_qty}")

    lines.append("")
    lines.append("⏳ Последние заказы в RESERVED (ждут выдачи):")
    if not reserved_orders:
        lines.append("— нет")
    else:
        for o in reserved_orders:
            lines.append(f"• #{int(o['id'])} | user {int(o['user_id'])} | сумма {int(o['total_points'] or 0)} | {o['created_at']}")

    lines.append("")
    lines.append("ℹ️ Примечание: 'выдано' считается по заказам со статусом FULFILLED и qty из order_items.")

    await message.answer("\n".join(lines), reply_markup=organizer_menu())
