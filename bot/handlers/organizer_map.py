import os
import uuid

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.organizer_keyboards import organizer_menu
from keyboards.student_keyboards import main_menu
from utils.database import is_admin
from utils.map_db import create_map, list_maps, get_map, set_map_image, set_map_active, delete_map

router = Router()


class MapAdminStates(StatesGroup):
    waiting_title = State()
    waiting_photo = State()


async def ensure_admin(message: types.Message) -> bool:
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа.", reply_markup=main_menu())
        return False
    return True


async def ensure_admin_cb(call: types.CallbackQuery) -> bool:
    if not await is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return False
    return True


def _maps_kb(items):
    rows = [[InlineKeyboardButton(text="➕ Добавить", callback_data="mapadm:add")]]
    for m in items:
        status = "✅" if m["is_active"] else "🚫"
        rows.append([InlineKeyboardButton(text=f"{status} {m['id']}. {m['title']}", callback_data=f"mapadm:open:{m['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mapadm:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _map_actions_kb(map_id: int, is_active: bool):
    rows = [
        [InlineKeyboardButton(text="🖼 Открыть", callback_data=f"mapadm:show:{map_id}")],
        [InlineKeyboardButton(text=("🚫 Выключить" if is_active else "✅ Включить"), callback_data=f"mapadm:toggle:{map_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"mapadm:del:{map_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="mapadm:list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🗺 Редактирование карты")
async def map_admin_home(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    await state.clear()
    items = await list_maps(include_inactive=True)
    await message.answer("🗺 Карта: разделы", reply_markup=_maps_kb(items))


@router.callback_query(F.data == "mapadm:back")
async def mapadm_back(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return
    await state.clear()
    await call.message.answer("🛠 Панель организатора", reply_markup=organizer_menu())
    await call.answer()


@router.callback_query(F.data == "mapadm:list")
async def mapadm_list(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return
    await state.clear()
    items = await list_maps(include_inactive=True)
    await call.message.answer("🗺 Карта: разделы", reply_markup=_maps_kb(items))
    await call.answer()


@router.callback_query(F.data == "mapadm:add")
async def mapadm_add(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return
    await state.clear()
    await call.message.answer("Введите название карты (например: 1 ЭТАЖ):", reply_markup=organizer_menu())
    await state.set_state(MapAdminStates.waiting_title)
    await call.answer()


@router.message(MapAdminStates.waiting_title)
async def mapadm_title(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не должно быть пустым. Введите снова:")
        return
    map_id = await create_map(title=title)
    await state.update_data(map_id=map_id)
    await message.answer("Теперь отправьте фото карты (не файлом, а фото).")
    await state.set_state(MapAdminStates.waiting_photo)


@router.message(MapAdminStates.waiting_photo)
async def mapadm_photo(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        await state.clear()
        return
    if not message.photo:
        await message.answer("Пришлите фото (не документ).")
        return

    data = await state.get_data()
    map_id = int(data["map_id"])

    p = message.photo[-1]
    telegram_file_id = p.file_id
    telegram_file_unique_id = p.file_unique_id

    file = await message.bot.get_file(telegram_file_id)

    folder = f"media/maps/{map_id}"
    os.makedirs(folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.jpg"
    path = f"{folder}/{filename}"

    await message.bot.download_file(file.file_path, destination=path)
    stat = os.stat(path)

    await set_map_image(
        map_id=map_id,
        telegram_file_id=telegram_file_id,
        telegram_file_unique_id=telegram_file_unique_id,
        storage_path=path,
        mime="image/jpeg",
        size_bytes=stat.st_size,
        width=p.width,
        height=p.height,
    )

    await message.answer("✅ Карта добавлена.", reply_markup=organizer_menu())
    await state.clear()


@router.callback_query(F.data.startswith("mapadm:open:"))
async def mapadm_open(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin_cb(call):
        return
    await state.clear()
    map_id = int(call.data.split(":")[-1])
    m = await get_map(map_id)
    if not m:
        await call.message.answer("Не найдено.", reply_markup=organizer_menu())
        await call.answer()
        return
    await call.message.answer(
        f"Карта #{m['id']}\nНазвание: {m['title']}\nАктивна: {m['is_active']}",
        reply_markup=_map_actions_kb(m["id"], bool(m["is_active"])),
    )
    await call.answer()


@router.callback_query(F.data.startswith("mapadm:show:"))
async def mapadm_show(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return
    map_id = int(call.data.split(":")[-1])
    m = await get_map(map_id)
    if not m:
        await call.message.answer("Не найдено.", reply_markup=organizer_menu())
        await call.answer()
        return

    if m.get("telegram_file_id"):
        await call.message.answer_photo(
            photo=m["telegram_file_id"],
            caption=f"🗺 {m['title']}",
            reply_markup=_map_actions_kb(m["id"], bool(m["is_active"])),
        )
    else:
        await call.message.answer(
            f"🗺 {m['title']}\nФото ещё не загружено.",
            reply_markup=_map_actions_kb(m["id"], bool(m["is_active"])),
        )
    await call.answer()


@router.callback_query(F.data.startswith("mapadm:toggle:"))
async def mapadm_toggle(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return
    map_id = int(call.data.split(":")[-1])
    m = await get_map(map_id)
    if not m:
        await call.message.answer("Не найдено.", reply_markup=organizer_menu())
        await call.answer()
        return
    new_state = not bool(m["is_active"])
    await set_map_active(map_id, new_state)
    await call.message.answer("✅ Обновлено.", reply_markup=organizer_menu())
    await call.answer()


@router.callback_query(F.data.startswith("mapadm:del:"))
async def mapadm_del(call: types.CallbackQuery):
    if not await ensure_admin_cb(call):
        return
    map_id = int(call.data.split(":")[-1])
    await delete_map(map_id)
    await call.message.answer("🗑 Удалено.", reply_markup=organizer_menu())
    await call.answer()
