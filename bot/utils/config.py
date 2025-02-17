import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# URL для инициализации (используем root-пользователя `postgres` с паролем)
INIT_DB_URL = "postgresql://postgres:postgres@db/postgres"
