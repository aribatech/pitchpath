import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.db.mongo import settings
from app.models.profile import Profile, Experience, Education

KEYWORD_PROMPT = PromptTemplate(
    input_variables=["skills", "experience", "summary"],
    template="""Based on this student's resume, suggest 4 internship search keywords for job boards.

Summary: {summary}
Skills: {skills}
Experience: {experience}

Rules:
- Each keyword must match their actual domain (ML -> "machine learning intern", design -> "UI UX intern", mobile -> "flutter intern")
- Format: "[domain] intern" or "[domain] developer intern"
- 2-4 words max, broad enough to return real listings
- Do NOT default to "software engineer" unless truly generic

Return ONLY a JSON array of 4 strings.
JSON:""",
)

CHECK_PROMPT = PromptTemplate(
    input_variables=["text"],
    template="""Is the following document a person's resume or CV?
Answer with a single JSON object: {{"is_resume": true}} or {{"is_resume": false}}
A resume must have at least some of: person's name, contact info, skills, work experience, or education.
Invoices, books, articles, manuals, reports are NOT resumes.

Document (first 1500 chars):
{text}

JSON:""",
)

PARSE_PROMPT = PromptTemplate(
    input_variables=["resume_text"],
    template="""Extract structured information from this resume.
Return ONLY valid JSON with exactly these keys:
- name (string)
- email (string)
- phone (string)
- skills (array of strings)
- experience (array of objects with: title, company, duration, description)
- education (object with: degree, institution, years)
- summary (string, 2-3 sentences about the candidate)

Resume:
{resume_text}

JSON:""",
)


async def suggest_keywords(profile: Profile) -> list[str]:
    llm = ChatOpenAI(openai_api_key=settings.openai_api_key, model="gpt-4o-mini", temperature=0.3)
    chain = KEYWORD_PROMPT | llm
    response = await chain.ainvoke({
        "skills": ", ".join(profile.skills[:15]),
        "experience": ", ".join(f"{e.title} at {e.company}" for e in profile.experience[:3]),
        "summary": profile.summary or "",
    })
    try:
        cleaned = response.content.strip().strip("```").removeprefix("json").strip()
        keywords = json.loads(cleaned)
        return [k for k in keywords if isinstance(k, str)][:4]
    except Exception:
        return ["software engineer intern", "backend intern", "developer intern", "tech intern"]


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0,
    )


async def is_resume(raw_text: str) -> bool:
    llm = _get_llm()
    chain = CHECK_PROMPT | llm
    response = await chain.ainvoke({"text": raw_text[:1500]})
    try:
        cleaned = response.content.strip().strip("```").removeprefix("json").strip()
        data = json.loads(cleaned)
        return bool(data.get("is_resume", False))
    except Exception:
        return False


async def parse_resume(raw_text: str) -> Profile:
    llm = _get_llm()
    chain = PARSE_PROMPT | llm
    response = await chain.ainvoke({"resume_text": raw_text})
    result = response.content

    try:
        cleaned = result.strip().strip("```").removeprefix("json").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    experiences = [
        Experience(**exp) if isinstance(exp, dict) else Experience(
            title=str(exp), company="", duration="", description=""
        )
        for exp in data.get("experience", [])
    ]

    education = None
    if edu := data.get("education"):
        try:
            education = Education(**edu) if isinstance(edu, dict) else None
        except Exception:
            education = None

    return Profile(
        name=data.get("name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        skills=data.get("skills", []),
        experience=experiences,
        education=education,
        summary=data.get("summary", ""),
        raw_text=raw_text,
    )
