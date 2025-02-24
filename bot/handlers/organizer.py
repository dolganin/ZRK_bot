import secrets
import string
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from keyboards.organizer_keyboards import organizer_menu
from keyboards.student_keyboards import main_menu
import logging

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
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
    asyncpg,
    delete_code,
    delete_event
)

router = Router()

# Клавиатура организатора

class OrganizerStates(StatesGroup):
    waiting_for_notification = State()
    waiting_for_admin_id = State()
    waiting_for_event_name = State()
    waiting_for_event_id = State()
    waiting_for_code_points = State()
    waiting_for_code_type = State()
    waiting_for_code = State()
    waiting_for_action = State()
    waiting_for_code_to_delete = State ()
    waiting_for_event_action = State ()
    waiting_for_event_to_delete = State ()
    waiting_for_rating_limit = State()

# Генерация уникальных кодов
def generate_random_code(length: int = 10) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

async def generate_unique_code(length: int = 10) -> str:
    while True:
        code = generate_random_code(length)
        if not await check_code_exists(code):
            return code

# Основные обработчики

def rating_menu():
    buttons = [
        [types.KeyboardButton(text="10 студентов")],
        [types.KeyboardButton(text="50 студентов")],
        [types.KeyboardButton(text="Весь список")]
    ]
    markup = types.ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return markup

# Проверка наStarted по тексту "📊 Рейтинг"
@router.message(F.text == "📊 Рейтинг")
async def show_rating(message: types.Message, state: FSMContext):
    # Проверка на роль пользователя
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return
    
    # Отправляем меню выбора и устанавливаем состояние ожидания
    await message.answer("Выберите, сколько студентов показать:", reply_markup=rating_menu())
    await state.set_state(OrganizerStates.waiting_for_rating_limit)

# Обработчик для приема сообщения с количеством студентов
@router.message(OrganizerStates.waiting_for_rating_limit)
async def handle_rating_limit(message: types.Message, state: FSMContext):
    # Удаляем клавиатуру
    # Обрабатываем выбор пользователя
    if message.text == "10 студентов":
        limit = 10
    elif message.text == "50 студентов":
        limit = 50
    elif message.text == "Весь список":
        limit = None
    else:
        # Если введено не предVR 医 kolebctime значение
        await message.answer("❌ Неправильный выбор!", reply_markup=rating_menu())
        return
    
    rating = await get_all_students_rating(limit)
    
    # Если лимит установлен, показываем только N студентов
    if limit:
        rating_text = f"🔥Рейтинг (топ {limit} студентов):\n"
    else:
        rating_text = "🔥Полный рейтинг:\n"
    
    # Формируем строку для отображения рейтинга
    for place, student in enumerate(rating, 1):
        rating_text += f"{place}. {student['name']} - {student['balance']}\n"
    
    await message.answer(rating_text, reply_markup=organizer_menu())
    await state.clear()

@router.message(F.text == "📢 Уведомление")
async def start_notify(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return
    
    await message.answer("✍️ Введите текст уведомления:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrganizerStates.waiting_for_notification)

@router.message(OrganizerStates.waiting_for_notification)
async def process_notify(message: types.Message, state: FSMContext):
    await send_notification(message.text)
    await message.answer("✅ Уведомление отправлено!", reply_markup=organizer_menu())
    await state.clear()

@router.message(F.text == "🔑 Создать код")
async def generate_code_handler(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return
    
    try:
        code = await generate_unique_code()
        await message.answer(
            f"🔐 Новый код доступа:\n<code>{code}</code>\n\n"
            "❗️ Сохраните в безопасном месте!",
            parse_mode="HTML",
            reply_markup=organizer_menu()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=organizer_menu())

@router.message(F.text == "🎯 Мероприятие")
async def manage_event(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить мероприятие", callback_data="action_add_event")],
        [InlineKeyboardButton(text="Удалить мероприятие", callback_data="action_delete_event")]
    ])

    await message.answer("Выберите действие:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_event_action)

@router.callback_query(OrganizerStates.waiting_for_event_action, F.data.startswith("action_"))
async def select_event_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]

    if action == "add":
        await callback.message.answer("📝 Введите название мероприятия:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrganizerStates.waiting_for_event_name)
    elif action == "delete":
        events = await get_events()
        if not events:
            return await callback.message.answer("❌ Нет мероприятий для удаления", reply_markup=organizer_menu())

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{event['name']}", callback_data=f"delete_event_{event['id']}")]
            for event in events
        ])

        await callback.message.answer("Выберите мероприятие для удаления:", reply_markup=keyboard)
        await state.set_state(OrganizerStates.waiting_for_event_to_delete)

    await callback.answer()

@router.message(OrganizerStates.waiting_for_event_name)
async def process_event_name(message: types.Message, state: FSMContext):
    await add_event(message.text)
    await message.answer(f"✅ Мероприятие '{message.text}' создано!", reply_markup=organizer_menu())
    await state.clear()

@router.callback_query(OrganizerStates.waiting_for_event_to_delete, F.data.startswith("delete_event_"))
async def delete_event_callback(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])

    try:
        await delete_event(event_id)
        await callback.message.answer(f"✅ Мероприятие успешно удалено!", reply_markup=organizer_menu())
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при удалении мероприятия: {str(e)}", reply_markup=organizer_menu())
    finally:
        await state.clear()
    await callback.answer()



