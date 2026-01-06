import logging
import redis.asyncio as redis
from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from handlers import student, organizer, common
from handlers.shop import router as shop_router

logging.basicConfig(level=logging.INFO)

redis_client = redis.Redis(host="redis", port=6379, db=0)
storage = RedisStorage(redis_client)

dp = Dispatcher(storage=storage)

dp.include_router(student.router)
dp.include_router(shop_router)
dp.include_router(organizer.router)
dp.include_router(common.router)
