from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.student_keyboards import main_menu
from utils.database import is_admin, get_balance, register_student
from keyboards.organizer_keyboards import organizer_menu

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = Router()

# Стейт-машина для регистрации
class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_course = State()
    waiting_for_faculty = State()

# Команда /start - приветствие и запрос регистрации
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()  # Получаем текущее состояние пользователя
    # Приветственное сообщение
    text = "Привет! Добро пожаловать в Карьерный квест НГУ 2025! 👋\n\n" \
           "Чтобы начать, нужно зарегистрироваться. Пожалуйста, введи свое ФИО."

    # Переходим в состояние ожидания ФИО
    await message.answer(text)
    await state.set_state(RegistrationState.waiting_for_name)


@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    # Сохраняем введенное ФИО
    user_name = message.text
    await state.update_data(name=user_name)

    # Запрашиваем курс с кнопками
    text = "Отлично, теперь выбери свой курс:"

    # Создаем клавиатуру для курсов
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 курс"), KeyboardButton(text="2 курс")],
            [KeyboardButton(text="3 курс"), KeyboardButton(text="4 курс")],
            [KeyboardButton(text="5 курс"), KeyboardButton(text="Магистратура")],
            [KeyboardButton(text="Аспирантура"), KeyboardButton(text="Выпускник")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_course)


# Обработка курса
@router.message(RegistrationState.waiting_for_course)
async def process_course(message: types.Message, state: FSMContext):
    course = message.text

    # Проверяем, что курс правильный
    valid_courses = [
        "1 курс", "2 курс", "3 курс", "4 курс", "5 курс",
        "Магистратура", "Аспирантура", "Выпускник"
    ]
    if course not in valid_courses:
        await message.answer("Пожалуйста, выбери курс из предложенных вариантов.")
        return

    # Сохраняем курс
    await state.update_data(course=course)

    # Создаем клавиатуру для факультетов
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ИИР"), KeyboardButton(text="ФЕН")],
            [KeyboardButton(text="ФФ"), KeyboardButton(text="ИМПЗ")],
            [KeyboardButton(text="ФИТ"), KeyboardButton(text="ММФ")],
            [KeyboardButton(text="ГИ"), KeyboardButton(text="ФИЯ")],
            [KeyboardButton(text="ИФП"), KeyboardButton(text="ГГФ")],
            [KeyboardButton(text="ЭФ"), KeyboardButton(text="ПИШ")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    text = "Теперь выбери факультет:"
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_faculty)


# Обработка факультета
@router.message(RegistrationState.waiting_for_faculty)
async def process_faculty(message: types.Message, state: FSMContext):
    faculty = message.text
    valid_faculties = [
        "ИИР", "ФЕН", "ФФ", "ИМПЗ", "ФИТ", "ММФ",
        "ГИ", "ФИЯ", "ИФП", "ГГФ", "ЭФ", "ПИШ"
    ]
    
    if faculty not in valid_faculties:
        await message.answer("Пожалуйста, выбери факультет из предложенных вариантов.")
        return

    # Сохраняем факультет
    await state.update_data(faculty=faculty)

    # Получаем все данные
    user_data = await state.get_data()
    name = user_data['name']
    course = user_data['course']
    faculty = user_data['faculty']

    # Сохраняем данные в базу данных
    user_id = message.from_user.id
    username = message.from_user.username

    logger.info(user_id)

    await register_student(user_id, name, username, course, faculty)

    # Подтверждаем регистрацию
    text = f"Регистрация завершена! 🎉\n\n" \
           f"Ты зарегистрирован как:\n\n" \
           f"ФИО: {name}\n" \
           f"Курс: {course}\n" \
           f"Факультет: {faculty}\n\n" \
           "Теперь ты можешь участвовать в Карьерном квесте НГУ 2025! 🚀"
    
    keyboard = organizer_menu() if is_user_admin else main_menu()
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
    await state.clear()

# Команда /home - возвращает пользователя в главное меню
@router.message(Command("home"))
async def cmd_home(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)  # Получаем баланс пользователя
    is_user_admin = await is_admin(user_id)  # Проверяем, является ли пользователь админом

    # Текст сообщения
    text = (
        "📸 [Ссылка на картинку]\n\n"
        "Привет, это Карьерный квест НГУ 2025 👋\n\n"
        f"🏅 Твой баланс: *{balance}* баллов\n\n"
        "С 3 марта по 10 апреля получай баллы за активное участие в Днях карьеры НГУ "
        "и обменивай их на крутой мерч от компаний! 🚀\n\n"
        "*Как это работает?*\n"
        "✅ Посещай мастер-классы, лекции и экспресс-собеседования\n"
        "✅ Выполняй задания на стендах компаний\n"
        "✅ Набирай баллы и меняй их на подарки! 🎁\n\n"
        "Твоя цель – не только участвовать, но и попасть в топ! 💪 "
        "Чем активнее ты, тем больше баллов и крутых призов!\n\n"
        "🔹 Посмотри доступные мероприятия в программе и начинай зарабатывать баллы! 🏆"
    )

    keyboard = organizer_menu() if is_user_admin else main_menu()
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)

# Обработчик неизвестных команд
@router.message()
async def unknown_command(message: types.Message):
    await message.answer("❌ Неизвестная команда. Используйте меню или команду /help.")
