import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
INIT_DB_URL = "postgresql://postgres:postgres@db/postgres"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")