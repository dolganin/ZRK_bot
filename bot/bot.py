import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand, BotCommandScopeChat, Message
from aiogram.filters import Command, CommandStart  # Добавляем нужные фильтры
from core.bot import bot   # Инициализация бота
from core.dp import dp     # Инициализация диспетчера
from utils.database import init_db, is_admin
from aiogram import Router

logging.basicConfig(level=logging.INFO)

router = Router()

async def set_commands_for_chat(chat_id: int):
    base_commands = [
        BotCommand(command="/start", description="Начать"),
        BotCommand(command="/code", description="Ввести код для начисления баллов"),
        BotCommand(command="/spend", description="Ввести код для списания баллов"),
        BotCommand(command="/top", description="Посмотреть топ студентов")
    ]
    
    if await is_admin(chat_id):
        base_commands.append(BotCommand(command="/add_admin", description="Добавить администратора"))
        base_commands.append(BotCommand(command="/notify", description="Отправить уведомление студентам"))
    
    await bot.set_my_commands(base_commands, scope=BotCommandScopeChat(chat_id=chat_id))

# Используем новый синтаксис с Command
@router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = message.chat.id
    await set_commands_for_chat(chat_id)
    await message.answer("Добро пожаловать! Команды обновлены в зависимости от ваших прав.")

async def main():
    print("🔄 Настройка базы данных...")
    await init_db()
    print("🚀 База данных готова!")
    
    dp.include_router(router)
    
    # Убедитесь, что все middleware и другие настройки правильно подключены
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())