import asyncio
import json
from pathlib import Path
from aiogram import types

from texts.default_texts import DEFAULT_TEXTS

_STORE_PATH = Path(__file__).resolve().parent / "store.json"
_LOCK = asyncio.Lock()

def _ensure_store_exists():
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

async def _read_store():
    _ensure_store_exists()
    async with _LOCK:
        raw = _STORE_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)

async def _write_store(data):
    async with _LOCK:
        _STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

async def list_templates():
    store = await _read_store()
    keys = sorted(set(DEFAULT_TEXTS.keys()) | set(store.keys()))
    out = []
    for k in keys:
        v = store.get(k, {})
        text = v.get("text")
        photo = v.get("photo")
        out.append(
            {
                "key": k,
                "text": text if isinstance(text, str) and text else DEFAULT_TEXTS.get(k, ""),
                "photo": photo if isinstance(photo, str) and photo else None,
            }
        )
    return out

async def get_template(key: str):
    store = await _read_store()
    v = store.get(key, {})
    text = v.get("text")
    photo = v.get("photo")
    return {
        "key": key,
        "text": text if isinstance(text, str) and text else DEFAULT_TEXTS.get(key, ""),
        "photo": photo if isinstance(photo, str) and photo else None,
    }

async def set_text(key: str, text: str):
    store = await _read_store()
    v = store.get(key, {})
    v["text"] = text
    store[key] = v
    await _write_store(store)

async def set_photo(key: str, file_id: str):
    store = await _read_store()
    v = store.get(key, {})
    v["photo"] = file_id
    store[key] = v
    await _write_store(store)

async def clear_photo(key: str):
    store = await _read_store()
    v = store.get(key, {})
    v["photo"] = None
    store[key] = v
    await _write_store(store)

def render(text: str, **kwargs):
    try:
        return text.format(**kwargs)
    except Exception:
        return text

async def send_template(bot, message: types.Message, key: str, reply_markup=None, parse_mode=None, disable_web_page_preview=None, **kwargs):
    tpl = await get_template(key)
    text = render(tpl["text"] or "", **kwargs)

    if tpl.get("photo"):
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=tpl["photo"],
            caption=text if text else None,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return

    await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )