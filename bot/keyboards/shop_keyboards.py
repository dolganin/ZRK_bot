from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def shop_item_kb(
    idx: int,
    product_id: int,
    qty: int = 0,
    cart_qty: int = 0,
):
    qty = int(qty or 0)
    cart_qty = int(cart_qty or 0)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖", callback_data=f"shop:rm:{product_id}:{idx}"),
                InlineKeyboardButton(text=f"{qty}", callback_data="shop:noop"),
                InlineKeyboardButton(text="➕", callback_data=f"shop:add:{product_id}:{idx}"),
            ],
            [
                InlineKeyboardButton(text=f"🧾 Корзина ({cart_qty})", callback_data="shop:cart"),
            ],
            [
                InlineKeyboardButton(text="⬅️", callback_data=f"shop:prev:{idx}"),
                InlineKeyboardButton(text="➡️", callback_data=f"shop:next:{idx}"),
            ],
        ]
    )


def shop_cart_kb(total_items: int = 0):
    total_items = int(total_items or 0)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Оформить ({total_items})", callback_data="shop:checkout")],
            [InlineKeyboardButton(text="⬅️ Назад в магазин", callback_data="shop:open:0")],
        ]
    )