@router.message(F.text == "👥 Добавить админа")
async def start_add_admin(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return
    
    await message.answer("🆔 Введите ID пользователя:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrganizerStates.waiting_for_admin_id)

@router.message(OrganizerStates.waiting_for_admin_id)
async def process_add_admin(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await add_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} стал администратором!", reply_markup=organizer_menu())
    except ValueError:
        await message.answer("❌ Неверный формат ID", reply_markup=organizer_menu())
    finally:
        await state.clear()



@router.message(F.text == "📜 Активные коды")
async def show_active_codes(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return

    codes = await get_codes_usage()  # Получаем список кодов с их использованием
    if not codes:
        return await message.answer("❌ Нет активных кодов", reply_markup=organizer_menu())

    response = ["🔑 Активные коды:\n"]
    for code in codes:
        response.append(
            f"\n🔸 Код: {code['code']}\n"
            f"🏷️ Мероприятие: {code['event_name']}\n"
            f"💵 Баллы: {code['points']} ({'➕' if code['is_income'] else '➖'})\n"
            f"📊 Количество использований: {code['usage_count']}"  # Добавляем количество использований
        )

    await message.answer("\n".join(response), reply_markup=organizer_menu())


# Обработчики для создания кода мероприятия
@router.message(F.text == "🔑 Код к мероприятию")
async def cmd_manage_code(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=main_menu())
        return

    events = await get_events()
    if not events:
        return await message.answer("❌ Нет мероприятий", reply_markup=organizer_menu())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{e['id']}. {e['name']}", callback_data=f"event_{e['id']}")]
        for e in events
    ])

    await message.answer("📋 Выберите мероприятие:", reply_markup=keyboard)
    await state.set_state(OrganizerStates.waiting_for_event_id)

@router.callback_query(OrganizerStates.waiting_for_event_id, F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[1])
    event = await get_events(event_id)

    if not event:
        await callback.message.answer("❌ Мероприятие не найдено")
        return await state.clear()

    await state.update_data(event_id=event_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить код", callback_data="action_add")],
        [InlineKeyboardButton(text="Удалить код", callback_data="action_delete")]
    ])

    await callback.message.answer(
        f"🛠 Управление кодами для: {event['name']}\n"
        "➡️ Выберите действие:",
        reply_markup=keyboard
    )
    await state.set_state(OrganizerStates.waiting_for_action)
    await callback.answer()

@router.callback_query(OrganizerStates.waiting_for_action, F.data.startswith("action_"))
async def select_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]

    if action == "add":
        await callback.message.answer("➡️ Введите количество баллов:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(OrganizerStates.waiting_for_code_points)
    elif action == "delete":
        codes = await get_codes_usage(event_id=(await state.get_data())['event_id'])  # Используем get_codes_usage для получения всех кодов
        if not codes:
            return await callback.message.answer("❌ Нет активных кодов для удаления", reply_markup=organizer_menu())

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{code['code']} ({code['points']} баллов, использовано: {code['usage_count']} раз, {'Пополнение' if code['is_income'] else 'Списание'})",
                    callback_data=f"delete_code_{code['code']}"
                )
            ]
            for code in codes
        ])

        await callback.message.answer("📋 Выберите код для удаления:", reply_markup=keyboard)
        await state.set_state(OrganizerStates.waiting_for_code_to_delete)

    await callback.answer()


@router.message(OrganizerStates.waiting_for_code_points)
async def input_points(message: types.Message, state: FSMContext):
    try:
        points = abs(int(message.text))
        if points == 0:
            raise ValueError
        await state.update_data(points=points)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнение ➕", callback_data="type_income")],
            [InlineKeyboardButton(text="Списание ➖", callback_data="type_outcome")]
        ])

        await message.answer("🔧 Выберите тип операции:", reply_markup=keyboard)
        await state.set_state(OrganizerStates.waiting_for_code_type)
    except (ValueError, TypeError):
        await message.answer("❌ Введите целое число больше 0")

@router.callback_query(OrganizerStates.waiting_for_code_type, F.data.startswith("type_"))
async def select_type(callback: types.CallbackQuery, state: FSMContext):
    operation_type = callback.data.split("_")[1]
    is_income = operation_type == "income"

    await state.update_data(is_income=is_income)
    await callback.message.answer("🔠 Введите уникальный код (латинские буквы/цифры):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(OrganizerStates.waiting_for_code)
    await callback.answer()

@router.message(OrganizerStates.waiting_for_code)
async def input_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    code = message.text.strip().upper()

    if not code.isalnum() or len(code) < 4:
        return await message.answer(
            "❌ Код должен содержать только латинские буквы/цифры и быть не короче 4 символов"
        )

    try:
        await add_code_to_event(
            event_id=data['event_id'],
            code=code,
            points=data['points'],
            is_income=data['is_income']
        )
        operation_type = "➕" if data['is_income'] else "➖"
        await message.answer(
            f"✅ Код успешно создан!\n"
            f"🔑 {code} | {operation_type} {data['points']} баллов",
            reply_markup=organizer_menu()
        )
    except asyncpg.exceptions.UniqueViolationError:
        await message.answer("❌ Этот код уже существует", reply_markup=organizer_menu())
    finally:
        await state.clear()

@router.callback_query(OrganizerStates.waiting_for_code_to_delete, F.data.startswith("delete_code_"))
async def select_code_to_delete(callback: types.CallbackQuery, state: FSMContext):
    code_to_delete = callback.data.split("_")[2]

    try:
        await delete_code(code_to_delete)
        await callback.message.answer(f"✅ Код {code_to_delete} успешно удален!", reply_markup=organizer_menu())
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при удалении кода: {str(e)}", reply_markup=organizer_menu())
    finally:
        await state.clear()
    await callback.answer()

@router.callback_query(OrganizerStates.waiting_for_event_to_delete, F.data.startswith("delete_event_"))
async def delete_event_callback(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])

    try:
        await delete_event(event_id)
        await callback.message.answer(f"✅ Мероприятие успешно удалено!", reply_markup=organizer_menu())
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при удалении мероприятия: {str(e)}", reply_markup=organizer_menu())
    finally:
        await state.clear()
    await callback.answer()
