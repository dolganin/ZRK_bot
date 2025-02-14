import asyncio
from aiogram import BaseMiddleware
from aiogram.types import Message

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=1):
        self.rate_limit = rate_limit
        self.users = {}

    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        if user_id in self.users and self.users[user_id] > asyncio.get_event_loop().time():
            return await event.answer("❌ Слишком часто! Подождите немного.")
        self.users[user_id] = asyncio.get_event_loop().time() + self.rate_limit
        return await handler(event, data)
