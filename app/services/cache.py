import json
from app.db.redis import get_redis

JOBS_CACHE_KEY = "jobs:{keyword}:{location}"
CACHE_TTL = 21600  # 6 hours


async def get_cached_jobs(keyword: str, location: str) -> list | None:
    redis = get_redis()
    key = JOBS_CACHE_KEY.format(keyword=keyword, location=location)
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None


async def cache_jobs(keyword: str, location: str, jobs: list) -> None:
    redis = get_redis()
    key = JOBS_CACHE_KEY.format(keyword=keyword, location=location)
    await redis.setex(key, CACHE_TTL, json.dumps(jobs))


async def invalidate_jobs_cache(keyword: str, location: str) -> None:
    redis = get_redis()
    key = JOBS_CACHE_KEY.format(keyword=keyword, location=location)
    await redis.delete(key)
