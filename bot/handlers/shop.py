from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto
from keyboards.student_keyboards import main_menu
from keyboards.shop_keyboards import shop_item_kb, shop_cart_kb
from utils.shop_db import (
    get_products,
    get_or_create_draft_order,
    add_item,
    remove_item,
    get_item_qty,
    get_order_items,
    calc_order_total,
    checkout_order,
    get_checked_out_order_id, get_product_main_image, get_active_order_id
)
from utils.database import get_balance
from utils.shop_db import get_cart_qty

router = Router()

def render_product_text(product, qty_in_cart: int, balance: int, idx: int, total_count: int):
    return (
        f"🛍 Магазин ({idx+1}/{total_count})\n\n"
        f"📦 Товар: {product['name']}\n"
        f"💰 Цена: {product['price_points']} баллов\n"
        f"🧺 В корзине: {qty_in_cart}\n\n"
        f"💳 Твой баланс: {balance}"
        f"📦 Остаток: {product['stock']}\n"
    )

def render_cart_text(items, total: int, balance: int):
    if not items:
        return f"🧾 Корзина пуста\n\n💳 Твой баланс: {balance}"
    lines = ["🧾 Корзина\n"]
    for it in items:
        lines.append(f"• {it['name']} × {it['qty']} = {it['subtotal']} баллов")
    lines.append(f"\nИтого: {total} баллов")
    lines.append(f"💳 Твой баланс: {balance}")
    return "\n".join(lines)

async def upsert_product_message(call_or_msg, text: str, kb, photo_file_id: str | None):
    if isinstance(call_or_msg, types.CallbackQuery):
        m = call_or_msg.message

        want_photo = bool(photo_file_id)
        have_photo = bool(getattr(m, "photo", None))

        if want_photo and have_photo:
            await m.edit_media(
                media=InputMediaPhoto(media=photo_file_id, caption=text),
                reply_markup=kb
            )
            await call_or_msg.answer()
            return

        if (not want_photo) and (not have_photo):
            await m.edit_text(text, reply_markup=kb)
            await call_or_msg.answer()
            return

        try:
            await m.delete()
        except Exception:
            pass

        if want_photo:
            await m.answer_photo(photo=photo_file_id, caption=text, reply_markup=kb)
        else:
            await m.answer(text, reply_markup=kb)

        await call_or_msg.answer()
        return

    if photo_file_id:
        await call_or_msg.answer_photo(photo=photo_file_id, caption=text, reply_markup=kb)
    else:
        await call_or_msg.answer(text, reply_markup=kb)


async def show_product(message_or_call, user_id: int, idx: int):
    products = await get_products()
    if not products:
        text = "🛍 Магазин пока пуст"
        if isinstance(message_or_call, types.CallbackQuery):
            await upsert_product_message(message_or_call, text, None, None)
        else:
            await message_or_call.answer(text, reply_markup=main_menu())
        return

    idx = idx % len(products)
    product = products[idx]

    checked_out = await get_checked_out_order_id(user_id)
    if checked_out:
        text = "✅ У тебя уже есть оформленный заказ. Дождись выдачи мерча у организаторов."
        if isinstance(message_or_call, types.CallbackQuery):
            await message_or_call.answer(text, show_alert=True)
        else:
            await message_or_call.answer(text, reply_markup=main_menu())
        return

    order_id = await get_or_create_draft_order(user_id)
    qty = await get_item_qty(order_id, product["id"])
    cart_qty = await get_cart_qty(order_id)
    balance = await get_balance(user_id)

    text = render_product_text(product, qty, balance, idx, len(products))
    kb = shop_item_kb(idx=idx, product_id=product["id"], qty=qty, cart_qty=cart_qty)

    img = await get_product_main_image(product["id"])
    photo_file_id = img["telegram_file_id"] if img else None

    await upsert_product_message(message_or_call, text, kb, photo_file_id)

@router.message(lambda m: m.text == "🛍 Магазин")
async def shop_open(message: types.Message):
    await show_product(message, message.from_user.id, 0)

@router.callback_query(lambda c: c.data.startswith("shop:open:"))
async def shop_open_cb(call: types.CallbackQuery):
    idx = int(call.data.split(":")[2])
    await show_product(call, call.from_user.id, idx)

@router.callback_query(lambda c: c.data.startswith("shop:next:"))
async def shop_next(call: types.CallbackQuery):
    idx = int(call.data.split(":")[2])
    await show_product(call, call.from_user.id, idx + 1)

