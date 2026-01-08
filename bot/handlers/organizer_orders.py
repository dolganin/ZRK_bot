from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu
from utils.database import is_admin
from utils.shop_db import get_order_for_issue, issue_order_by_admin

router = Router()


class OrganizerOrdersStates(StatesGroup):
    waiting_for_order_id = State()
    picking_items = State()
    waiting_for_item_qty = State()


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


def _render_issue_text(order: dict, items: list[dict], issued: dict) -> str:
    lines = [
        f"📦 Выдача заказа #{order['order_id']}",
        f"👤 Пользователь: {order['user_id']}",
        f"📌 Статус: {order['status']}",
        "",
        "Позиции (выдаём / заказано):"
    ]
    total_planned = 0
    total_issued = 0
    for it in items:
        pid = int(it["product_id"])
        key = str(pid)
        q = int(it["qty"])
        pe = int(it["points_each"])
        qi = int(issued.get(key, q))
        total_planned += q * pe
        total_issued += qi * pe
        lines.append(f"• {it['name']}: {qi}/{q}  (по {pe} балл.)")

    lines.append("")
    lines.append(f"🧾 Итого (заказано): {total_planned} баллов")
    lines.append(f"✅ К списанию (к выдаче): {total_issued} баллов")
    lines.append("")
    lines.append("По умолчанию выдаём всё. Нажми на позицию, чтобы уменьшить количество.")
    return "\n".join(lines)


