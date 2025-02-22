from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.database import (
    get_balance, 
    register_student, 
    add_points, 
    spend_points, 
    get_top_students, 
    is_admin
)
from keyboards.student_keyboards import main_menu

router = Router()

class CodeStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_spend_code = State()

# /start — регистрация пользователя и вывод клавиатуры
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name  # Используем полное имя пользователя
    if not await register_student(user_id, user_name):
        await message.answer("Вы уже зарегистрированы!", reply_markup=main_menu())
    else:
        await message.answer("Добро пожаловать! Используйте меню для взаимодействия.", reply_markup=main_menu())

# ========== Получение баллов ==========

# Команда /code — только для администраторов
@router.message(Command("code"))
async def cmd_code(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам. Пожалуйста, используйте клавиатуру для ввода кода.")
        return
    await message.answer("Введите уникальный код для получения баллов:")
    await state.set_state(CodeStates.waiting_for_code)

# Обработчик для клавиатурной кнопки "Получить баллы" (для рядовых пользователей)
@router.message(lambda message: message.text == "Получить баллы")
async def keyboard_get_code(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для получения баллов:")
    await state.set_state(CodeStates.waiting_for_code)

# Обработка ввода кода (общая для всех, вне зависимости от способа запуска)
@router.message(CodeStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    points = await add_points(user_id, code)
    if points:
        await message.answer(
            f"✅ Код принят! Вам начислено {points} баллов.\nВаш баланс: {await get_balance(user_id)} баллов."
        )
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.")
    await state.clear()

# ========== Списание баллов ==========

# Команда /spend — списание баллов
@router.message(Command("spend"))
async def cmd_spend(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")
    await state.set_state(CodeStates.waiting_for_spend_code)

# Обработчик для клавиатурной кнопки "Потратить баллы" (для всех)
@router.message(lambda message: message.text == "Потратить баллы")
async def keyboard_spend(message: types.Message, state: FSMContext):
    await message.answer("Введите уникальный код для обмена баллов на мерч:")
    await state.set_state(CodeStates.waiting_for_spend_code)

@router.message(CodeStates.waiting_for_spend_code)
async def process_spend(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip()
    success = await spend_points(user_id, code)
    if success:
        await message.answer(
            f"✅ Код принят! Баллы списаны.\nВаш новый баланс: {await get_balance(user_id)} баллов."
        )
    else:
        await message.answer("❌ Ошибка! Код неверен или уже использован. Ожидаю следующей команды.")
    await state.clear()

# ========== Просмотр рейтинга ==========

# Команда /top — просмотр рейтинга
@router.message(Command("top"))
async def cmd_top(message: types.Message):
    top_list = await get_top_students()
    leaderboard = "\n".join([f"{i+1}. {name} — {points} баллов" for i, (name, points) in enumerate(top_list)])
    await message.answer(f"🔥 Топ студентов:\n{leaderboard}")

# Обработчик для клавиатурной кнопки "Рейтинг"
@router.message(lambda message: message.text == "Рейтинг")
async def keyboard_top(message: types.Message):
    top_list = await get_top_students()
    leaderboard = "\n".join([f"{i+1}. {name} — {points} баллов" for i, (name, points) in enumerate(top_list)])
    await message.answer(f"🔥 Топ студентов:\n{leaderboard}")

# ========== Дополнительные кнопки (Программа, Карта) ==========

@router.message(lambda message: message.text == "Программа")
async def keyboard_program(message: types.Message):
    await message.answer("Информация о программе мероприятия...")

@router.message(lambda message: message.text == "Карта")
async def keyboard_map(message: types.Message):
    await message.answer("Интерактивная карта мероприятия...")
