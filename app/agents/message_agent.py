import asyncio
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.db.mongo import settings

MESSAGE_PROMPT = PromptTemplate(
    input_variables=["name", "role", "company", "top_skills", "platform"],
    template="""Write a short {platform} outreach message for a job application.
- Keep it under 60 words
- Sound human, not templated
- Mention the role and one specific skill
- End with a clear ask (call, reply, forward resume)

Candidate name: {name}
Applying for: {role} at {company}
Top matching skills: {top_skills}

Message:""",
)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        temperature=0.7,
    )


async def generate_messages(
    name: str,
    role: str,
    company: str,
    top_skills: list[str],
) -> dict[str, str]:
    llm = _get_llm()
    chain = MESSAGE_PROMPT | llm
    skills_str = ", ".join(top_skills[:3])

    inputs = {"name": name, "role": role, "company": company, "top_skills": skills_str}
    linkedin_resp, whatsapp_resp = await asyncio.gather(
        chain.ainvoke({**inputs, "platform": "LinkedIn DM"}),
        chain.ainvoke({**inputs, "platform": "WhatsApp"}),
    )

    return {
        "linkedin_message": linkedin_resp.content.strip(),
        "whatsapp_message": whatsapp_resp.content.strip(),
    }
