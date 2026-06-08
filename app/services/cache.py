import json
from app.db.redis import get_redis

JOBS_CACHE_KEY = "jobs:{keyword}:{location}"
CACHE_TTL = 21600


async def get_cached_jobs(keyword: str, location: str) -> list | None:
    key = JOBS_CACHE_KEY.format(keyword=keyword, location=location)
    cached = await get_redis().get(key)
    if cached:
        return json.loads(cached)
    return None


async def cache_jobs(keyword: str, location: str, jobs: list) -> None:
    key = JOBS_CACHE_KEY.format(keyword=keyword, location=location)
    await get_redis().set(key, json.dumps(jobs), ex=CACHE_TTL)
