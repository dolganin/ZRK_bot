import secrets
import string
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.organizer_keyboards import organizer_menu
from keyboards.student_keyboards import main_menu
from utils.database import (
    is_admin,
    check_code_exists,
    add_code_to_event,
    get_events,
    get_codes_usage,
    delete_code,
)

router = Router()

TZ = ZoneInfo("Asia/Novosibirsk")
UTC = ZoneInfo("UTC")


class CodesStates(StatesGroup):
    waiting_for_event_id = State()
    waiting_for_code_points = State()
    waiting_for_code_value = State()
    waiting_for_starts_delay = State()
    waiting_for_duration = State()
    waiting_for_max_uses = State()
    waiting_for_code_to_delete = State()


def generate_random_code(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


async def generate_unique_code(length: int = 10) -> str:
    while True:
        code = generate_random_code(length).upper()
        if not await check_code_exists(code):
            return code


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


def _dt_to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(UTC)


def _parse_delta(text: str) -> timedelta:
    s = text.strip().lower()
    if s.isdigit():
        return timedelta(minutes=int(s))

    value = int(s[:-1])
    unit = s[-1]

    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)

    raise ValueError


def _fmt_local(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M")


@router.message(Command("codes"))
async def codes_root(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    events = await get_events()
    if not events:
        await message.answer("❌ Нет мероприятий.", reply_markup=organizer_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{e['id']}. {e['name']}", callback_data=f"codes:event:{e['id']}")]
            for e in events
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="codes:back")]]
    )

    await message.answer("Выберите мероприятие:", reply_markup=kb)
    await state.set_state(CodesStates.waiting_for_event_id)


@router.callback_query(CodesStates.waiting_for_event_id, F.data.startswith("codes:event:"))
async def codes_event_pick(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    event_id = int(call.data.split(":")[-1])
    await state.update_data(event_id=event_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать код", callback_data="codes:add")],
        [InlineKeyboardButton(text="🗑 Удалить код", callback_data="codes:delete")],
        [InlineKeyboardButton(text="📜 Показать коды", callback_data="codes:list")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="codes:root")]
    ])

    await call.message.answer("Коды мероприятия:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "codes:list")
async def codes_list(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return

    event_id = (await state.get_data()).get("event_id")
    items = await get_codes_usage(event_id=event_id)

    if not items:
        await call.message.answer("❌ Кодов нет.", reply_markup=organizer_menu())
        await call.answer()
        return

    parts = ["🔑 Коды:"]
    for c in items:
        parts.append(
            f"\n🔸 {c['code']} ({c['status']})"
            f"\n➕ {c['points']} | использований: {c['usage_count']}"
            f"\n⏳ start: {_fmt_local(c.get('starts_at'))} | end: {_fmt_local(c.get('expires_at'))}"
        )

    await call.message.answer("\n".join(parts), reply_markup=organizer_menu())
    await call.answer()


@router.callback_query(F.data == "codes:add")
async def codes_add_start(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    await call.message.answer("Введите количество баллов (> 0):")
    await state.set_state(CodesStates.waiting_for_code_points)
    await call.answer()


@router.message(CodesStates.waiting_for_code_points)
async def codes_points(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    try:
        points = int(message.text)
        if points <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Нужно целое число > 0")
        return

    await state.update_data(points=points)
    await message.answer("Введите код или '-' для генерации:")
    await state.set_state(CodesStates.waiting_for_code_value)


@router.message(CodesStates.waiting_for_code_value)
async def codes_value(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    raw = message.text.strip()
    if raw == "-":
        code = await generate_unique_code()
    else:
        code = raw.upper()
        if not code.isalnum() or len(code) < 4:
            await message.answer("❌ Только латиница/цифры, длина ≥ 4")
            return
        if await check_code_exists(code):
            await message.answer("❌ Такой код уже существует")
            return

    await state.update_data(code=code)

    await message.answer(
        "Через сколько код НАЧНЁТ действовать?\n"
        "Примеры: 0, 10m, 2h, 1d\n"
        "'-' — без ограничения снизу"
    )
    await state.set_state(CodesStates.waiting_for_starts_delay)


@router.message(CodesStates.waiting_for_starts_delay)
async def codes_starts_delay(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    now = datetime.now(tz=TZ)

    s = message.text.strip().lower()
    if s == "-":
        starts_at = None
    else:
        try:
            starts_at = now + _parse_delta(s)
        except Exception:
            await message.answer("❌ Формат: 10m / 2h / 1d / 0 / -")
            return

    await state.update_data(starts_at=_dt_to_utc(starts_at))

    await message.answer(
        "Сколько код БУДЕТ действовать?\n"
        "Примеры: 30m, 12h, 7d\n"
        "'-' — бессрочно"
    )
    await state.set_state(CodesStates.waiting_for_duration)


@router.message(CodesStates.waiting_for_duration)
async def codes_duration(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    data = await state.get_data()
    starts_at = data.get("starts_at")

    s = message.text.strip().lower()
    if s == "-":
        expires_at = None
    else:
        try:
            duration = _parse_delta(s)
        except Exception:
            await message.answer("❌ Формат: 30m / 12h / 7d / -")
            return

        base = starts_at or datetime.now(tz=TZ)
        expires_at = base + duration

    await state.update_data(expires_at=_dt_to_utc(expires_at))

    await message.answer(
        "Лимит использований?\n"
        "Число ≥ 1 или '-'"
    )
    await state.set_state(CodesStates.waiting_for_max_uses)


@router.message(CodesStates.waiting_for_max_uses)
async def codes_max_uses(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    s = message.text.strip()
    if s == "-":
        max_uses = None
    else:
        try:
            max_uses = int(s)
            if max_uses < 1:
                raise ValueError
        except Exception:
            await message.answer("❌ Введите число ≥ 1 или '-'")
            return

    data = await state.get_data()

    await add_code_to_event(
        event_id=data["event_id"],
        code=data["code"],
        points=data["points"],
        is_income=True,
        starts_at=data["starts_at"],
        expires_at=data["expires_at"],
        max_uses=max_uses,
    )

    await message.answer(
        f"✅ Код создан\n🔑 {data['code']} | ➕ {data['points']}",
        reply_markup=organizer_menu()
    )
    await state.clear()


@router.callback_query(F.data == "codes:delete")
async def codes_delete_start(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return

    event_id = (await state.get_data()).get("event_id")
    items = await get_codes_usage(event_id=event_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c['code']} ({c['usage_count']})", callback_data=f"codes:del:{c['code']}")]
        for c in items
    ])

    await call.message.answer("Выберите код для удаления:", reply_markup=kb)
    await state.set_state(CodesStates.waiting_for_code_to_delete)
    await call.answer()


@router.callback_query(CodesStates.waiting_for_code_to_delete, F.data.startswith("codes:del:"))
async def codes_delete_pick(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return

    code = call.data.split(":")[-1]
    await delete_code(code)
    await call.message.answer(f"✅ Код {code} удалён", reply_markup=organizer_menu())
    await state.clear()
    await call.answer()
