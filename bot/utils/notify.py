from aiogram import Bot
from bot.utils.database import get_all_students
from bot.utils.config import TOKEN

bot = Bot(token=TOKEN)

async def send_broadcast(message):
    students = await get_all_students()
    for user_id in students:
        await bot.send_message(user_id, message)
