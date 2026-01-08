from typing import Optional, List, Dict, Any

from utils.database import get_db


async def create_map(title: str) -> int:
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO maps(title) VALUES($1) RETURNING id",
            title,
        )
        return int(row["id"])


async def set_map_image(
    map_id: int,
    telegram_file_id: str,
    telegram_file_unique_id: str,
    storage_path: str,
    mime: str,
    size_bytes: int,
    width: int,
    height: int,
) -> None:
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE maps
            SET telegram_file_id=$2,
                telegram_file_unique_id=$3,
                storage_path=$4,
                mime=$5,
                size_bytes=$6,
                width=$7,
                height=$8
            WHERE id=$1
            """,
            map_id,
            telegram_file_id,
            telegram_file_unique_id,
            storage_path,
            mime,
            size_bytes,
            width,
            height,
        )


async def list_maps(include_inactive: bool = False) -> List[Dict[str, Any]]:
    pool = await get_db()
    async with pool.acquire() as conn:
        if include_inactive:
            rows = await conn.fetch(
                "SELECT * FROM maps ORDER BY id DESC"
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM maps WHERE is_active=TRUE ORDER BY id DESC"
            )
        return [dict(r) for r in rows]


async def get_map(map_id: int) -> Optional[Dict[str, Any]]:
    pool = await get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM maps WHERE id=$1",
            map_id,
        )
        return dict(row) if row else None


async def set_map_active(map_id: int, is_active: bool) -> None:
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE maps SET is_active=$2 WHERE id=$1",
            map_id,
            is_active,
        )


async def delete_map(map_id: int) -> None:
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM maps WHERE id=$1", map_id)
