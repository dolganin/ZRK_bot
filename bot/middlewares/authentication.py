from aiogram import BaseMiddleware
from aiogram.types import Message
from utils.database import is_organizer

class RoleMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        if await is_organizer(user_id):
            return await handler(event, data)
        return await event.answer("❌ У вас нет прав для выполнения этой команды.")
