import logging
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

from core.bot import bot
from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu
from utils.database import is_admin, get_balance, register_student, is_user_registered

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_course = State()
    waiting_for_faculty = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_user_registered(user_id):
        await message.answer("Вы уже зарегистрированы в Карьерном квесте НГУ 2025!", reply_markup=main_menu())
        return

    text = (
        "Привет! Добро пожаловать в Карьерный квест НГУ 2025! 👋\n\n"
        "Чтобы начать, нужно зарегистрироваться. Пожалуйста, введи свое ФИО."
    )
    await message.answer(text)
    await state.set_state(RegistrationState.waiting_for_name)

@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_name = message.text
    await state.update_data(name=user_name)

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

    await message.answer("Отлично, теперь выбери свой курс:", reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_course)

@router.message(RegistrationState.waiting_for_course)
async def process_course(message: types.Message, state: FSMContext):
    course = message.text
    valid_courses = [
        "1 курс", "2 курс", "3 курс", "4 курс", "5 курс",
        "Магистратура", "Аспирантура", "Выпускник"
    ]
    if course not in valid_courses:
        await message.answer("Пожалуйста, выбери курс из предложенных вариантов.")
        return

    await state.update_data(course=course)

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

    await message.answer("Теперь выбери факультет:", reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_faculty)

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

    await state.update_data(faculty=faculty)

    user_data = await state.get_data()
    name = user_data["name"]
    course = user_data["course"]

    user_id = message.from_user.id
    username = message.from_user.username

    await register_student(user_id, name, username, course, faculty)

    text = (
        "Регистрация завершена! 🎉\n\n"
        "Ты зарегистрирован как:\n\n"
        f"ФИО: {name}\n"
        f"Курс: {course}\n"
        f"Факультет: {faculty}\n\n"
        "Теперь ты можешь участвовать в Карьерном квесте НГУ 2025! 🚀"
    )
    await message.answer(text, reply_markup=main_menu())
    await state.clear()

@router.message(Command("home"))
async def cmd_home(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    admin = await is_admin(user_id)

    text = (
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

    keyboard = organizer_menu() if admin else main_menu()
    image_path = "./hello.jpg"

    with open(image_path, "rb") as file:
        photo = BufferedInputFile(file.read(), filename=image_path)
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

@router.message()
async def unknown_command(message: types.Message):
    await message.answer("❌ Неизвестная команда. Используйте меню или команду /help.", reply_markup=main_menu())
