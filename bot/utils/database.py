import asyncpg
from asyncpg.pool import Pool
from sqlalchemy.ext.asyncio import create_async_engine
from typing import Optional, List, Dict, Union
from utils.config import DATABASE_URL, INIT_DB_URL
from database.models import Base
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

# Глобальный пул подключений
_pool: Optional[Pool] = None

async def setup_database():
    """Инициализация базы данных и пользователя"""
    try:
        # Временное подключение для настройки БД через INIT_DB_URL
        temp_conn = await asyncpg.connect(INIT_DB_URL)
        
        # Создание пользователя career_admin, если его нет
        await temp_conn.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'career_admin') THEN
                    CREATE ROLE career_admin WITH LOGIN PASSWORD 'securepassword' SUPERUSER;
                END IF;
            END $$;
        """)
        
        # Создание базы данных career_quest_db, если её нет
        await temp_conn.execute("""
            SELECT 'CREATE DATABASE career_quest_db OWNER career_admin'
            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'career_quest_db')
        """)
        
        await temp_conn.close()
        logger.info("Database and user setup completed successfully")
    except Exception as e:
        logger.error(f"Database setup error: {e}")
        raise

async def init_db():
    """Инициализация пула подключений и создание таблиц"""
    global _pool
    
    try:
        # Настройка основной БД
        await setup_database()
        
        # Для создания пула нужно использовать DSN с корректной схемой:
        dsn_for_pool = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        # Инициализация пула подключений
        _pool = await asyncpg.create_pool(
            dsn_for_pool,
            min_size=2,
            max_size=20,
            timeout=30,
            command_timeout=60
        )
        logger.info("Connection pool initialized")
        
        # Создание таблиц через SQLAlchemy (используем оригинальный DATABASE_URL)
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def get_db() -> Pool:
    """Получение глобального пула подключений"""
    if _pool is None:
        raise RuntimeError("Database connection pool is not initialized")
    return _pool

async def close_db():
    """Корректное закрытие пула подключений"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed")

async def register_student(user_id: int, name: str) -> bool:
    """Регистрация нового студента"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchval(
                "SELECT id FROM students WHERE id = $1", 
                user_id
            )
            if existing:
                return False
            
            await conn.execute(
                "INSERT INTO students (id, name, balance) VALUES ($1, $2, 0)",
                user_id, name
            )
            return True

async def get_balance(user_id: int) -> int:
    """Получение баланса студента"""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT balance FROM students WHERE id = $1",
            user_id
        )

async def add_points(user_id: int, code: str) -> Optional[int]:
    """Начисление баллов по коду"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            code_data = await conn.fetchrow(
                """SELECT points FROM codes 
                WHERE code = $1 AND is_active = TRUE""",
                code.upper()
            )
            
            if not code_data:
                return None
            
            points = code_data['points']
            await conn.execute(
                """UPDATE students 
                SET balance = balance + $1 
                WHERE id = $2""",
                points, user_id
            )
            
            await conn.execute(
                """UPDATE codes 
                SET is_active = FALSE 
                WHERE code = $1""",
                code.upper()
            )
            
            return points

async def spend_points(user_id: int, code: str) -> bool:
    """Списание баллов за мерч"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            merch_data = await conn.fetchrow(
                """SELECT cost FROM merch 
                WHERE code = $1 AND used = FALSE""",
                code.upper()
            )
            
            if not merch_data:
                return False
            
            cost = merch_data['cost']
            balance = await get_balance(user_id)
            
            if balance < cost:
                return False
            
            await conn.execute(
                """UPDATE students 
                SET balance = balance - $1 
                WHERE id = $2""",
                cost, user_id
            )
            
            await conn.execute(
                """UPDATE merch 
                SET used = TRUE 
                WHERE code = $1""",
                code.upper()
            )
            
            return True

async def get_top_students(limit: int = 10) -> List[Dict]:
    """Получение топа студентов"""
    pool = await get_db()
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """SELECT name, balance 
            FROM students 
            ORDER BY balance DESC 
            LIMIT $1""",
            limit
        )
        return [dict(r) for r in records]

async def add_admin(user_id: int):
    """Добавление администратора"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO admins (user_id) 
                VALUES ($1) 
                ON CONFLICT (user_id) DO NOTHING""",
                user_id
            )

async def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT 1 FROM admins WHERE user_id = $1",
            user_id
        ) is not None

async def send_notification(text: str):
    """Отправка уведомлений всем студентам"""
    from core.bot import bot
    pool = await get_db()
    async with pool.acquire() as conn:
        students = await conn.fetch("SELECT id FROM students")
        for student in students:
            try:
                await bot.send_message(student['id'], text)
            except Exception as e:
                logger.error(f"Failed to send message to {student['id']}: {e}")

async def get_all_students_rating() -> List[Dict]:
    """Полный рейтинг студентов"""
    pool = await get_db()
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """SELECT name, balance 
            FROM students 
            ORDER BY balance DESC"""
        )
        return [dict(r) for r in records]

async def get_active_codes() -> List[Dict]:
    """Получение активных кодов"""
    pool = await get_db()
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """SELECT c.code, c.points, c.is_income, e.name as event_name 
            FROM codes c
            JOIN events e ON c.event_id = e.id
            WHERE c.is_active = TRUE"""
        )
        return [dict(r) for r in records]

async def add_event(name: str):
    """Добавление мероприятия"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO events (name) VALUES ($1)",
                name
            )

async def get_events(event_id: Optional[int] = None) -> Union[Dict, List[Dict]]:
    """Получение мероприятий"""
    pool = await get_db()
    async with pool.acquire() as conn:
        if event_id:
            record = await conn.fetchrow(
                "SELECT * FROM events WHERE id = $1",
                event_id
            )
            return dict(record) if record else None
        
        records = await conn.fetch(
            "SELECT * FROM events ORDER BY id DESC"
        )
        return [dict(r) for r in records]

async def add_code_to_event(event_id: int, code: str, points: int, is_income: bool):
    """Добавление кода к мероприятию"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO codes 
                (event_id, code, points, is_income, is_active)
                VALUES ($1, $2, $3, $4, TRUE)
                ON CONFLICT (code) DO NOTHING""",
                event_id, code.upper(), points, is_income
            )

async def check_code_exists(code: str) -> bool:
    """Проверка существования кода"""
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT 1 FROM codes WHERE code = $1",
            code.upper()
        ) is not None

async def send_message(user_id: int, text: str):
    """Отправка сообщения пользователю"""
    from core.bot import bot
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        logger.error(f"Failed to send message to {user_id}: {e}")
