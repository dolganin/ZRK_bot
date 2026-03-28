from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.organizer_keyboards import organizer_menu, ADMIN_PANEL_TEXT
from utils.database import is_admin
from texts.storage import list_templates, get_template, set_text, set_photo, clear_photo

router = Router()

class TextEditStates(StatesGroup):
    choosing = State()
    editing_text = State()
    editing_photo = State()

def _preview(s: str, n: int = 32):
    s = (s or "").replace("\n", " ").strip()
    return s[:n] + ("…" if len(s) > n else "")

def _list_kb(items):
    rows = []
    for it in items:
        label = f"{it['key']} — {_preview(it['text'])}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"txt:open:{it['key']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="txt:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _edit_kb(key: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"txt:edit_text:{key}")],
            [InlineKeyboardButton(text="🖼 Изменить картинку", callback_data=f"txt:edit_photo:{key}")],
            [InlineKeyboardButton(text="🧹 Убрать картинку", callback_data=f"txt:clear_photo:{key}")],
            [InlineKeyboardButton(text="⬅️ К списку", callback_data="txt:list")],
        ]
    )

@router.message(F.text == "✏️ Тексты")
async def open_texts(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    items = await list_templates()
    await state.set_state(TextEditStates.choosing)
    await message.answer("Выбери шаблон для редактирования:", reply_markup=_list_kb(items))

@router.callback_query(F.data == "txt:back")
async def back_to_menu(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Возврат в панель организатора.", reply_markup=None)
    await cb.message.answer(ADMIN_PANEL_TEXT, reply_markup=organizer_menu())
    await cb.answer()

@router.callback_query(F.data == "txt:list")
async def list_again(cb: types.CallbackQuery, state: FSMContext):
    items = await list_templates()
    await state.set_state(TextEditStates.choosing)
    await cb.message.edit_text("Выбери шаблон для редактирования:", reply_markup=_list_kb(items))
    await cb.answer()

@router.callback_query(F.data.startswith("txt:open:"))
async def open_one(cb: types.CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 2)[2]
    tpl = await get_template(key)
    text = tpl["text"] or ""
    photo = tpl["photo"]
    header = f"Шаблон: {key}\n\n"
    body = text if len(text) <= 3500 else text[:3500] + "\n…"
    footer = "\n\nКартинка: " + ("есть" if photo else "нет")
    await state.update_data(key=key)
    await cb.message.edit_text(header + body + footer, reply_markup=_edit_kb(key))
    await cb.answer()

@router.callback_query(F.data.startswith("txt:edit_text:"))
async def ask_new_text(cb: types.CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 2)[2]
    await state.update_data(key=key)
    await state.set_state(TextEditStates.editing_text)
    await cb.message.answer(f"Пришли новый текст для шаблона `{key}` одним сообщением.", parse_mode="Markdown")
    await cb.answer()

@router.message(TextEditStates.editing_text)
async def save_new_text(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    key = data.get("key")
    if not key:
        await state.clear()
        return
    await set_text(key, message.text or "")
    tpl = await get_template(key)
    text = tpl["text"] or ""
    photo = tpl["photo"]
    header = f"Обновлено: {key}\n\n"
    body = text if len(text) <= 3500 else text[:3500] + "\n…"
    footer = "\n\nКартинка: " + ("есть" if photo else "нет")
    await state.set_state(TextEditStates.choosing)
    await message.answer(header + body + footer, reply_markup=_edit_kb(key))
    await state.update_data(key=key)

@router.callback_query(F.data.startswith("txt:edit_photo:"))
async def ask_new_photo(cb: types.CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 2)[2]
    await state.update_data(key=key)
    await state.set_state(TextEditStates.editing_photo)
    await cb.message.answer(f"Пришли фото для шаблона `{key}` (обычным фото, не файлом).", parse_mode="Markdown")
    await cb.answer()

@router.message(TextEditStates.editing_photo)
async def save_new_photo(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    key = data.get("key")
    if not key:
        await state.clear()
        return
    if not message.photo:
        await message.answer("Нужно прислать именно фото.")
        return
    file_id = message.photo[-1].file_id
    await set_photo(key, file_id)
    tpl = await get_template(key)
    text = tpl["text"] or ""
    await state.set_state(TextEditStates.choosing)
    await message.answer(f"Картинка обновлена для `{key}`.", parse_mode="Markdown")
    await message.answer("Готово.", reply_markup=_edit_kb(key))

@router.callback_query(F.data.startswith("txt:clear_photo:"))
async def do_clear_photo(cb: types.CallbackQuery, state: FSMContext):
    key = cb.data.split(":", 2)[2]
    await clear_photo(key)
    tpl = await get_template(key)
    text = tpl["text"] or ""
    header = f"Шаблон: {key}\n\n"
    body = text if len(text) <= 3500 else text[:3500] + "\n…"
    footer = "\n\nКартинка: нет"
    await cb.message.edit_text(header + body + footer, reply_markup=_edit_kb(key))
    await cb.answer("Картинка убрана")
