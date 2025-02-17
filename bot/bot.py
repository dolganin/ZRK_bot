import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from aioredis import Redis
from handlers import student, organizer
from utils.config import TOKEN
from utils.database import init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация подключения к Redis (для хранения состояний)
redis = Redis(host='redis', port=6379, db=0)
storage = RedisStorage(redis)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)  # Используем RedisStorage для хранения состояний

# Включаем роутеры
dp.include_router(student.router)
dp.include_router(organizer.router)

async def set_commands():
    commands = [
        BotCommand(command="/start", description="Начать"),
        BotCommand(command="/code", description="Ввести код для начисления баллов"),
        BotCommand(command="/spend", description="Ввести код для списания баллов"),
        BotCommand(command="/top", description="Посмотреть топ студентов"),
        BotCommand(command="/add_admin", description="Добавить администратора"),
        BotCommand(command="/notify", description="Отправить уведомление студентам")
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
