from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def organizer_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Рейтинг"), KeyboardButton(text="📢 Уведомление")],
            [KeyboardButton(text="🎯 Мероприятия"), KeyboardButton(text="🔑 Коды мероприятий")],
            [KeyboardButton(text="📜 Активные коды"), KeyboardButton(text="👥 Добавить админа")],
            [KeyboardButton(text="🛒 Товары"), KeyboardButton(text="✏️ Тексты")],
            [KeyboardButton(text="✅ Выдать заказ")],
            [KeyboardButton(text="📦 Отчёт по складу")],
            [KeyboardButton(text="🗺 Редактирование карты")],
        ],
        resize_keyboard=True,
    )



def rating_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10 студентов"), KeyboardButton(text="50 студентов")],
            [KeyboardButton(text="Весь список")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
