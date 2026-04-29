import httpx
from app.db.mongo import settings
from app.services.cache import get_cached_jobs, cache_jobs

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


async def fetch_jobs(keyword: str = "internship", location: str = "Pakistan") -> list[dict]:
    cached = await get_cached_jobs(keyword, location)
    if cached:
        return cached

    headers = {
        "X-RapidAPI-Key":  settings.rapidapi_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            JSEARCH_URL,
            headers=headers,
            params={
                "query":            f"{keyword} {location}",
                "num_pages":        "1",
                "page":             "1",
                "employment_types": "INTERN",
            },
        )
        resp.raise_for_status()

    raw = resp.json().get("data", [])
    jobs = [
        {
            "job_id":      j.get("job_id", ""),
            "title":       j.get("job_title", ""),
            "company":     j.get("employer_name", ""),
            "location":    f"{j.get('job_city', '')} {j.get('job_country', '')}".strip(),
            "description": (j.get("job_description") or "")[:3000],
            "apply_url":   j.get("job_apply_link", ""),
        }
        for j in raw
    ]

    await cache_jobs(keyword, location, jobs)
    return jobs
