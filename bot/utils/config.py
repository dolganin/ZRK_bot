import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
# Для SQLAlchemy используем asyncpg, поэтому схема "postgresql+asyncpg://"
DATABASE_URL = os.getenv("DATABASE_URL")
# Для инициализации (подключение через asyncpg напрямую) используем схему "postgresql://"
INIT_DB_URL = "postgresql://postgres:postgres@db/postgres"
