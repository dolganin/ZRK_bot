from aiogram import Router, types
from aiogram.filters import Command
from keyboards.student_keyboards import main_menu

router = Router()

# Команда /home - возвращает пользователя в главное меню
@router.message(Command("home"))
async def cmd_home(message: types.Message):
    await message.answer("Главное меню", reply_markup=main_menu())

# Обработчик неизвестных команд
@router.message()
async def unknown_command(message: types.Message):
    await message.answer("Неизвестная команда. Используйте меню или команду /help.")
