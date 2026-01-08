from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from keyboards.organizer_keyboards import organizer_menu
from keyboards.student_keyboards import main_menu
from utils.database import get_balance, add_points, spend_points, get_all_students_rating, is_admin
from texts.storage import get_template, render

router = Router()

class CodeStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_spend_code = State()

@router.message(lambda message: message.text == "⬅️ На главную")
async def go_home(message: types.Message, state: FSMContext):
    await state.clear()
    tpl = await get_template("go_home")
    await message.answer(tpl["text"], parse_mode="Markdown", reply_markup=main_menu())

@router.message(Command("code"))
async def cmd_code(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer(
            "Эта команда доступна только администраторам. Пожалуйста, используйте клавиатуру для ввода кода.",
            reply_markup=main_menu(),
        )
        return
    await message.answer("Введите уникальный код для получения баллов:")
    await state.set_state(CodeStates.waiting_for_code)

@router.message(lambda message: message.text == "💎 Получить баллы")
async def keyboard_get_code(message: types.Message, state: FSMContext):
    tpl = await get_template("get_points_prompt")
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ На главную")]], resize_keyboard=True)
    await message.answer(tpl["text"], parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(CodeStates.waiting_for_code)

@router.message(CodeStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    if message.text == "⬅️ На главную":
        await go_home(message, state)
        return

    user_id = message.from_user.id
    code = message.text.strip()
    points = await add_points(user_id, code)
    if points:
        tpl = await get_template("get_points_success")
        text = render(tpl["text"], points=points, balance=await get_balance(user_id))
        await message.answer(text, reply_markup=main_menu())
    else:
        tpl = await get_template("get_points_fail")
        await message.answer(tpl["text"], reply_markup=main_menu())
    await state.clear()

@router.message(Command("spend"))
async def cmd_spend(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")
    await state.set_state(CodeStates.waiting_for_spend_code)

@router.message(lambda message: message.text == "💸 Потратить баллы")
async def keyboard_spend(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    tpl = await get_template("spend_points_prompt")
    text = render(tpl["text"], balance=balance)

    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ На главную")]], resize_keyboard=True)
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
        tpl = await get_template("spend_points_success")
        text = render(tpl["text"], balance=await get_balance(user_id))
        await message.answer(text, reply_markup=main_menu())
    else:
        tpl = await get_template("spend_points_fail")
        await message.answer(tpl["text"], reply_markup=main_menu())
    await state.clear()

@router.message(Command("top"))
async def cmd_top(message: types.Message):
    students = await get_all_students_rating(user_id=message.from_user.id)
    header_tpl = await get_template("top_header")
    response = [header_tpl["text"]]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")

    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ На главную")]], resize_keyboard=True)
    await message.answer("\n".join(response), reply_markup=keyboard)

@router.message(lambda message: message.text == "🏆 Рейтинг")
async def keyboard_top(message: types.Message):
    students = await get_all_students_rating(user_id=message.from_user.id)
    header_tpl = await get_template("top_header")
    response = [header_tpl["text"]]
    for idx, student in enumerate(students, 1):
        response.append(f"{idx}. {student['name']} - {student['balance']} баллов")

    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ На главную")]], resize_keyboard=True)
    await message.answer("\n".join(response), reply_markup=keyboard)

@router.message(lambda message: message.text == "📅 Программа")
async def keyboard_program(message: types.Message):
    tpl = await get_template("program_text")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть программу", url="https://t.me/careerdaynsu2025")]]
    )
    await message.answer(tpl["text"], reply_markup=keyboard)

@router.message(lambda message: message.text == "🗺 Карта")
async def keyboard_map(message: types.Message):
    tpl = await get_template("map_text")
    await message.answer(tpl["text"], reply_markup=main_menu())

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    is_user_admin = await is_admin(user_id)

    tpl = await get_template("help_admin" if is_user_admin else "help_user")
    keyboard = organizer_menu() if is_user_admin else main_menu()
    await message.answer(tpl["text"], reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
