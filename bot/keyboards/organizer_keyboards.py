from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def organizer_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Просмотр рейтинга"), KeyboardButton(text="Отправить уведомление")]
        ],
        resize_keyboard=True
    )
