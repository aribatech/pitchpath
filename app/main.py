from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db.mongo import connect_mongo, close_mongo
from app.db.redis import connect_redis, close_redis
from app.api import resume, jobs, tracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    await connect_redis()
    yield
    await close_mongo()
    await close_redis()


app = FastAPI(
    title="AI Internship Finder",
    description="Multi-agent pipeline: upload resume → match internships → outreach + track applications",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(tracker.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "AI Internship Finder"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
