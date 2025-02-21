from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.database import add_admin, is_admin, send_notification

router = Router()

class OrganizerStates(StatesGroup):
    waiting_for_notification = State()
    waiting_for_admin_id = State()

# Команда /notify - отправка уведомлений студентам
@router.message(Command("notify"))
async def cmd_notify(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    await message.answer("Введите текст уведомления:")
    await state.set_state(OrganizerStates.waiting_for_notification)

# Обработчик для состояния ожидания уведомления
@router.message(OrganizerStates.waiting_for_notification)
async def process_notify(message: types.Message, state: FSMContext):
    text = message.text
    await send_notification(text)
    await message.answer("✅ Уведомление отправлено всем студентам!")
    await state.clear()

# Команда /add_admin - добавление администратора
@router.message(Command("add_admin"))
async def cmd_add_admin(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    await message.answer("Введите ID пользователя, которого хотите добавить в администраторы:")
    await state.set_state(OrganizerStates.waiting_for_admin_id)

# Обработчик для состояния ожидания ID администратора
@router.message(OrganizerStates.waiting_for_admin_id)
async def process_add_admin(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Попробуйте ещё раз.")
        return

    await add_admin(user_id)
    await message.answer(f"✅ Пользователь с ID {user_id} добавлен в администраторы!")
    await state.clear()
