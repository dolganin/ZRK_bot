import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from handlers import student, organizer
from utils.config import TOKEN
from utils.database import init_db

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
    print("🔄 Настройка базы данных...")
    await init_db()  # Создает таблицы
    print("🚀 База данных готова!")
    
    await set_commands()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
