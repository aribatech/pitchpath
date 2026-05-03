import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.pdf_parser import extract_text_from_pdf
from app.agents.resume_agent import is_resume, parse_resume, suggest_keywords
from app.services.vector_store import upsert_profile_embedding
from app.db.mongo import get_db

router = APIRouter(prefix="/resume", tags=["Resume"])

PDF_MAGIC = b"%PDF"


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    header = await file.read(4)
    await file.seek(0)
    if header != PDF_MAGIC:
        raise HTTPException(status_code=400, detail="File is not a valid PDF.")

    raw_text = await extract_text_from_pdf(file)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from this PDF.")

    if not await is_resume(raw_text):
        raise HTTPException(
            status_code=422,
            detail="This does not look like a resume. Please upload a valid resume PDF."
        )

    profile = await parse_resume(raw_text)
    profile.keywords = await suggest_keywords(profile)

    profile_id = str(uuid.uuid4())
    doc = profile.model_dump()
    doc["_id"] = profile_id

    db = get_db()
    await db.profiles.insert_one(doc)

    embedding_text = f"{profile.name} {' '.join(profile.skills)} {profile.summary} {profile.raw_text}"
    await upsert_profile_embedding(profile_id, embedding_text)

    return {"id": profile_id, **profile.model_dump(exclude={"raw_text"})}


@router.get("/all")
async def list_profiles():
    db = get_db()
    docs = await db.profiles.find({}, {"name": 1, "email": 1, "created_at": 1}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {"profiles": docs}


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    db = get_db()
    doc = await db.profiles.find_one({"_id": profile_id}, {"raw_text": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found.")
    doc["id"] = doc.pop("_id")
    return doc
