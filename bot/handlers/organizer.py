import secrets
import string
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.organizer_keyboards import organizer_menu, rating_menu
from keyboards.student_keyboards import main_menu
from utils.database import (
    is_admin,
    get_all_students_rating,
    get_codes_usage,
    add_event,
    get_events,
    add_code_to_event,
    add_admin,
    send_notification,
    check_code_exists,
    delete_code,
    delete_event
)

router = Router()

class OrganizerStates(StatesGroup):
    waiting_for_notification = State()
    confirming_notification = State()
    waiting_for_admin_id = State()
    waiting_for_rating_limit = State()
    waiting_for_event_name = State()
    waiting_for_event_to_delete = State()
    waiting_for_event_id = State()
    waiting_for_code_points = State()
    waiting_for_code_type = State()
    waiting_for_code = State()
    waiting_for_code_to_delete = State()
    waiting_for_product_name = State()
    waiting_for_product_price = State()

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

@router.message(Command("admin"))
async def admin_home(message: types.Message):
    if not await ensure_admin(message):
        return
    await message.answer("🛠 Панель организатора", reply_markup=organizer_menu())

@router.message(F.text == "📊 Рейтинг")
async def show_rating(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("Выберите, сколько студентов показать:", reply_markup=rating_menu())
    await state.set_state(OrganizerStates.waiting_for_rating_limit)

@router.message(OrganizerStates.waiting_for_rating_limit)
async def handle_rating_limit(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    if message.text == "⬅️ Назад":
        await message.answer("🛠 Панель организатора", reply_markup=organizer_menu())
        await state.clear()
        return

    if message.text == "10 студентов":
        limit = 10
    elif message.text == "50 студентов":
        limit = 50
    elif message.text == "Весь список":
        limit = None
    else:
        await message.answer("❌ Неправильный выбор!", reply_markup=rating_menu())
        return

    rating = await get_all_students_rating(user_id=message.from_user.id, limit=limit or 10_000_000)

    title = f"🔥 Рейтинг (топ {limit})" if limit else "🔥 Полный рейтинг"
    lines = [title, ""]
    for place, student in enumerate(rating, 1):
        lines.append(f"{place}. {student['name']} — {student['balance']}")

    await message.answer("\n".join(lines), reply_markup=organizer_menu())
    await state.clear()

@router.message(F.text == "📢 Уведомление")
async def start_notify(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("✍️ Введите текст уведомления:")
    await state.set_state(OrganizerStates.waiting_for_notification)

@router.message(OrganizerStates.waiting_for_notification)
async def confirm_notify(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    await state.update_data(notification_text=message.text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="org:notify:confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="org:notify:cancel")]
    ])

    await message.answer(
        "⚠️ Подтвердите отправку уведомления всем пользователям:\n\n"
        f"{message.text}",
        reply_markup=keyboard
    )
    await state.set_state(OrganizerStates.confirming_notification)

@router.callback_query(OrganizerStates.confirming_notification, F.data == "org:notify:confirm")
async def process_confirm_send_notification(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    data = await state.get_data()
    notification_text = data.get("notification_text", "")
    await send_notification(notification_text)

    await callback.message.edit_text("✅ Уведомление отправлено.")
    await callback.answer()
    await state.clear()

@router.callback_query(OrganizerStates.confirming_notification, F.data == "org:notify:cancel")
async def process_cancel_send_notification(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()
    await state.clear()

@router.message(F.text == "👥 Добавить админа")
async def start_add_admin(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await message.answer("🆔 Введите Telegram ID пользователя:")
    await state.set_state(OrganizerStates.waiting_for_admin_id)

@router.message(OrganizerStates.waiting_for_admin_id)
async def process_add_admin(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    try:
        user_id = int(message.text)
        await add_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} стал администратором!", reply_markup=organizer_menu())
    except Exception:
        await message.answer("❌ Неверный ID", reply_markup=organizer_menu())
    await state.clear()

@router.message(F.text == "🛒 Товары")
async def products_menu(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="org:prod:add")],
        [InlineKeyboardButton(text="📃 Список товаров", callback_data="org:prod:list")]
    ])
    await message.answer("Управление товарами:", reply_markup=kb)


@router.message(F.text == "📜 Активные коды")
async def show_active_codes(message: types.Message):
    if not await ensure_admin(message):
        return

    codes = await get_codes_usage()
    if not codes:
        await message.answer("❌ Нет активных кодов", reply_markup=organizer_menu())
        return

    parts = ["🔑 Активные коды:"]
    for c in codes:
        sign = "➕" if c["is_income"] else "➖"
        parts.append(
            f"\n🔸 {c['code']}\n"
            f"🏷️ {c['event_name']}\n"
            f"{sign} {c['points']} баллов\n"
            f"📊 использований: {c['usage_count']}"
        )

    await message.answer("\n".join(parts), reply_markup=organizer_menu())

@router.message(F.text == "🎯 Мероприятия")
async def manage_events(message: types.Message):
    if not await ensure_admin(message):
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="org:event:add")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="org:event:delete")]
    ])
    await message.answer("Мероприятия:", reply_markup=keyboard)

