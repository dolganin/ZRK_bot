import logging
from aiogram import Router, types

router = Router()

@router.errors()
async def error_handler(update: types.Update, exception: Exception):
    logging.exception(f"Ошибка: {exception}")
    return True  # Бот продолжает работать
