from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from utils.database import get_balance, register_student, add_points, spend_points, get_top_students
from keyboards.student_keyboards import main_menu

router = Router()
storage = MemoryStorage()

class CodeStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_spend_code = State()

# Команда /start - регистрация пользователя
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if not await register_student(user_id):
        await message.answer("Вы уже зарегистрированы!", reply_markup=main_menu())
    else:
        await message.answer("Добро пожаловать! Используйте меню для взаимодействия.")

# Команда /code - начисление баллов
@router.message(Command("code"))
async def cmd_code(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для получения баллов:")
    await state.set_state(CodeStates.waiting_for_code)

@router.message(CodeStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    points = await add_points(user_id, code)
    if points:
        await message.answer(f"✅ Код принят! Вам начислено {points} баллов.\nВаш баланс: {await get_balance(user_id)} баллов.")
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.")
    await state.clear()

# Команда /spend - списание баллов
@router.message(Command("spend"))
async def cmd_spend(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")
    await state.set_state(CodeStates.waiting_for_spend_code)

@router.message(CodeStates.waiting_for_spend_code)
async def process_spend(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    success = await spend_points(user_id, code)
    if success:
        await message.answer(f"✅ Код принят! Баллы списаны.\nВаш новый баланс: {await get_balance(user_id)} баллов.")
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.")
    await state.clear()

# Команда /top - просмотр рейтинга
@router.message(Command("top"))
async def cmd_top(message: types.Message):
    top_list = await get_top_students()
    leaderboard = "\n".join([f"{i+1}. {name} — {points} баллов" for i, (name, points) in enumerate(top_list)])
    await message.answer(f"🔥 Топ студентов:\n{leaderboard}")
