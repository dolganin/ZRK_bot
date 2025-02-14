from aiogram import Router, types
from aiogram.filters import Command
from bot.utils.database import get_balance, register_student, add_points, spend_points, get_top_students
from bot.keyboards.student_keyboards import main_menu

router = Router()

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
async def cmd_code(message: types.Message):
    await message.answer("Введите уникальный код для получения баллов:")

@router.message()
async def process_code(message: types.Message):
    user_id = message.from_user.id
    code = message.text.strip()
    points = await add_points(user_id, code)
    if points:
        await message.answer(f"✅ Код принят! Вам начислено {points} баллов.\nВаш баланс: {await get_balance(user_id)} баллов.")
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован.")

# Команда /spend - списание баллов
@router.message(Command("spend"))
async def cmd_spend(message: types.Message):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")

@router.message()
async def process_spend(message: types.Message):
    user_id = message.from_user.id
    code = message.text.strip()
    success = await spend_points(user_id, code)
    if success:
        await message.answer(f"✅ Код принят! Баллы списаны.\nВаш новый баланс: {await get_balance(user_id)} баллов.")
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован.")

# Команда /top - просмотр рейтинга
@router.message(Command("top"))
async def cmd_top(message: types.Message):
    top_list = await get_top_students()
    leaderboard = "\n".join([f"{i+1}. {name} — {points} баллов" for i, (name, points) in enumerate(top_list)])
    await message.answer(f"🔥 Топ студентов:\n{leaderboard}")
