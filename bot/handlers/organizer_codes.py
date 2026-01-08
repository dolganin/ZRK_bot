import secrets
import string
from datetime import datetime
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

TZ = ZoneInfo("Europe/Stockholm")
UTC = ZoneInfo("UTC")


class CodesStates(StatesGroup):
    waiting_for_event_id = State()
    waiting_for_code_points = State()
    waiting_for_code_value = State()
    waiting_for_starts_at = State()
    waiting_for_expires_at = State()
    waiting_for_max_uses = State()
    waiting_for_code_to_delete = State()


def generate_random_code(length: int = 10) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))


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


def _dt_to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat()


def _iso_to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


def _parse_dt_local_to_utc(text: str) -> datetime:
    s = text.strip()
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=TZ).astimezone(UTC)


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

    await message.answer("Выберите мероприятие для работы с кодами:", reply_markup=kb)
    await state.set_state(CodesStates.waiting_for_event_id)


@router.callback_query(CodesStates.waiting_for_event_id, F.data == "codes:back")
async def codes_back(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return
    await call.message.answer("🛠 Панель организатора", reply_markup=organizer_menu())
    await state.clear()
    await call.answer()


@router.callback_query(CodesStates.waiting_for_event_id, F.data.startswith("codes:event:"))
async def codes_event_pick(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    event_id = int(call.data.split(":")[-1])
    await state.update_data(event_id=event_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать код (пополнение)", callback_data="codes:add")],
        [InlineKeyboardButton(text="🗑 Удалить код", callback_data="codes:delete")],
        [InlineKeyboardButton(text="📜 Показать коды", callback_data="codes:list")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="codes:root")]
    ])
    await call.message.answer("Коды мероприятия:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "codes:root")
async def codes_root_back(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return
    await state.clear()
    await codes_root(call.message, state)
    await call.answer()


@router.callback_query(F.data == "codes:list")
async def codes_list(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    items = await get_codes_usage(event_id=event_id)

    if not items:
        await call.message.answer("❌ Кодов нет.", reply_markup=organizer_menu())
        await call.answer()
        return

    parts = ["🔑 Коды (только пополнение):"]
    for c in items:
        st = c.get("starts_at")
        ex = c.get("expires_at")
        mu = c.get("max_uses")
        status = c.get("status")

        parts.append(
            f"\n🔸 {c['code']} ({status})\n"
            f"➕ {c['points']} баллов | использований: {c['usage_count']}"
            + (f" / лимит: {mu}" if mu is not None else "")
            + f"\n⏳ start: {_fmt_local(st)} | end: {_fmt_local(ex)}"
        )

    await call.message.answer("\n".join(parts), reply_markup=organizer_menu())
    await call.answer()


@router.callback_query(F.data == "codes:add")
async def codes_add_start(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return
    await call.message.answer("Введите количество баллов (целое > 0):")
    await state.set_state(CodesStates.waiting_for_code_points)
    await call.answer()


@router.message(CodesStates.waiting_for_code_points)
async def codes_points(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    try:
        points = abs(int(message.text))
        if points <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Введите целое число > 0")
        return

    await state.update_data(points=points)

    await message.answer("Введите код или '-' чтобы сгенерировать:")
    await state.set_state(CodesStates.waiting_for_code_value)


@router.message(CodesStates.waiting_for_code_value)
async def codes_value(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    raw = (message.text or "").strip()
    if raw == "-":
        code = await generate_unique_code()
    else:
        code = raw.upper()
        if not code.isalnum() or len(code) < 4:
            await message.answer("❌ Код: только латиница/цифры, длина >= 4")
            return
        if await check_code_exists(code):
            await message.answer("❌ Такой код уже существует. Введите другой или '-'")
            return

    await state.update_data(code=code)

    await message.answer(
        "Когда код НАЧНЁТ действовать?\n"
        "Формат: YYYY-MM-DD HH:MM (Europe/Stockholm)\n"
        "Варианты: 'now' = прямо сейчас, '-' = без ограничения снизу"
    )
    await state.set_state(CodesStates.waiting_for_starts_at)


@router.message(CodesStates.waiting_for_starts_at)
async def codes_starts_at(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    s = (message.text or "").strip().lower()
    if s == "-":
        starts_at = None
    elif s == "now":
        starts_at = datetime.now(tz=TZ).astimezone(UTC)
    else:
        try:
            starts_at = _parse_dt_local_to_utc(message.text)
        except Exception:
            await message.answer("❌ Неверный формат. Нужно YYYY-MM-DD HH:MM или 'now' или '-'")
            return

    await state.update_data(starts_at=_dt_to_iso_utc(starts_at))

    await message.answer(
        "Когда код ПЕРЕСТАНЕТ действовать?\n"
        "Формат: YYYY-MM-DD HH:MM (Europe/Stockholm)\n"
        "Вариант: '-' = не протухает"
    )
    await state.set_state(CodesStates.waiting_for_expires_at)


@router.message(CodesStates.waiting_for_expires_at)
async def codes_expires_at(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    s = (message.text or "").strip().lower()
    if s == "-":
        expires_at = None
    else:
        try:
            expires_at = _parse_dt_local_to_utc(message.text)
        except Exception:
            await message.answer("❌ Неверный формат. Нужно YYYY-MM-DD HH:MM или '-'")
            return

    data = await state.get_data()
    starts_at = _iso_to_dt(data.get("starts_at"))
    if starts_at is not None and expires_at is not None and expires_at <= starts_at:
        await message.answer("❌ expires_at должен быть позже starts_at. Введите снова:")
        return

    await state.update_data(expires_at=_dt_to_iso_utc(expires_at))

    await message.answer(
        "Лимит общих использований (max_uses)?\n"
        "Введите целое число >= 1 или '-' = без лимита"
    )
    await state.set_state(CodesStates.waiting_for_max_uses)


@router.message(CodesStates.waiting_for_max_uses)
async def codes_max_uses(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    s = (message.text or "").strip().lower()
    if s == "-":
        max_uses = None
    else:
        try:
            max_uses = int(s)
            if max_uses < 1:
                raise ValueError
        except Exception:
            await message.answer("❌ Введите целое число >= 1 или '-'")
            return

    data = await state.get_data()

    try:
        await add_code_to_event(
            event_id=int(data["event_id"]),
            code=str(data["code"]),
            points=int(data["points"]),
            is_income=True,
            starts_at=_iso_to_dt(data.get("starts_at")),
            expires_at=_iso_to_dt(data.get("expires_at")),
            max_uses=max_uses,
        )
        await message.answer(
            f"✅ Код создан\n🔑 {data['code']} | ➕ {data['points']} баллов",
            reply_markup=organizer_menu()
        )
    except Exception:
        await message.answer("❌ Не удалось создать код", reply_markup=organizer_menu())

    await state.clear()


@router.callback_query(F.data == "codes:delete")
async def codes_delete_start(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        await state.clear()
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    items = await get_codes_usage(event_id=event_id)
    if not items:
        await call.message.answer("❌ Нет кодов для удаления", reply_markup=organizer_menu())
        await call.answer()
        return

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
        await state.clear()
        return

    code = call.data.split(":")[-1]
    try:
        await delete_code(code)
        await call.message.answer(f"✅ Код {code} удалён", reply_markup=organizer_menu())
    except Exception:
        await call.message.answer("❌ Ошибка при удалении", reply_markup=organizer_menu())

    await state.clear()
    await call.answer()