@router.callback_query(F.data == "org:event:add")
async def event_add(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        return
    await callback.message.answer("📝 Введите название мероприятия:")
    await state.set_state(OrganizerStates.waiting_for_event_name)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_event_name)
async def process_event_name(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    await add_event(message.text)
    await message.answer("✅ Мероприятие создано!", reply_markup=organizer_menu())
    await state.clear()

@router.callback_query(F.data == "org:event:delete")
async def event_delete(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        return

    events = await get_events()
    if not events:
        await callback.message.answer("❌ Нет мероприятий для удаления", reply_markup=organizer_menu())
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=e["name"], callback_data=f"org:event:del:{e['id']}")]
        for e in events
    ])
    await callback.message.answer("Выберите мероприятие для удаления:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_event_to_delete)
    await callback.answer()

@router.callback_query(OrganizerStates.waiting_for_event_to_delete, F.data.startswith("org:event:del:"))
async def delete_event_callback(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    event_id = int(callback.data.split(":")[3])
    try:
        await delete_event(event_id)
        await callback.message.answer("✅ Мероприятие удалено!", reply_markup=organizer_menu())
    except Exception:
        await callback.message.answer("❌ Ошибка при удалении мероприятия", reply_markup=organizer_menu())
    await state.clear()
    await callback.answer()

@router.message(F.text == "🔑 Коды мероприятий")
async def codes_to_event(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return

    events = await get_events()
    if not events:
        await message.answer("❌ Нет мероприятий", reply_markup=organizer_menu())
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{e['id']}. {e['name']}", callback_data=f"org:code:event:{e['id']}")]
        for e in events
    ])
    await message.answer("Выберите мероприятие:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_event_id)

@router.callback_query(OrganizerStates.waiting_for_event_id, F.data.startswith("org:code:event:"))
async def select_event(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    event_id = int(callback.data.split(":")[3])
    await state.update_data(event_id=event_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить код", callback_data="org:code:add")],
        [InlineKeyboardButton(text="🗑 Удалить код", callback_data="org:code:delete")],
        [InlineKeyboardButton(text="🎲 Сгенерировать код", callback_data="org:code:gen")]
    ])

    await callback.message.answer("Коды мероприятия:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "org:code:gen")
async def gen_code(callback: types.CallbackQuery):
    if not await ensure_admin_cb(callback):
        return
    code = await generate_unique_code()
    await callback.message.answer(f"🔐 Новый код:\n<code>{code}</code>", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "org:code:add")
async def start_add_code(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return
    await callback.message.answer("Введите количество баллов (целое > 0):")
    await state.set_state(OrganizerStates.waiting_for_code_points)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_code_points)
async def input_points(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    try:
        points = abs(int(message.text))
        if points <= 0:
            raise ValueError
        await state.update_data(points=points)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнение ➕", callback_data="org:code:type:income")],
            [InlineKeyboardButton(text="Списание ➖", callback_data="org:code:type:outcome")]
        ])
        await message.answer("Выберите тип операции:", reply_markup=keyboard)
        await state.set_state(OrganizerStates.waiting_for_code_type)
    except Exception:
        await message.answer("❌ Введите целое число больше 0")

@router.callback_query(OrganizerStates.waiting_for_code_type, F.data.startswith("org:code:type:"))
async def select_type(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    operation_type = callback.data.split(":")[3]
    is_income = operation_type == "income"
    await state.update_data(is_income=is_income)

    await callback.message.answer("Введите уникальный код (латинские буквы/цифры) или '-' чтобы сгенерировать:")
    await state.set_state(OrganizerStates.waiting_for_code)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_code)
async def input_code(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return

    data = await state.get_data()
    code_raw = message.text.strip()

    if code_raw == "-":
        code = await generate_unique_code()
    else:
        code = code_raw.strip().upper()
        if not code.isalnum() or len(code) < 4:
            await message.answer("❌ Код: только латиница/цифры, длина >= 4")
            return

    try:
        await add_code_to_event(
            event_id=data["event_id"],
            code=code,
            points=data["points"],
            is_income=data["is_income"]
        )
        sign = "➕" if data["is_income"] else "➖"
        await message.answer(
            f"✅ Код создан\n🔑 {code} | {sign} {data['points']} баллов",
            reply_markup=organizer_menu()
        )
    except Exception:
        await message.answer("❌ Не удалось создать код (возможно, уже существует)", reply_markup=organizer_menu())
    await state.clear()

@router.callback_query(F.data == "org:code:delete")
async def start_delete_code(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    data = await state.get_data()
    event_id = data.get("event_id")
    codes = await get_codes_usage(event_id=event_id)
    if not codes:
        await callback.message.answer("❌ Нет кодов для удаления", reply_markup=organizer_menu())
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{c['code']} ({c['points']} | {'➕' if c['is_income'] else '➖'} | использовано {c['usage_count']})",
                callback_data=f"org:code:del:{c['code']}"
            )
        ]
        for c in codes
    ])
    await callback.message.answer("Выберите код для удаления:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_code_to_delete)
    await callback.answer()

@router.callback_query(OrganizerStates.waiting_for_code_to_delete, F.data.startswith("org:code:del:"))
async def select_code_to_delete(callback: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(callback):
        await state.clear()
        return

    code = callback.data.split(":")[3]
    try:
        await delete_code(code)
        await callback.message.answer(f"✅ Код {code} удалён", reply_markup=organizer_menu())
    except Exception:
        await callback.message.answer("❌ Ошибка при удалении кода", reply_markup=organizer_menu())
    await state.clear()
    await callback.answer()

@router.message(F.text == "🛒 Товары")
async def products_menu(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="org:prod:add")],
        [InlineKeyboardButton(text="📃 Список товаров", callback_data="org:prod:list")]
    ])
    await message.answer("Управление товарами:", reply_markup=kb)


