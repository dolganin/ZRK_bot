from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from utils.config import TOKEN, TELEGRAM_PROXY_URL

session = AiohttpSession(proxy=TELEGRAM_PROXY_URL) if TELEGRAM_PROXY_URL else None
bot = Bot(token=TOKEN, session=session)
