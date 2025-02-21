import asyncio
import logging
from core.bot import bot
from core.dp import dp
from aiogram.types import BotCommand
from utils.database import init_db

async def set_commands():
    """Задает список команд для бота."""
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
