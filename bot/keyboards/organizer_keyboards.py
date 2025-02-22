from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def organizer_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Рейтинг"), KeyboardButton(text="📢 Уведомление")],
            [KeyboardButton(text="🔑 Создать код"), KeyboardButton(text="🎯 Мероприятие")],
            [KeyboardButton(text="👥 Добавить админа"), KeyboardButton(text="📜 Активные коды")],
            [KeyboardButton(text="🔑 Код к мероприятию")]
        ],
        resize_keyboard=True
    )
