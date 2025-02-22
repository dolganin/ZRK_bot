import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis
from handlers import student, organizer, common

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация подключения к Redis (для хранения состояний)
redis = redis.Redis(host='redis', port=6379, db=0)
storage = RedisStorage(redis)

# Инициализация диспетчера
dp = Dispatcher(storage=storage)

# Включаем роутеры (обработчики для студентов и организаторов)
dp.include_router(student.router)
dp.include_router(organizer.router)
dp.include_router(common.router)
