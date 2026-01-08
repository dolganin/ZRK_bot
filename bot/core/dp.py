import logging
import redis.asyncio as redis
from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from handlers import student, organizer, common
from handlers.shop import router as shop_router
from handlers.organizer_codes import router as organizer_codes_router
from texts.texts_editor import router as texts_editor_router
from handlers.organizer_orders import router as organizer_orders_router
from handlers.organizer_inventory import router as organizer_inventory_router

logging.basicConfig(level=logging.INFO)

redis_client = redis.Redis(host="redis", port=6379, db=0)
storage = RedisStorage(redis_client)

dp = Dispatcher(storage=storage)

dp.include_router(student.router)
dp.include_router(shop_router)
dp.include_router(organizer.router)
dp.include_router(organizer_orders_router)
dp.include_router(organizer_codes_router)
dp.include_router(organizer_inventory_router)
dp.include_router(texts_editor_router)
dp.include_router(common.router)
