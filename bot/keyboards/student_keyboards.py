from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Получить баллы"), KeyboardButton(text="💸 Потратить баллы")],
            [KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="📅 Программа"), KeyboardButton(text="🗺 Карта")]
        ],
        resize_keyboard=True,
    )