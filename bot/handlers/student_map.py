from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.student_keyboards import main_menu
from utils.map_db import list_maps, get_map

router = Router()


def _student_maps_kb(items):
    rows = []
    for m in items:
        rows.append([InlineKeyboardButton(text=m["title"], callback_data=f"map:open:{m['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ На главную", callback_data="map:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🗺 Карта")
async def student_map(message: types.Message):
    items = await list_maps(include_inactive=False)
    if not items:
        await message.answer("🗺 Карта пока не добавлена.", reply_markup=main_menu())
        return
    await message.answer("🗺 Выберите раздел карты:", reply_markup=_student_maps_kb(items))


@router.callback_query(F.data == "map:home")
async def map_home(call: types.CallbackQuery):
    await call.message.answer("Главное меню:", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data.startswith("map:open:"))
async def map_open(call: types.CallbackQuery):
    map_id = int(call.data.split(":")[-1])
    m = await get_map(map_id)
    if not m or not m.get("is_active"):
        await call.answer("Недоступно", show_alert=True)
        return

    if m.get("telegram_file_id"):
        await call.message.answer_photo(
            photo=m["telegram_file_id"],
            caption=f"🗺 {m['title']}",
            reply_markup=_student_maps_kb(await list_maps(include_inactive=False)),
        )
    else:
        await call.message.answer(
            f"🗺 {m['title']}\nФото ещё не загружено.",
            reply_markup=_student_maps_kb(await list_maps(include_inactive=False)),
        )
    await call.answer()
