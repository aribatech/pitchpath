from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from app.db.mongo import settings

_index = None
_embeddings: OpenAIEmbeddings | None = None


def get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(settings.pinecone_index)
    return _index


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model="text-embedding-3-small",
        )
    return _embeddings


async def upsert_profile_embedding(profile_id: str, text: str) -> None:
    vector = get_embeddings().embed_query(text)
    get_index().upsert(
        vectors=[{"id": profile_id, "values": vector, "metadata": {"profile_id": profile_id}}],
        namespace="profiles",
    )


async def upsert_job_embedding(job_id: str, text: str) -> None:
    vector = get_embeddings().embed_query(text)
    get_index().upsert(
        vectors=[{"id": job_id, "values": vector, "metadata": {"job_id": job_id}}],
        namespace="jobs",
    )


async def get_profile_embedding(profile_id: str) -> list[float] | None:
    result = get_index().fetch(ids=[profile_id], namespace="profiles")
    vectors = result.get("vectors") or {}
    if profile_id in vectors:
        return vectors[profile_id]["values"]
    return None


async def get_job_embeddings_for_jobs(job_ids: list[str]) -> dict[str, list[float]]:
    result = get_index().fetch(ids=job_ids, namespace="jobs")
    vectors = result.get("vectors") or {}
    return {jid: vectors[jid]["values"] for jid in job_ids if jid in vectors}