from utils.shop_db import create_product, list_products

@router.callback_query(F.data == "org:prod:add")
async def prod_add(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return
    await call.message.answer("Введите название товара:")
    await state.set_state(OrganizerStates.waiting_for_product_name)
    await call.answer()

@router.message(OrganizerStates.waiting_for_product_name)
async def prod_name(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    name = message.text.strip()
    if not name:
        await message.answer("Введите непустое название товара:")
        return
    await state.update_data(product_name=name)
    await message.answer("Введите цену в баллах (целое число > 0):")
    await state.set_state(OrganizerStates.waiting_for_product_price)

@router.message(OrganizerStates.waiting_for_product_price)
async def prod_price(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
    except Exception:
        await message.answer("Цена должна быть целым числом > 0. Введите снова:")
        return

    data = await state.get_data()
    name = data["product_name"]

    pid = await create_product(name=name, price_points=price)
    await message.answer(f"✅ Товар добавлен: {name} — {price} баллов (id={pid})", reply_markup=organizer_menu())
    await state.clear()

@router.callback_query(F.data == "org:prod:list")
async def prod_list(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return
    items = await list_products(include_inactive=True)
    if not items:
        await call.message.answer("Товаров нет.", reply_markup=organizer_menu())
        await call.answer()
        return
    lines = ["🛒 Товары:"]
    for p in items:
        status = "✅" if p["is_active"] else "🚫"
        lines.append(f"{status} {p['id']}. {p['name']} — {p['price_points']} баллов")
    await call.message.answer("\n".join(lines), reply_markup=organizer_menu())
    await call.answer()
