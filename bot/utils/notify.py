from aiogram import Bot
from utils.database import get_all_students
from utils.config import TOKEN

bot = Bot(token=TOKEN)

async def send_broadcast(message):
    students = await get_all_students()
    for user_id in students:
        await bot.send_message(user_id, message)
