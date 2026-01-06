from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def shop_item_kb(idx: int, product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖", callback_data=f"shop:rm:{product_id}:{idx}"),
                InlineKeyboardButton(text="➕", callback_data=f"shop:add:{product_id}:{idx}")
            ],
            [
                InlineKeyboardButton(text="🧾 Корзина", callback_data="shop:cart")
            ],
            [
                InlineKeyboardButton(text="⬅️", callback_data=f"shop:prev:{idx}"),
                InlineKeyboardButton(text="➡️", callback_data=f"shop:next:{idx}")
            ]
        ]
    )

def shop_cart_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оформить", callback_data="shop:checkout")],
            [InlineKeyboardButton(text="⬅️ Назад в магазин", callback_data="shop:open:0")]
        ]
    )
