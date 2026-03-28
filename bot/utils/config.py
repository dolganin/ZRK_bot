import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_redis_url(value: str | None) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return "redis://localhost:6379/0"
    if "://" in raw_value:
        return raw_value
    if raw_value.startswith("/"):
        return f"unix://{raw_value}"
    return f"redis://{raw_value}"


TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = _normalize_redis_url(os.getenv("REDIS_URL"))
TELEGRAM_PROXY_URL = os.getenv("TELEGRAM_PROXY_URL")
