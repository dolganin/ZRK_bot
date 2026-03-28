from aiogram import Router, types, F
from aiogram.filters import Command

from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu, ADMIN_PANEL_TEXT
from utils.database import is_admin, get_db

router = Router()

BTN_TEXT = "📦 Отчёт по складу"
INVENTORY_PAGE_LIMIT = 3200


async def ensure_admin(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return False
    return True


async def ensure_admin_cb(call: types.CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return False
    return True


def _inventory_kb(page: int, total_pages: int):
    rows = []
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"org:inventory:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"org:inventory:page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([types.InlineKeyboardButton(text="⬅️ В панель", callback_data="org:inventory:back")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _paginate_inventory_blocks(blocks: list[str]) -> list[str]:
    pages: list[str] = []
    current = ""

    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) <= INVENTORY_PAGE_LIMIT:
            current = candidate
            continue

        if current:
            pages.append(current)
            current = block
            continue

        pages.append(block[:INVENTORY_PAGE_LIMIT])
        current = block[INVENTORY_PAGE_LIMIT:]

    if current:
        pages.append(current)

    return pages or ["📦 Склад / отчёт\n\n— данных нет"]


@router.message(Command("inventory"))
async def inventory_cmd(message: types.Message):
    if not await ensure_admin(message):
        return
    await _open_inventory_report(message)


@router.message(F.text == BTN_TEXT)
async def inventory_btn(message: types.Message):
    if not await ensure_admin(message):
        return
    await _open_inventory_report(message)


async def _build_inventory_pages() -> list[str]:
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

    blocks = [
        "📦 Склад / отчёт",
        f"🧷 Всего зарезервировано (шт.): {reserved_total_qty}",
        "Товары (на складе / зарезервировано / выдано):",
    ]

    if not products:
        blocks.append("— товаров нет")
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
            blocks.append(
                f"{status_badge} {pid}. {name} — {pe} балл.\n"
                f"   📦 склад: {stock} | 🧷 резерв: {reserved} | ✅ выдано: {fulfilled}"
            )

    blocks.append("⏳ Последние заказы в RESERVED (ждут выдачи):")
    if not reserved_orders:
        blocks.append("— нет")
    else:
        for o in reserved_orders:
            blocks.append(
                f"• #{int(o['id'])} | user {int(o['user_id'])} | "
                f"сумма {int(o['total_points'] or 0)} | {o['created_at']}"
            )

    blocks.append("ℹ️ Примечание: 'выдано' считается по заказам со статусом FULFILLED и qty из order_items.")
    pages = _paginate_inventory_blocks(blocks)
    total_pages = len(pages)
    return [
        f"{page_text}\n\nСтраница {idx + 1}/{total_pages}"
        for idx, page_text in enumerate(pages)
    ]


async def _open_inventory_report(message: types.Message):
    pages = await _build_inventory_pages()
    await message.answer(
        pages[0],
        reply_markup=_inventory_kb(page=0, total_pages=len(pages)),
    )


@router.callback_query(F.data.startswith("org:inventory:page:"))
async def inventory_page(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return

    pages = await _build_inventory_pages()
    page = int(call.data.split(":")[-1])
    page = max(0, min(page, len(pages) - 1))
    await call.message.edit_text(
        pages[page],
        reply_markup=_inventory_kb(page=page, total_pages=len(pages)),
    )
    await call.answer()


@router.callback_query(F.data == "org:inventory:back")
async def inventory_back(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return

    await call.message.edit_text("Возврат в панель организатора.", reply_markup=None)
    await call.message.answer(ADMIN_PANEL_TEXT, reply_markup=organizer_menu())
    await call.answer()
