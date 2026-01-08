import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from core.bot import bot
from keyboards.organizer_keyboards import organizer_menu
from keyboards.student_keyboards import main_menu
from texts.storage import get_template, render, send_template
from utils.database import get_balance, is_admin, is_user_registered, register_student

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_course = State()
    waiting_for_faculty = State()


COURSES = [
    "1 курс",
    "2 курс",
    "3 курс",
    "4 курс",
    "5 курс",
    "Магистратура",
    "Аспирантура",
    "Выпускник",
]

FACULTIES = [
    "ИИР",
    "ФЕН",
    "ФФ",
    "ИМПЗ",
    "ФИТ",
    "ММФ",
    "ГИ",
    "ФИЯ",
    "ИФП",
    "ГГФ",
    "ЭФ",
    "ПИШ",
]


async def role_keyboard(user_id: int):
    return organizer_menu() if await is_admin(user_id) else main_menu()


def course_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 курс"), KeyboardButton(text="2 курс")],
            [KeyboardButton(text="3 курс"), KeyboardButton(text="4 курс")],
            [KeyboardButton(text="5 курс"), KeyboardButton(text="Магистратура")],
            [KeyboardButton(text="Аспирантура"), KeyboardButton(text="Выпускник")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def faculty_keyboard():
    return ReplyKeyboardMarkup(
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


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    keyboard = await role_keyboard(user_id)

    await state.clear()

    if await is_user_registered(user_id):
        await send_template(bot, message, "start_already_registered", reply_markup=keyboard)
        return

    await send_template(bot, message, "start_intro")
    await state.set_state(RegistrationState.waiting_for_name)


@router.message(RegistrationState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_name = (message.text or "").strip()
    if not user_name:
        await send_template(bot, message, "reg_invalid_name")
        return

    await state.update_data(name=user_name)
    await send_template(bot, message, "reg_ask_course", reply_markup=course_keyboard())
    await state.set_state(RegistrationState.waiting_for_course)


@router.message(RegistrationState.waiting_for_course)
async def process_course(message: types.Message, state: FSMContext):
    course = (message.text or "").strip()

    if course not in COURSES:
        await send_template(bot, message, "reg_invalid_course")
        return

    await state.update_data(course=course)
    await send_template(bot, message, "reg_ask_faculty", reply_markup=faculty_keyboard())
    await state.set_state(RegistrationState.waiting_for_faculty)


@router.message(RegistrationState.waiting_for_faculty)
async def process_faculty(message: types.Message, state: FSMContext):
    faculty = (message.text or "").strip()

    if faculty not in FACULTIES:
        await send_template(bot, message, "reg_invalid_faculty")
        return

    await state.update_data(faculty=faculty)

    user_data = await state.get_data()
    name = user_data.get("name")
    course = user_data.get("course")

    user_id = message.from_user.id
    username = message.from_user.username

    await register_student(user_id, name, username, course, faculty)

    keyboard = await role_keyboard(user_id)

    await send_template(
        bot,
        message,
        "reg_done",
        reply_markup=keyboard,
        name=name,
        course=course,
        faculty=faculty,
    )

    await state.clear()


@router.message(Command("home"))
async def cmd_home(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    keyboard = await role_keyboard(user_id)

    tpl = await get_template("home_caption")
    caption = render(tpl.get("text", ""), balance=balance)

    if tpl.get("photo"):
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=tpl["photo"],
            caption=caption if caption else None,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    await message.answer(
        caption,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.message()
async def unknown_command(message: types.Message):
    keyboard = await role_keyboard(message.from_user.id)
    await send_template(bot, message, "unknown_command", reply_markup=keyboard)
