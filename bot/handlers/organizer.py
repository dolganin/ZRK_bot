import secrets
import string
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import (
    is_admin, get_all_students_rating,
    get_active_codes, add_event, get_events,
    add_code_to_event, add_admin, send_notification,
    check_code_exists, asyncpg
)

router = Router()

class OrganizerStates(StatesGroup):
    waiting_for_notification = State()
    waiting_for_admin_id = State()
    waiting_for_event_name = State()
    waiting_for_event_id = State()
    waiting_for_code_points = State()
    waiting_for_code_type = State()
    waiting_for_code = State()

# ======================= ГЕНЕРАЦИЯ КОДОВ =======================
def generate_random_code(length: int = 100) -> str:
    """Генерирует случайный код из букв и цифр"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

async def generate_unique_code(length: int = 100) -> str:
    """Генерирует уникальный код с проверкой в БД"""
    while True:
        code = generate_random_code(length)
        if not await check_code_exists(code):
            return code

@router.message(Command("generate_code"))
async def cmd_generate_code(message: types.Message):
    """Генерация уникального 100-символьного кода"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    try:
        code = await generate_unique_code()
        response = (
            "🔑 Сгенерирован новый уникальный код:\n\n"
            f"<code>{code}</code>\n\n"
            "❗️ Сохраните его в безопасном месте!"
        )
        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации кода: {str(e)}")

# ======================= ОСНОВНЫЕ КОМАНДЫ =======================
@router.message(Command("notify"))
async def cmd_notify(message: types.Message, state: FSMContext):
    """Отправка уведомлений всем студентам"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    await message.answer("📢 Введите текст уведомления:")
    await state.set_state(OrganizerStates.waiting_for_notification)

@router.message(OrganizerStates.waiting_for_notification)
async def process_notify(message: types.Message, state: FSMContext):
    """Обработка текста уведомления"""
    await send_notification(message.text)
    await message.answer("✅ Уведомление отправлено всем студентам!")
    await state.clear()

@router.message(Command("add_admin"))
async def cmd_add_admin(message: types.Message, state: FSMContext):
    """Добавление нового администратора"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    await message.answer("👨💻 Введите ID нового администратора:")
    await state.set_state(OrganizerStates.waiting_for_admin_id)

@router.message(OrganizerStates.waiting_for_admin_id)
async def process_add_admin(message: types.Message, state: FSMContext):
    """Обработка ID администратора"""
    try:
        user_id = int(message.text)
        await add_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} добавлен в администраторы!")
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя")
    finally:
        await state.clear()

# ======================= РЕЙТИНГ И КОДЫ =======================
@router.message(Command("top_all"))
async def cmd_top_all(message: types.Message):
    """Показ полного рейтинга студентов"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    students = await get_all_students_rating()
    response = ["🏆 Полный рейтинг студентов:"]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']}: {student['balance']} баллов")
    
    await message.answer("\n".join(response))

@router.message(Command("active_codes"))
async def cmd_active_codes(message: types.Message):
    """Показ активных кодов"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    codes = await get_active_codes()
    if not codes:
        return await message.answer("🔐 Нет активных кодов")
    
    response = ["🔑 Активные коды:"]
    for code in codes:
        response.append(
            f"\nКод: {code['code']}\n"
            f"Мероприятие: {code['event_name']}\n"
            f"Баллы: {code['points']} ({'➕ Пополнение' if code['is_income'] else '➖ Списание'})"
        )
    
    await message.answer("\n".join(response))

# ======================= МЕРОПРИЯТИЯ И КОДЫ =======================
@router.message(Command("add_event"))
async def cmd_add_event(message: types.Message, state: FSMContext):
    """Добавление нового мероприятия"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    await message.answer("📝 Введите название мероприятия:")
    await state.set_state(OrganizerStates.waiting_for_event_name)

@router.message(OrganizerStates.waiting_for_event_name)
async def process_event_name(message: types.Message, state: FSMContext):
    """Обработка названия мероприятия"""
    await add_event(message.text)
    await message.answer(f"✅ Мероприятие «{message.text}» добавлено!")
    await state.clear()

@router.message(Command("add_code"))
async def cmd_add_code(message: types.Message, state: FSMContext):
    """Добавление кода к мероприятию"""
    if not await is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещен")
    
    events = await get_events()
    if not events:
        return await message.answer("❌ Нет мероприятий для привязки кода")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{e['id']}. {e['name']}", callback_data=f"event_{e['id']}")]
        for e in events
    ])
    
    await message.answer("📋 Выберите мероприятие:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_event_id)

@router.callback_query(OrganizerStates.waiting_for_event_id, F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора мероприятия"""
    event_id = int(callback.data.split("_")[1])
    event = await get_events(event_id)
    
    if not event:
        await callback.message.answer("❌ Мероприятие не найдено")
        return await state.clear()
    
    await state.update_data(event_id=event_id)
    await callback.message.answer(f"🛠 Создаем код для мероприятия: {event['name']}\n"
                                   "➡ Введите количество баллов:")
    await state.set_state(OrganizerStates.waiting_for_code_points)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_code_points)
async def input_points(message: types.Message, state: FSMContext):
    """Обработка ввода количества баллов"""
    try:
        points = abs(int(message.text))
        if points == 0:
            raise ValueError
        await state.update_data(points=points)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнение баллов", callback_data="type_income")],
            [InlineKeyboardButton(text="Списание баллов", callback_data="type_outcome")]
        ])
        
        await message.answer("🔧 Выберите тип операции:", reply_markup=keyboard)
        await state.set_state(OrganizerStates.waiting_for_code_type)
    except (ValueError, TypeError):
        await message.answer("❌ Некорректное значение. Введите целое число больше 0")

@router.callback_query(OrganizerStates.waiting_for_code_type, F.data.startswith("type_"))
async def select_type(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора типа операции"""
    operation_type = callback.data.split("_")[1]
    is_income = operation_type == "income"
    
    await state.update_data(is_income=is_income)
    await callback.message.answer("🔠 Введите код (латинские буквы и цифры):")
    await state.set_state(OrganizerStates.waiting_for_code)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_code)
async def input_code(message: types.Message, state: FSMContext):
    """Финализация создания кода"""
    data = await state.get_data()
    code = message.text.strip().upper()
    
    if not code.isalnum() or len(code) < 4:
        return await message.answer("❌ Код должен содержать только латинские буквы/цифры и быть не короче 4 символов")
    
    try:
        await add_code_to_event(
            event_id=data['event_id'],
            code=code,
            points=data['points'],
            is_income=data['is_income']
        )
        await message.answer(f"✅ Код успешно создан!\n"
                             f"🔑 {code} | {'➕ ' if data['is_income'] else '➖ '}{data['points']} баллов")
    except asyncpg.exceptions.UniqueViolationError:
        await message.answer("❌ Этот код уже существует")
    
    await state.clear()