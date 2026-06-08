import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from app.db.mongo import settings

_client: chromadb.ClientAPI | None = None
_embeddings: OpenAIEmbeddings | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        path = "/tmp/chroma_db" if os.environ.get("VERCEL") else settings.chroma_persist_dir
        _client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model="text-embedding-3-small",
        )
    return _embeddings


async def upsert_profile_embedding(profile_id: str, text: str) -> None:
    client = get_chroma_client()
    emb = get_embeddings()
    collection = client.get_or_create_collection("profiles")
    vector = emb.embed_query(text)
    collection.upsert(
        ids=[profile_id],
        embeddings=[vector],
        metadatas=[{"profile_id": profile_id}],
        documents=[text],
    )


async def upsert_job_embedding(job_id: str, text: str) -> None:
    client = get_chroma_client()
    emb = get_embeddings()
    collection = client.get_or_create_collection("jobs")
    vector = emb.embed_query(text)
    collection.upsert(
        ids=[job_id],
        embeddings=[vector],
        metadatas=[{"job_id": job_id}],
        documents=[text],
    )


async def get_profile_embedding(profile_id: str) -> list[float] | None:
    client = get_chroma_client()
    collection = client.get_or_create_collection("profiles")
    result = collection.get(ids=[profile_id], include=["embeddings"])
    embs = result.get("embeddings")
    if embs is not None and len(embs) > 0:
        e = embs[0]
        return e.tolist() if hasattr(e, "tolist") else list(e)
    return None


async def get_job_embeddings_for_jobs(job_ids: list[str]) -> dict[str, list[float]]:
    client = get_chroma_client()
    collection = client.get_or_create_collection("jobs")
    result = collection.get(ids=job_ids, include=["embeddings"])
    out = {}
    embs = result.get("embeddings")
    if embs is None:
        return out
    for jid, emb in zip(result["ids"], embs):
        out[jid] = emb.tolist() if hasattr(emb, "tolist") else list(emb)
    return out
