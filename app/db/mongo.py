from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    mongodb_url: str = "mongodb://localhost:27017"
    redis_url: str = "redis://localhost:6379"
    rapidapi_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = "pitchpath"
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""
    db_name: str = "internship_agent"

    class Config:
        env_file = ".env"


settings = Settings()

_client: AsyncIOMotorClient | None = None


async def connect_mongo():
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)


async def close_mongo():
    global _client
    if _client:
        _client.close()
        _client = None


def get_db():
    if _client is None:
        raise RuntimeError("MongoDB not connected")
    return _client[settings.db_name]
