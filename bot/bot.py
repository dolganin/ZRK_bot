import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand, BotCommandScopeChat, Message
from aiogram.filters import Command, CommandStart
from core.bot import bot   # Инициализация бота
from core.dp import dp     # Инициализация диспетчера
from utils.database import init_db
from aiogram import Router

logging.basicConfig(level=logging.INFO)

router = Router()

async def set_commands_for_chat():
    # Теперь все пользователи получат одинаковые команды
    base_commands = [
        BotCommand(command="/help", description="Вывести справку помощи"),
        BotCommand(command="/home", description="Вернуться домой")
        # Можно добавить другие команды, которые будут доступны всем
    ]
    
    await bot.set_my_commands(base_commands)

async def main():
    print("🔄 Настройка базы данных...")
    await init_db()
    print("🚀 База данных готова!")

    await set_commands_for_chat()
    
    dp.include_router(router)
    
    # Убедитесь, что все middleware и другие настройки правильно подключены
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
