from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from utils.database import (
    get_balance, 
    add_points, 
    spend_points, 
    get_all_students_rating, 
    is_admin
)
from keyboards.student_keyboards import main_menu

router = Router()

class CodeStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_spend_code = State()

# ========== Получение баллов ==========

@router.message(lambda message: message.text == "⬅️ На главную")
async def go_home(message: types.Message, state: FSMContext):
    """Возвращает пользователя в главное меню и очищает состояние."""
    await state.clear()
    await message.answer("🏠 *Вернулся в главное меню*", parse_mode="Markdown", reply_markup=main_menu())

# Команда /code — только для администраторов
@router.message(Command("code"))
async def cmd_code(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам. Пожалуйста, используйте клавиатуру для ввода кода.", reply_markup=main_menu())
        return
    await message.answer("Введите уникальный код для получения баллов:")
    await state.set_state(CodeStates.waiting_for_code)

# Обработчик для клавиатурной кнопки "Получить баллы" (для рядовых пользователей)
@router.message(lambda message: message.text == "💎 Получить баллы")
async def keyboard_get_code(message: types.Message, state: FSMContext):
    text = (
        "🎉 *Получить баллы*\n\n"
        "Посещай мероприятия *Дней карьеры* и выполняй задания от работодателей, "
        "чтобы зарабатывать баллы! Ты сможешь обменять их на крутой мерч уже *8 и 10 апреля* 🎁\n\n"
        "🔢 *Введи уникальный код ниже:*"
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ На главную")]],
        resize_keyboard=True
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

    await state.set_state(CodeStates.waiting_for_code)

# Обработка ввода кода (общая для всех, вне зависимости от способа запуска)
@router.message(CodeStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):

    if message.text == "⬅️ На главную":
        await go_home(message, state)
        return
    
    user_id = message.from_user.id
    code = message.text.strip()
    points = await add_points(user_id, code)
    if points:
        await message.answer(
            f"✅ Код принят! Вам начислено {points} баллов.\nВаш баланс: {await get_balance(user_id)} баллов.", reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.", reply_markup=main_menu())
    await state.clear()

# ========== Списание баллов ==========

# Команда /spend — списание баллов
@router.message(Command("spend"))
async def cmd_spend(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")
    await state.set_state(CodeStates.waiting_for_spend_code)

# Обработчик для клавиатурной кнопки "Потратить баллы" (для всех)
@router.message(lambda message: message.text == "💸 Потратить баллы")
async def keyboard_spend(message: types.Message, state: FSMContext):
    """Информирует пользователя о возможностях обмена баллов и предлагает ввести код."""
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    text = (
    "🎁 *Потратить баллы*\n\n"
    "Обменивай свои баллы на эксклюзивный мерч от работодателей на *стендовых сессиях Дней карьеры*:\n"
    "📅 *8 апреля* с *15:00* до *19:00* в *Лабораторном корпусе НГУ*\n"
    "📅 *10 апреля* с *15:00* до *19:00* в *Учебном корпусе НГУ*\n\n"
    f"💰 *Твой баланс:* {balance} баллов\n\n"
    "🔢 *Введи уникальный код ниже:*"
)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ На главную")]],
        resize_keyboard=True
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(CodeStates.waiting_for_spend_code)

@router.message(CodeStates.waiting_for_spend_code)
async def process_spend(message: types.Message, state: FSMContext):

    if message.text == "⬅️ На главную":
        await go_home(message, state)
        return
    
    user_id = message.from_user.id
    code = message.text.strip()
    success = await spend_points(user_id, code)
    if success:
        await message.answer(
            f"✅ Код принят! Баллы списаны.\nВаш новый баланс: {await get_balance(user_id)} баллов.", reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.", reply_markup=main_menu())
    await state.clear()

# ========== Просмотр рейтинга ==========

# Команда /top — просмотр рейтинга
@router.message(Command("top"))
async def cmd_top(message: types.Message):
    students = await get_all_students_rating(user_id=message.from_user.id)
    response = ["🔥 Топ студентов\n"+
            "Посещай мероприятия Дней карьеры и выполняй задания от работодателей, чтобы получить больше баллов.\n"+
            "Лидеры рейтинга получат особые призы от Центра развития карьеры:\n\n"]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ На главную")]],
        resize_keyboard=True
    )

    await message.answer("\n".join(response), reply_markup=keyboard)

# Обработчик для клавиатурной кнопки "Рейтинг"
@router.message(lambda message: message.text == "🏆 Рейтинг")
async def keyboard_top(message: types.Message):
    students = await get_all_students_rating(user_id=message.from_user.id)
    response = ["🔥 Топ студентов\n"+
                "Посещай мероприятия Дней карьеры и выполняй задания от работодателей, чтобы получить больше баллов.\n"+
                "Лидеры рейтинга получат особые призы от Центра развития карьеры:\n\n"]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ На главную")]],
        resize_keyboard=True
    )

    await message.answer("\n".join(response), reply_markup=keyboard)

# ========== Дополнительные кнопки (Программа, Карта) ==========


@router.message(lambda message: message.text == "📅 Программа")
async def keyboard_program(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть программу", url="https://t.me/careerdaynsu2025")]
    ])
    await message.answer("Информацию о программе мероприятия ты всегда можешь найти в нашей группе:", reply_markup=keyboard)

@router.message(lambda message: message.text == "🗺 Карта")
async def keyboard_map(message: types.Message):
    await message.answer("Интерактивная карта мероприятия...", reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    if await is_admin(user_id):
        help_text = (
            "🛠 Админская справка:\n\n"
            "/start — регистрация и вывод клавиатуры\n"
            "/code — ввести код для начисления баллов\n"
            "/spend — ввести код для списания баллов\n"
            "📊 Рейтинг — просмотр рейтинга, выведется весь топ, аккуратнее\n"
            "👥 Добавить админа — добавить нового администратора по id (вдруг вы его знаете)\n"
            "📢 Уведомление — отправить уведомление всем студентам (НЕ ПРОЖИМАЙТЕ ПРОСТО ТАК, ОТПРАВИТ УВЕДОМЛЕНИЕ ВСЕМ!!!)\n"
            "🔑 Создать код — генерация уникального кода (сгенерирует код с помощью SHA256)\n"
            "🎯 Мероприятие — управление мероприятиями (добавление/удаление)\n"
            "🔑 Код к мероприятию — привязка кода к мероприятию для списания/пополнения баллов\n"
            "📜 Активные коды - список ВСЕХ кодов, что не удалены и параметры по ним (например, кол-во использований)\n"
            "\nИспользуйте клавиатуру для быстрого доступа к основным функциям."
        )
    else:
        help_text = (
            "📚 Справка для пользователя:\n\n"
            "/start — регистрация и вывод клавиатуры\n"
            "/code — ввести код для получения баллов (через клавиатуру)\n"
            "/spend — ввести код для списания баллов (через клавиатуру)\n"
            "/top — просмотр рейтинга\n"
            "\nИспользуйте клавиатуру для быстрого доступа к функциям бота."
        )
    await message.answer(help_text, parse_mode="HTML", reply_markup=main_menu())
