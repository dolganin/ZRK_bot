import json
from typing import Optional
from redis.asyncio import Redis
from redis.asyncio.client import Redis as RedisClient


class CodesCache:
    def __init__(self, redis: RedisClient):
        self.redis = redis

    @staticmethod
    def _key(code: str) -> str:
        return f"code:status:{code.upper()}"

    async def get_status(self, code: str) -> Optional[str]:
        v = await self.redis.get(self._key(code))
        if not v:
            return None
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8", errors="ignore")
        return str(v)

    async def set_status(self, code: str, status: str, ttl_seconds: int) -> None:
        ttl = max(1, int(ttl_seconds))
        await self.redis.set(self._key(code), status, ex=ttl)


def ttl_until(ts_now, ts_target) -> int:
    if ts_target is None:
        return 60
    delta = (ts_target - ts_now).total_seconds()
    return max(1, int(delta))


def compute_status(now, starts_at, expires_at) -> str:
    if starts_at is not None and now < starts_at:
        return "pending"
    if expires_at is not None and now >= expires_at:
        return "expired"
    return "active"