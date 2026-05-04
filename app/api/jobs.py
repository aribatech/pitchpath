import uuid
import asyncio
from fastapi import APIRouter, HTTPException, Query
from app.db.mongo import get_db
from app.models.profile import Profile
from app.models.job import Job
from app.services.job_scraper import fetch_jobs
from app.services.vector_store import (
    upsert_job_embedding,
    get_profile_embedding,
    get_job_embeddings_for_jobs,
)
from app.agents.matcher_agent import rank_jobs_by_embedding, build_match
from app.agents.gap_agent import analyze_gap

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/match/{profile_id}")
async def match_jobs(
    profile_id: str,
    keyword: str = Query(..., description="Job search keyword"),
    location: str = Query(..., description="Job location"),
    top_n: int = Query(10, ge=1, le=20),
):
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword is required.")
    if not location.strip():
        raise HTTPException(status_code=400, detail="Location is required.")

    db = get_db()
    profile_doc = await db.profiles.find_one({"_id": profile_id})
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile = Profile(**{k: v for k, v in profile_doc.items() if k != "_id"})

    raw_jobs = await fetch_jobs(keyword=keyword.strip(), location=location.strip())
    if not raw_jobs:
        raise HTTPException(status_code=404, detail=f"No jobs found for '{keyword}'. Try a different keyword.")

    jobs = [Job(**j) for j in raw_jobs if j.get("job_id")]

    await asyncio.gather(*[
        upsert_job_embedding(job.job_id, f"{job.title} {job.company} {job.description}")
        for job in jobs
    ])

    profile_embedding = await get_profile_embedding(profile_id)
    if profile_embedding and jobs:
        job_embeddings = await get_job_embeddings_for_jobs([j.job_id for j in jobs])
        ranked = rank_jobs_by_embedding(profile_embedding, job_embeddings)
        job_map = {j.job_id: j for j in jobs}
        top_jobs = [job_map[jid] for jid, _ in ranked[:top_n] if jid in job_map]
    else:
        top_jobs = jobs[:top_n]

    matches = await asyncio.gather(*[build_match(profile_id, profile, job) for job in top_jobs])
    matches = sorted(matches, key=lambda m: m.match_score, reverse=True)

    await db.matches.delete_many({"profile_id": profile_id})
    match_docs = []
    for m in matches:
        doc = m.model_dump()
        doc["_id"] = str(uuid.uuid4())
        match_docs.append(doc)

    if match_docs:
        await db.matches.insert_many(match_docs)

    return {
        "profile_id": profile_id,
        "keyword_used": keyword,
        "total": len(match_docs),
        "matches": [{"id": d["_id"], **{k: v for k, v in d.items() if k != "_id"}} for d in match_docs],
    }



@router.get("/{job_id}/gap/{profile_id}")
async def get_skill_gap(job_id: str, profile_id: str):
    db = get_db()
    profile_doc = await db.profiles.find_one({"_id": profile_id})
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found.")
    match_doc = await db.matches.find_one({"job_id": job_id, "profile_id": profile_id})
    if not match_doc:
        raise HTTPException(status_code=404, detail="Match not found. Run /jobs/match first.")

    profile = Profile(**{k: v for k, v in profile_doc.items() if k != "_id"})
    gap = await analyze_gap(profile, match_doc.get("job_description", ""))
    return {"profile_id": profile_id, "job_id": job_id, **gap}
