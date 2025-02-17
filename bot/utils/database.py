import asyncpg
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.config import DATABASE_URL, INIT_DB_URL
from database.models import Base

async def setup_database():
    """Создает пользователя и базу данных, если их нет"""
    try:
        conn = await asyncpg.connect(INIT_DB_URL)

        # Создаем пользователя, если его нет
        await conn.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'career_admin') THEN CREATE ROLE career_admin WITH LOGIN PASSWORD 'securepassword' SUPERUSER; END IF; END $$;")

        # Проверяем, существует ли база
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='career_quest_db'")
        if not db_exists:
            await conn.execute("CREATE DATABASE career_quest_db OWNER career_admin;")

        await conn.close()
        print("✅ База данных и пользователь успешно созданы!")

    except Exception as e:
        print(f"⚠ Ошибка при настройке базы данных: {e}")

async def init_db():
    """Создает таблицы в базе данных, если их нет"""
    await setup_database()
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    print("✅ Таблицы успешно созданы!")

async def get_db():
    """Создает пул соединений с базой данных"""
    return await asyncpg.create_pool(DATABASE_URL)

async def register_student(user_id):
    """Регистрирует студента, если он еще не зарегистрирован"""
    db = await get_db()
    async with db.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM students WHERE id=$1", user_id)
        if existing:
            return False
        await conn.execute("INSERT INTO students (id, balance) VALUES ($1, 0)", user_id)
        return True

async def get_balance(user_id):
    """Возвращает баланс студента"""
    db = await get_db()
    return await db.fetchval("SELECT balance FROM students WHERE id=$1", user_id)

async def add_points(user_id, code):
    """Начисляет баллы по уникальному коду"""
    db = await get_db()
    async with db.acquire() as conn:
        points = await conn.fetchval("SELECT points FROM codes WHERE code=$1 AND used=false", code)
        if points:
            await conn.execute("UPDATE students SET balance = balance + $1 WHERE id=$2", points, user_id)
            await conn.execute("UPDATE codes SET used=true WHERE code=$1", code)
            return points
    return None

async def spend_points(user_id, code):
    """Списывает баллы за мерч"""
    db = await get_db()
    async with db.acquire() as conn:
        price = await conn.fetchval("SELECT cost FROM merch WHERE code=$1 AND used=false", code)
        balance = await get_balance(user_id)
        if price and balance >= price:
            await conn.execute("UPDATE students SET balance = balance - $1 WHERE id=$2", price, user_id)
            await conn.execute("UPDATE merch SET used=true WHERE code=$1", code)
            return True
    return False

async def get_top_students():
    """Возвращает топ студентов"""
    db = await get_db()
    return await db.fetch("SELECT name, balance FROM students ORDER BY balance DESC LIMIT 10")