@router.callback_query(lambda c: c.data.startswith("shop:prev:"))
async def shop_prev(call: types.CallbackQuery):
    idx = int(call.data.split(":")[2])
    await show_product(call, call.from_user.id, idx)

@router.callback_query(lambda c: c.data.startswith("shop:add:"))
async def shop_add(call: types.CallbackQuery):
    _, _, product_id, idx = call.data.split(":")
    product_id = int(product_id)
    idx = int(idx)

    checked_out = await get_checked_out_order_id(call.from_user.id)
    if checked_out:
        await call.answer("У тебя уже есть оформленный заказ. Дождись выдачи.", show_alert=True)
        return

    order_id = await get_or_create_draft_order(call.from_user.id)
    res = await add_item(order_id, product_id)
    if not res["ok"]:
        if res.get("reason") == "out_of_stock":
            await call.answer("Товар закончился", show_alert=True)
            return
        await call.answer("Товар недоступен", show_alert=True)
        return

    await show_product(call, call.from_user.id, idx)
    await call.answer()


@router.callback_query(lambda c: c.data.startswith("shop:rm:"))
async def shop_rm(call: types.CallbackQuery):
    _, _, product_id, idx = call.data.split(":")
    product_id = int(product_id)
    idx = int(idx)

    checked_out = await get_checked_out_order_id(call.from_user.id)
    if checked_out:
        await call.answer("У тебя уже есть оформленный заказ. Дождись выдачи.", show_alert=True)
        return

    order_id = await get_or_create_draft_order(call.from_user.id)
    await remove_item(order_id, product_id)
    await show_product(call, call.from_user.id, idx)

@router.callback_query(lambda c: c.data == "shop:cart")
async def shop_cart(call: types.CallbackQuery):
    checked_out = await get_checked_out_order_id(call.from_user.id)
    if checked_out:
        await call.answer("У тебя уже есть оформленный заказ. Дождись выдачи.", show_alert=True)
        return

    order_id = await get_or_create_draft_order(call.from_user.id)
    items = await get_order_items(order_id)
    total = await calc_order_total(order_id)
    balance = await get_balance(call.from_user.id)

    total_items = sum(int(it["qty"]) for it in items) if items else 0

    text = render_cart_text(items, total, balance)
    await call.message.edit_text(text, reply_markup=shop_cart_kb(total_items=total_items))
    await call.answer()


@router.callback_query(lambda c: c.data == "shop:checkout")
async def shop_checkout(call: types.CallbackQuery):
    checked_out = await get_checked_out_order_id(call.from_user.id)
    if checked_out:
        await call.answer("У тебя уже есть оформленный заказ. Дождись выдачи.", show_alert=True)
        return

    order_id = await get_or_create_draft_order(call.from_user.id)
    total = await calc_order_total(order_id)
    balance = await get_balance(call.from_user.id)

    if total <= 0:
        await call.answer("Корзина пуста", show_alert=True)
        return

    if balance < total:
        await call.answer(
            f"Недостаточно баллов: нужно {total}, у тебя {balance}",
            show_alert=True
        )
        return

    res = await checkout_order(call.from_user.id)
    if not res["ok"]:
        reason = res.get("reason")
        if reason == "already_checked_out":
            await call.answer("У тебя уже есть оформленный заказ. Дождись выдачи.", show_alert=True)
            return
        if reason == "empty":
            await call.answer("Корзина пуста", show_alert=True)
            return
        if reason == "not_enough":
            await call.answer(
                f"Недостаточно баллов: нужно {res['need']}, у тебя {res['balance']}",
                show_alert=True
            )
            return
        await call.answer("Не удалось оформить заказ", show_alert=True)
        return

    await call.message.edit_text(
        f"✅ Заказ оформлен!\n"
        f"ID заказа: {res['order_id']}\n"
        f"Сумма: {res['total']} баллов\n\n"
        f"Сообщи организатору ID заказа для выдачи мерча.\n"
        f"Баллы и склад спишутся при выдаче.",
        reply_markup=None
    )
    await call.answer()




@router.message(lambda m: m.text == "🧾 Заказы")
async def my_orders(message: types.Message):
    order_id = await get_active_order_id(message.from_user.id)
    if not order_id:
        await message.answer("🧾 У тебя пока нет активных заказов.", reply_markup=main_menu())
        return
    await message.answer(
        f"🧾 Твой активный заказ: #{order_id}\n"
        f"Дождись выдачи у организаторов.\n"
        f"Баллы спишутся при выдаче.",
        reply_markup=main_menu()
    )