def _issue_kb(items: list[dict], issued: dict) -> InlineKeyboardMarkup:
    rows = []
    for it in items:
        pid = int(it["product_id"])
        key = str(pid)
        q = int(it["qty"])
        qi = int(issued.get(key, q))
        rows.append([
            InlineKeyboardButton(
                text=f"{it['name']}: {qi}/{q}",
                callback_data=f"issue:item:{pid}"
            )
        ])

    rows.append([
        InlineKeyboardButton(text="✅ Подтвердить выдачу", callback_data="issue:confirm")
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="issue:cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("fulfill"))
async def cmd_fulfill(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("Введите ID заказа, который нужно выдать (этап подтверждения выдачи):")
    await state.set_state(OrganizerOrdersStates.waiting_for_order_id)


@router.message(F.text == "✅ Выдать заказ")
async def fulfill_btn(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("Введите ID заказа, который нужно выдать (этап подтверждения выдачи):")
    await state.set_state(OrganizerOrdersStates.waiting_for_order_id)


@router.message(OrganizerOrdersStates.waiting_for_order_id)
async def issue_start_by_id(message: types.Message, state: FSMContext):
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

    info = await get_order_for_issue(order_id=order_id)
    if not info["ok"]:
        reason = info.get("reason", "unknown")
        if reason == "not_found":
            await message.answer("❌ Заказ не найден.", reply_markup=organizer_menu())
        elif reason == "bad_status":
            await message.answer(
                f"❌ Заказ нельзя выдавать в текущем статусе: {info.get('status')}",
                reply_markup=organizer_menu()
            )
        elif reason == "empty":
            await message.answer("❌ Заказ пустой.", reply_markup=organizer_menu())
        else:
            await message.answer("❌ Не удалось открыть заказ для выдачи.", reply_markup=organizer_menu())
        await state.clear()
        return

    order = info["order"]
    items = info["items"]

    issued = {str(int(it["product_id"])): int(it["qty"]) for it in items}

    await state.update_data(
        order_id=int(order["order_id"]),
        user_id=int(order["user_id"]),
        status=str(order["status"]),
        items=items,
        issued=issued
    )

    await message.answer(
        _render_issue_text(order, items, issued),
        reply_markup=_issue_kb(items, issued)
    )
    await state.set_state(OrganizerOrdersStates.picking_items)


@router.callback_query(OrganizerOrdersStates.picking_items, F.data == "issue:cancel")
async def issue_cancel(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return
    await call.message.answer("🛠 Панель организатора", reply_markup=organizer_menu())
    await state.clear()
    await call.answer()


@router.callback_query(OrganizerOrdersStates.picking_items, F.data.startswith("issue:item:"))
async def issue_pick_item(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    pid = int(call.data.split(":")[-1])
    data = await state.get_data()
    items = data["items"]
    issued = data["issued"]

    it = next((x for x in items if int(x["product_id"]) == pid), None)
    if not it:
        await call.answer("Позиция не найдена", show_alert=True)
        return

    q = int(it["qty"])
    qi = int(issued.get(str(pid), q))

    await state.update_data(editing_product_id=pid)

    await call.message.answer(
        f"✏️ Введите новое количество к выдаче для позиции:\n"
        f"• {it['name']}\n"
        f"Заказано: {q}\n"
        f"Сейчас к выдаче: {qi}\n\n"
        f"Введите число от 0 до {q}:"
    )
    await state.set_state(OrganizerOrdersStates.waiting_for_item_qty)
    await call.answer()


@router.message(OrganizerOrdersStates.waiting_for_item_qty)
async def issue_set_item_qty(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    data = await state.get_data()
    pid = int(data.get("editing_product_id") or 0)
    items = data["items"]
    issued = data["issued"]

    it = next((x for x in items if int(x["product_id"]) == pid), None)
    if not it:
        await message.answer("❌ Позиция не найдена. Начните заново.", reply_markup=organizer_menu())
        await state.clear()
        return

    max_q = int(it["qty"])
    try:
        new_q = int((message.text or "").strip())
        if new_q < 0 or new_q > max_q:
            raise ValueError
    except Exception:
        await message.answer(f"❌ Введите число от 0 до {max_q}")
        return

    issued[str(pid)] = new_q
    await state.update_data(issued=issued, editing_product_id=None)

    order = {
        "order_id": data["order_id"],
        "user_id": data["user_id"],
        "status": data["status"],
    }

    await message.answer(
        _render_issue_text(order, items, issued),
        reply_markup=_issue_kb(items, issued)
    )
    await state.set_state(OrganizerOrdersStates.picking_items)


@router.callback_query(OrganizerOrdersStates.picking_items, F.data == "issue:confirm")
async def issue_confirm(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data["order_id"])
    issued = {int(k): int(v) for k, v in (data.get("issued") or {}).items()}

    res = await issue_order_by_admin(
        order_id=order_id,
        admin_id=call.from_user.id,
        issued_qty=issued
    )

    if not res["ok"]:
        reason = res.get("reason", "unknown")
        if reason == "not_found":
            await call.message.answer("❌ Заказ не найден.", reply_markup=organizer_menu())
        elif reason == "bad_status":
            await call.message.answer(
                f"❌ Заказ нельзя выдавать в текущем статусе: {res.get('status')}",
                reply_markup=organizer_menu()
            )
        elif reason == "already_fulfilled":
            await call.message.answer("ℹ️ Заказ уже был выдан ранее.", reply_markup=organizer_menu())
        elif reason == "empty":
            await call.message.answer("❌ Заказ пустой.", reply_markup=organizer_menu())
        elif reason == "nothing_to_issue":
            await call.message.answer("❌ Нечего выдавать (везде 0).", reply_markup=organizer_menu())
        elif reason == "not_enough":
            await call.message.answer(
                f"❌ Недостаточно баллов у пользователя.\nНужно: {res.get('need')} | Есть: {res.get('balance')}",
                reply_markup=organizer_menu()
            )
        elif reason == "out_of_stock":
            items = res.get("items", [])
            if items:
                lines = ["❌ Не хватает товара на складе:"]
                for it in items:
                    lines.append(f"• {it['name']} (нужно {it['need']}, есть {it['have']})")
                await call.message.answer("\n".join(lines), reply_markup=organizer_menu())
            else:
                await call.message.answer("❌ Не хватает товара на складе.", reply_markup=organizer_menu())
        else:
            await call.message.answer("❌ Не удалось выдать заказ.", reply_markup=organizer_menu())

        await state.clear()
        await call.answer()
        return

    await call.message.answer(
        f"✅ Заказ #{order_id} выдан.\n"
        f"Списано: {res['total']} баллов\n"
        f"Баланс пользователя: {res['new_balance']}",
        reply_markup=organizer_menu()
    )
    await state.clear()
    await call.answer()
