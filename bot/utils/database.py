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

async def register_student(user_id: int, name: str, telegram_username: str = None, course: str = None, faculty: str = None) -> bool:
    """Регистрация нового студента с учетом никнейма, курса и факультета"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Проверяем, существует ли уже студент с таким ID
            existing = await conn.fetchval(
                "SELECT id FROM students WHERE id = $1", 
                user_id
            )
            if existing:
                return False  # Студент с таким ID уже зарегистрирован

            # Вставляем данные о студенте в таблицу
            await conn.execute(
                """
                INSERT INTO students (id, name, telegram_username, balance, course, faculty)
                VALUES ($1, $2, $3, 0, $4, $5)
                """,
                user_id, name, telegram_username, course, faculty
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
    """Начисление баллов по коду (если код ещё не использован этим пользователем).
       Если для пары (user_id, code_id) отсутствует запись в user_codes,
       производится начисление баллов и создаётся запись о использовании.
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Ищем код в таблице codes
            code_data = await conn.fetchrow(
                "SELECT id, points, is_income FROM codes WHERE code = $1",
                code.upper()
            )

            # Если код не найден или предназначен не для начисления баллов
            if not code_data or not code_data["is_income"]:
                return None

            # Проверяем, использовал ли пользователь этот код ранее
            is_used = await conn.fetchrow(
                "SELECT 1 FROM user_codes WHERE user_id = $1 AND code_id = $2",
                user_id, code_data["id"]
            )
            if is_used:
                return None  # Код уже был использован этим пользователем

            # Начисляем баллы студенту
            await conn.execute(
                "UPDATE students SET balance = balance + $1 WHERE id = $2",
                code_data["points"], user_id
            )

            # Фиксируем факт использования кода пользователем
            await conn.execute(
                "INSERT INTO user_codes (user_id, code_id) VALUES ($1, $2)",
                user_id, code_data["id"]
            )

            return code_data["points"]





async def spend_points(user_id: int, code: str) -> bool:
    """Списание баллов по коду (если код ещё не использовался этим пользователем).
       Если код существует, предназначен для списания (is_income = FALSE) и у пользователя достаточно баллов,
       то баллы списываются, и в таблицу user_codes добавляется запись, фиксирующая использование кода.
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Получаем данные кода из таблицы codes
            code_data = await conn.fetchrow(
                "SELECT id, points, is_income FROM codes WHERE code = $1",
                code.upper()
            )
            # Если код не найден или предназначен для пополнения, выходим
            if not code_data or code_data["is_income"]:
                return False

            # Проверяем, использовал ли пользователь этот код ранее (запись в user_codes отсутствует)
            is_used = await conn.fetchrow(
                "SELECT 1 FROM user_codes WHERE user_id = $1 AND code_id = $2",
                user_id, code_data["id"]
            )
            if is_used:
                return False  # Код уже был использован этим пользователем

            # Проверяем, достаточно ли баллов у пользователя для списания
            balance = await get_balance(user_id)
            if balance < code_data["points"]:
                return False

            # Списываем баллы: обновляем баланс студента
            await conn.execute(
                "UPDATE students SET balance = balance - $1 WHERE id = $2",
                code_data["points"], user_id
            )

            # Фиксируем использование кода: создаём запись в user_codes
            await conn.execute(
                "INSERT INTO user_codes (user_id, code_id) VALUES ($1, $2)",
                user_id, code_data["id"]
            )

            return True



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

async def get_all_students_rating(user_id: int, limit: int = 10) -> List[Dict]:
    """Полный рейтинг студентов с возможностью указать количество первых мест"""
    pool = await get_db()
    async with pool.acquire() as conn:
        if await is_admin(user_id):
            # If the user is an admin, return all students
            records = await conn.fetch(
                """SELECT name, balance
                FROM students
                ORDER BY balance DESC"""
            )
        else:
            # If the user is not an admin, return the top 10 students
            records = await conn.fetch(
                """SELECT name, balance
                FROM students
                ORDER BY balance DESC
                LIMIT $1""",
                limit
            )
        return [dict(r) for r in records]



async def get_codes_usage(event_id: int = None):
    """Получение кодов с количеством их использований, с возможностью фильтрации по мероприятию"""
    pool = await get_db()
    async with pool.acquire() as conn:
        if event_id is not None:
            query = """
                SELECT c.code, e.name AS event_name, c.points, c.is_income, 
                       COUNT(uc.code_id) AS usage_count
                FROM codes c
                JOIN events e ON c.event_id = e.id
                LEFT JOIN user_codes uc ON c.id = uc.code_id
                WHERE c.event_id = $1
                GROUP BY c.id, e.name
            """
            rows = await conn.fetch(query, event_id)
        else:
            query = """
                SELECT c.code, e.name AS event_name, c.points, c.is_income, 
                       COUNT(uc.code_id) AS usage_count
                FROM codes c
                JOIN events e ON c.event_id = e.id
                LEFT JOIN user_codes uc ON c.id = uc.code_id
                GROUP BY c.id, e.name
            """
            rows = await conn.fetch(query)

        return [
            {
                "code": row["code"],
                "event_name": row["event_name"],
                "points": row["points"],
                "is_income": row["is_income"],
                "usage_count": row["usage_count"]
            }
            for row in rows
        ]





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
    """Добавление кода к мероприятию.
       Код сохраняется в таблице codes и не считается использованным до момента применения.
    """
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO codes (event_id, code, points, is_income)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (code) DO NOTHING
                """,
                event_id, code.upper(), points, is_income
            )
            return {"status": "success", "message": "Код успешно добавлен."}



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

async def delete_code(code: str):
    """Удаление кода из базы данных"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """DELETE FROM codes
                   WHERE code = $1""",
                code.upper()
            )

async def delete_event(event_id: int):
    """Удаление мероприятия и всех связанных с ним кодов из базы данных"""
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Удаление всех кодов, связанных с мероприятием
            await conn.execute(
                """DELETE FROM codes WHERE event_id = $1""",
                event_id
            )
            # Удаление самого мероприятия
            await conn.execute(
                """DELETE FROM events WHERE id = $1""",
                event_id
            )

