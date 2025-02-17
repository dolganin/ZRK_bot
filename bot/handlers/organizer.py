from aiogram import Router, types
from aiogram.filters import Command
from utils.database import add_admin, is_admin

router = Router()

# Команда /notify - отправка уведомлений студентам
@router.message(Command("notify"))
async def cmd_notify(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    await message.answer("Введите текст уведомления:")

@router.message()
async def process_notify(message: types.Message):
    from utils.database import send_notification  # Условный импорт
    text = message.text
    await send_notification(text)
    await message.answer("✅ Уведомление отправлено всем студентам!")

# Команда /add_admin - добавление администратора
@router.message(Command("add_admin"))
async def cmd_add_admin(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    await message.answer("Введите ID пользователя, которого хотите добавить в администраторы:")

@router.message()
async def process_add_admin(message: types.Message):
    user_id = int(message.text.strip())
    await add_admin(user_id)
    await message.answer(f"✅ Пользователь с ID {user_id} добавлен в администраторы!")