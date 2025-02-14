import asyncpg
from bot.utils.config import DATABASE_URL

async def get_db():
    return await asyncpg.create_pool(DATABASE_URL)

async def register_student(user_id):
    db = await get_db()
    async with db.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM students WHERE id=$1", user_id)
        if existing:
            return False
        await conn.execute("INSERT INTO students (id, balance) VALUES ($1, 0)", user_id)
        return True

async def get_balance(user_id):
    db = await get_db()
    return await db.fetchval("SELECT balance FROM students WHERE id=$1", user_id)

async def add_points(user_id, code):
    db = await get_db()
    async with db.acquire() as conn:
        points = await conn.fetchval("SELECT points FROM codes WHERE code=$1 AND used=false", code)
        if points:
            await conn.execute("UPDATE students SET balance = balance + $1 WHERE id=$2", points, user_id)
            await conn.execute("UPDATE codes SET used=true WHERE code=$1", code)
            return points
    return None

async def spend_points(user_id, code):
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
    db = await get_db()
    return await db.fetch("SELECT name, balance FROM students ORDER BY balance DESC LIMIT 10")

async def send_notification(text):
    db = await get_db()
    users = await db.fetch("SELECT id FROM students")
    for user in users:
        await bot.send_message(user['id'], text)
