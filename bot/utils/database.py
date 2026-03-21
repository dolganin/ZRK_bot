import asyncpg
from asyncpg.pool import Pool
from typing import Optional, List, Dict, Union
from utils.config import DATABASE_URL
import logging


from datetime import datetime, timezone
from utils.config import REDIS_URL
from redis.asyncio import Redis
from utils.codes_cache import CodesCache, compute_status, ttl_until


# Настройка логгера
logger = logging.getLogger(__name__)

# Глобальный пул подключений
_pool: Optional[Pool] = None
_redis: Optional[Redis] = None
_codes_cache: Optional[CodesCache] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def redeem_code(user_id: int, code: str) -> Optional[int]:
    pool = await get_db()
    code_u = code.upper()
    now = _utcnow()

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id, points, is_income, starts_at, expires_at, max_uses
                FROM codes
                WHERE code = $1
                FOR UPDATE
                """,
                code_u
            )
            if not row:
                return None
            
            if not row["is_income"]:
                return None

            starts_at = row["starts_at"]
            expires_at = row["expires_at"]
            max_uses = row["max_uses"]

            if starts_at is not None and now < starts_at:
                return None
            if expires_at is not None and now >= expires_at:
                return None

            used = await conn.fetchval(
                "SELECT 1 FROM user_codes WHERE user_id = $1 AND code_id = $2",
                user_id, row["id"]
            )
            if used:
                return None

            if max_uses is not None:
                used_total = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_codes WHERE code_id = $1",
                    row["id"]
                )
                if int(used_total) >= int(max_uses):
                    return None

            delta = int(row["points"])
            await conn.execute(
                "UPDATE students SET balance = balance + $1 WHERE id = $2",
                delta, user_id
            )
            await conn.execute(
                "INSERT INTO user_codes (user_id, code_id) VALUES ($1, $2)",
                user_id, row["id"]
            )

    if _codes_cache is not None:
        try:
            status = compute_status(now, starts_at, expires_at)
            if status == "pending":
                ttl = ttl_until(now, starts_at)
            elif status == "expired":
                ttl = 3600
            else:
                ttl = ttl_until(now, expires_at) if expires_at is not None else 60
            await _codes_cache.set_status(code_u, status, ttl)
        except Exception:
            pass

    return delta


async def init_db():
    """Инициализация пула подключений без изменения существующей БД."""
    global _pool
    
    try:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")

        dsn_for_pool = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

        _pool = await asyncpg.create_pool(
            dsn_for_pool,
            min_size=2,
            max_size=20,
            timeout=30,
            command_timeout=60
        )
        logger.info("Connection pool initialized")

        global _redis, _codes_cache
        _redis = Redis.from_url(REDIS_URL, decode_responses=False)
        _codes_cache = CodesCache(_redis)
        logger.info("Database startup checks completed without schema changes")
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
    global _redis, _codes_cache
    if _redis:
        await _redis.close()
        _redis = None
        _codes_cache = None


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

            # Исправленный запрос с явным указанием столбцов
            await conn.execute(
                """
                INSERT INTO students 
                    (id, name, telegram_username, course, faculty)
                VALUES 
                    ($1, $2, $3, $4, $5)
                """,
                user_id, 
                name, 
                telegram_username, 
                course, 
                faculty  # Теперь параметры совпадают с порядком в запросе
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
    delta = await redeem_code(user_id, code)
    if delta is None:
        return None
    return delta if delta > 0 else None




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
    pool = await get_db()
    now = _utcnow()

    async with pool.acquire() as conn:
        if event_id is not None:
            query = """
                SELECT c.code, e.name AS event_name, c.points, c.is_income,
                       c.starts_at, c.expires_at, c.max_uses,
                       COUNT(uc.code_id) AS usage_count
                FROM codes c
                JOIN events e ON c.event_id = e.id
                LEFT JOIN user_codes uc ON c.id = uc.code_id
                WHERE c.event_id = $1
                GROUP BY c.id, e.name
                ORDER BY c.id DESC
            """
            rows = await conn.fetch(query, event_id)
        else:
            query = """
                SELECT c.code, e.name AS event_name, c.points, c.is_income,
                       c.starts_at, c.expires_at, c.max_uses,
                       COUNT(uc.code_id) AS usage_count
                FROM codes c
                JOIN events e ON c.event_id = e.id
                LEFT JOIN user_codes uc ON c.id = uc.code_id
                GROUP BY c.id, e.name
                ORDER BY c.id DESC
            """
            rows = await conn.fetch(query)

    out = []
    for row in rows:
        status = compute_status(now, row["starts_at"], row["expires_at"])
        out.append(
            {
                "code": row["code"],
                "event_name": row["event_name"],
                "points": row["points"],
                "is_income": row["is_income"],
                "usage_count": row["usage_count"],
                "starts_at": row["starts_at"],
                "expires_at": row["expires_at"],
                "max_uses": row["max_uses"],
                "status": status,
            }
        )
    return out



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



async def add_code_to_event(
    event_id: int,
    code: str,
    points: int,
    is_income: bool,
    starts_at: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    max_uses: Optional[int] = None,
):
    pool = await get_db()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO codes (event_id, code, points, is_income, starts_at, expires_at, max_uses)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (code) DO NOTHING
                """,
                event_id,
                code.upper(),
                points,
                is_income,
                starts_at,
                expires_at,
                max_uses
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

async def is_user_registered(user_id: int) -> bool:
    """Проверка, зарегистрирован ли пользователь по его ID"""
    pool = await get_db()
    async with pool.acquire() as conn:
        # Выполняем запрос для проверки существования пользователя по ID
        result = await conn.fetchval(
            "SELECT 1 FROM students WHERE id = $1",
            user_id
        )
        # Если результат есть, значит пользователь зарегистрирован
        return result is not None
