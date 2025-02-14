import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from bot.handlers import student, organizer
from bot.utils.config import TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Регистрация обработчиков
dp.include_router(student.router)
dp.include_router(organizer.router)

# Установка команд
async def set_commands():
    commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/code", description="Получить баллы"),
        BotCommand(command="/spend", description="Потратить баллы"),
        BotCommand(command="/top", description="Просмотр рейтинга"),
        BotCommand(command="/notify", description="Отправить уведомление (организаторы)")
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
