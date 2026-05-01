import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.db.mongo import settings
from app.models.profile import Profile

GAP_PROMPT = PromptTemplate(
    input_variables=["skills", "job_description"],
    template="""Analyze the skill gap between this candidate and the job.

Candidate skills: {skills}
Job description: {job_description}

Return ONLY valid JSON with:
- missing_skills: list of skills required by the job that the candidate lacks
- matching_skills: list of skills the candidate has that match the job
- recommendation: one sentence of advice for the candidate

JSON:""",
)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0,
    )


async def analyze_gap(profile: Profile, job_description: str) -> dict:
    llm = _get_llm()
    chain = GAP_PROMPT | llm

    response = await chain.ainvoke({
        "skills": ", ".join(profile.skills),
        "job_description": job_description[:2000],
    })
    result = response.content

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except Exception:
        return {"missing_skills": [], "matching_skills": profile.skills, "recommendation": ""}
