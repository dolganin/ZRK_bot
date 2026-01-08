from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu
from utils.database import is_admin
from utils.shop_db import fulfill_order_by_admin

router = Router()


class OrganizerOrdersStates(StatesGroup):
    waiting_for_order_id = State()


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


@router.message(Command("fulfill"))
async def cmd_fulfill(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("Введите ID заказа (корзины), который нужно выдать:")
    await state.set_state(OrganizerOrdersStates.waiting_for_order_id)


@router.message(F.text == "✅ Выдать заказ")
async def fulfill_btn(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("Введите ID заказа (корзины), который нужно выдать:")
    await state.set_state(OrganizerOrdersStates.waiting_for_order_id)


@router.message(OrganizerOrdersStates.waiting_for_order_id)
async def fulfill_by_id(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    raw = (message.text or "").strip()
    if raw.lower() in {"назад", "⬅️ назад"}:
        await message.answer("🛠 Панель организатора", reply_markup=organizer_menu())
        await state.clear()
        return

    try:
        order_id = int(raw)
        if order_id <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Нужен целый положительный ID заказа. Введите ещё раз:")
        return

    res = await fulfill_order_by_admin(order_id=order_id, admin_id=message.from_user.id)

    if not res["ok"]:
        reason = res.get("reason", "unknown")

        if reason == "not_found":
            await message.answer("❌ Заказ не найден.", reply_markup=organizer_menu())
        elif reason == "bad_status":
            await message.answer(
                f"❌ Заказ нельзя выдать в текущем статусе: {res.get('status')}",
                reply_markup=organizer_menu()
            )
        elif reason == "already_fulfilled":
            await message.answer("ℹ️ Заказ уже был выдан ранее.", reply_markup=organizer_menu())
        elif reason == "empty":
            await message.answer("❌ Заказ пустой.", reply_markup=organizer_menu())
        elif reason == "not_enough":
            await message.answer(
                f"❌ Недостаточно баллов у пользователя.\nНужно: {res.get('need')} | Есть: {res.get('balance')}",
                reply_markup=organizer_menu()
            )
        elif reason == "out_of_stock":
            items = res.get("items", [])
            if items:
                lines = ["❌ Не хватает товара на складе:"]
                for it in items:
                    lines.append(f"• {it['name']} (нужно {it['need']}, есть {it['have']})")
                await message.answer("\n".join(lines), reply_markup=organizer_menu())
            else:
                await message.answer("❌ Не хватает товара на складе.", reply_markup=organizer_menu())
        else:
            await message.answer("❌ Не удалось выдать заказ.", reply_markup=organizer_menu())

        await state.clear()
        return

    user_id = res["user_id"]
    total = res["total"]
    new_balance = res["new_balance"]
    await message.answer(
        f"✅ Заказ #{order_id} выдан.\nСписано: {total} баллов\nБаланс пользователя: {new_balance}",
        reply_markup=organizer_menu()
    )
    await state.clear()
