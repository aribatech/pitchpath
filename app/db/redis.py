from upstash_redis.asyncio import Redis
from app.db.mongo import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)
    return _redis
