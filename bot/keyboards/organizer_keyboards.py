from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


ADMIN_PANEL_TEXT = "🛠 Панель организатора"
ADMIN_BACK_TEXT = "⬅️ В панель организатора"


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


def admin_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=ADMIN_BACK_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def rating_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="10 студентов"), KeyboardButton(text="50 студентов")],
            [KeyboardButton(text="Весь список")],
            [KeyboardButton(text=ADMIN_BACK_TEXT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
