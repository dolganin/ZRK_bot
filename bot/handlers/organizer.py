from aiogram import Router, types
from aiogram.filters import Command
from bot.utils.database import send_notification

router = Router()

# Команда /notify - отправка уведомлений студентам
@router.message(Command("notify"))
async def cmd_notify(message: types.Message):
    await message.answer("Введите текст уведомления:")

@router.message()
async def process_notify(message: types.Message):
    text = message.text
    await send_notification(text)
    await message.answer("✅ Уведомление отправлено всем студентам!")
