from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from core.bot import bot
from keyboards.organizer_keyboards import organizer_menu, ADMIN_BACK_TEXT
from keyboards.student_keyboards import main_menu
from utils.database import get_balance, add_points, get_all_students_rating, is_admin
from texts.storage import send_template

router = Router()
HOME_TEXT = "⬅️ На главную"

class CodeStates(StatesGroup):
    waiting_for_code = State()

async def role_home_button(user_id: int) -> str:
    return ADMIN_BACK_TEXT if await is_admin(user_id) else HOME_TEXT


async def role_home_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=await role_home_button(user_id))]],
        resize_keyboard=True,
    )


async def role_main_menu(user_id: int):
    return organizer_menu() if await is_admin(user_id) else main_menu()


@router.message(lambda message: message.text in {HOME_TEXT, ADMIN_BACK_TEXT})
async def go_home(message: types.Message, state: FSMContext):
    await state.clear()
    await send_template(
        bot,
        message,
        "go_home",
        reply_markup=await role_main_menu(message.from_user.id),
        parse_mode="Markdown",
    )

@router.message(Command("code"))
async def cmd_code(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer(
            "Эта команда доступна только администраторам. Пожалуйста, используйте клавиатуру для ввода кода.",
            reply_markup=main_menu(),
        )
        return
    await message.answer(
        "Введите уникальный код для получения баллов:",
        reply_markup=await role_home_keyboard(message.from_user.id),
    )
    await state.set_state(CodeStates.waiting_for_code)

@router.message(lambda message: message.text == "💎 Получить баллы")
async def keyboard_get_code(message: types.Message, state: FSMContext):
    await send_template(
        bot,
        message,
        "get_points_prompt",
        reply_markup=await role_home_keyboard(message.from_user.id),
        parse_mode="Markdown",
    )
    await state.set_state(CodeStates.waiting_for_code)

@router.message(CodeStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    if message.text in {HOME_TEXT, ADMIN_BACK_TEXT}:
        await go_home(message, state)
        return

    user_id = message.from_user.id
    code = (message.text or "").strip()
    points = await add_points(user_id, code)

    if points:
        await send_template(
            bot,
            message,
            "get_points_success",
            reply_markup=await role_main_menu(user_id),
            points=points,
            balance=await get_balance(user_id),
        )
    else:
        await send_template(bot, message, "get_points_fail", reply_markup=await role_main_menu(user_id))

    await state.clear()

@router.message(Command("top"))
async def cmd_top(message: types.Message):
    students = await get_all_students_rating(limit=10)
    response = [
        "🔥 Топ студентов\n"
        "Посещай мероприятия Дней карьеры и выполняй задания от работодателей, чтобы получить больше баллов.\n"
        "Лидеры рейтинга получат особые призы от Центра развития карьеры:\n\n"
    ]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")

    await message.answer("\n".join(response), reply_markup=await role_home_keyboard(message.from_user.id))

@router.message(lambda message: message.text == "🏆 Рейтинг")
async def keyboard_top(message: types.Message):
    students = await get_all_students_rating(limit=10)
    response = [
        "🔥 Топ студентов\n"
        "Посещай мероприятия Дней карьеры и выполняй задания от работодателей, чтобы получить больше баллов.\n"
        "Лидеры рейтинга получат особые призы от Центра развития карьеры:\n\n"
    ]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")

    await message.answer("\n".join(response), reply_markup=await role_home_keyboard(message.from_user.id))

@router.message(lambda message: message.text == "📅 Программа")
async def keyboard_program(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть программу", url="https://t.me/careerdaynsu2025")]]
    )
    await send_template(bot, message, "program_text", reply_markup=keyboard)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    is_user_admin = await is_admin(user_id)

    key = "help_admin" if is_user_admin else "help_user"
    keyboard = organizer_menu() if is_user_admin else main_menu()

    await send_template(
        bot,
        message,
        key,
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
