import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from core.bot import bot
from keyboards.student_keyboards import main_menu
from keyboards.organizer_keyboards import organizer_menu
from utils.database import is_admin, get_balance, register_student, is_user_registered
from texts.storage import get_template, render

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
        tpl = await get_template("start_already_registered")
        await message.answer(tpl["text"], reply_markup=main_menu())
        return

    tpl = await get_template("start_intro")
    await message.answer(tpl["text"])
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
            [KeyboardButton(text="Аспирантура"), KeyboardButton(text="Выпускник")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    tpl = await get_template("reg_ask_course")
    await message.answer(tpl["text"], reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_course)

@router.message(RegistrationState.waiting_for_course)
async def process_course(message: types.Message, state: FSMContext):
    course = message.text
    valid_courses = [
        "1 курс", "2 курс", "3 курс", "4 курс", "5 курс",
        "Магистратура", "Аспирантура", "Выпускник",
    ]
    if course not in valid_courses:
        tpl = await get_template("reg_invalid_course")
        await message.answer(tpl["text"])
        return

    await state.update_data(course=course)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ИИР"), KeyboardButton(text="ФЕН")],
            [KeyboardButton(text="ФФ"), KeyboardButton(text="ИМПЗ")],
            [KeyboardButton(text="ФИТ"), KeyboardButton(text="ММФ")],
            [KeyboardButton(text="ГИ"), KeyboardButton(text="ФИЯ")],
            [KeyboardButton(text="ИФП"), KeyboardButton(text="ГГФ")],
            [KeyboardButton(text="ЭФ"), KeyboardButton(text="ПИШ")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    tpl = await get_template("reg_ask_faculty")
    await message.answer(tpl["text"], reply_markup=keyboard)
    await state.set_state(RegistrationState.waiting_for_faculty)

@router.message(RegistrationState.waiting_for_faculty)
async def process_faculty(message: types.Message, state: FSMContext):
    faculty = message.text
    valid_faculties = [
        "ИИР", "ФЕН", "ФФ", "ИМПЗ", "ФИТ", "ММФ",
        "ГИ", "ФИЯ", "ИФП", "ГГФ", "ЭФ", "ПИШ",
    ]

    if faculty not in valid_faculties:
        tpl = await get_template("reg_invalid_faculty")
        await message.answer(tpl["text"])
        return

    await state.update_data(faculty=faculty)

    user_data = await state.get_data()
    name = user_data["name"]
    course = user_data["course"]

    user_id = message.from_user.id
    username = message.from_user.username

    await register_student(user_id, name, username, course, faculty)

    tpl = await get_template("reg_done")
    text = render(tpl["text"], name=name, course=course, faculty=faculty)
    await message.answer(text, reply_markup=main_menu())
    await state.clear()

@router.message(Command("home"))
async def cmd_home(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    admin = await is_admin(user_id)

    tpl = await get_template("home_caption")
    caption = render(tpl["text"], balance=balance)

    keyboard = organizer_menu() if admin else main_menu()

    if tpl["photo"]:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=tpl["photo"],
            caption=caption,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    image_path = "./hello.jpg"
    with open(image_path, "rb") as f:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=types.BufferedInputFile(f.read(), filename=image_path),
            caption=caption,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

@router.message()
async def unknown_command(message: types.Message):
    tpl = await get_template("unknown_command")
    await message.answer(tpl["text"], reply_markup=main_menu())
