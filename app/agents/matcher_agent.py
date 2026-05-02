import json
import math
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.db.mongo import settings
from app.models.profile import Profile
from app.models.job import Job, Match

SCORE_PROMPT = PromptTemplate(
    input_variables=["profile_summary", "job_description"],
    template="""Given this candidate profile and job description, return ONLY valid JSON with:
- score: integer 0-100 (how well the candidate matches the job)
- reasoning: one sentence explaining the score
- skill_gap: list of skills the job needs that the candidate lacks

Profile: {profile_summary}
Job: {job_description}

JSON:""",
)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0,
    )


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def rank_jobs_by_embedding(
    profile_embedding: list[float],
    job_embeddings: dict[str, list[float]],
) -> list[tuple[str, float]]:
    scored = [
        (job_id, _cosine_similarity(profile_embedding, emb))
        for job_id, emb in job_embeddings.items()
    ]
    return sorted(scored, key=lambda x: x[1], reverse=True)


async def score_match(profile: Profile, job: Job) -> tuple[int, str, list[str]]:
    llm = _get_llm()
    chain = SCORE_PROMPT | llm

    profile_summary = (
        f"Name: {profile.name}\n"
        f"Skills: {', '.join(profile.skills)}\n"
        f"Summary: {profile.summary}\n"
        f"Experience: {'; '.join(f'{e.title} at {e.company}' for e in profile.experience)}"
    )

    response = await chain.ainvoke({
        "profile_summary": profile_summary,
        "job_description": job.description[:2000],
    })

    try:
        cleaned = response.content.strip().strip("```").removeprefix("json").strip()
        data = json.loads(cleaned)
        return int(data.get("score", 50)), data.get("reasoning", ""), data.get("skill_gap", [])
    except Exception:
        return 50, "Could not parse score.", []


async def build_match(profile_id: str, profile: Profile, job: Job) -> Match:
    score, reasoning, gap = await score_match(profile, job)
    return Match(
        profile_id=profile_id,
        job_id=job.job_id,
        job_title=job.title,
        company=job.company,
        location=job.location,
        match_score=score,
        score_reasoning=reasoning,
        skill_gap=gap,
        job_description=job.description,
        apply_url=job.apply_url,
    )
