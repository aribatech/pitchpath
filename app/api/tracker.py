import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.db.mongo import get_db
from app.models.application import ApplicationCreate, ApplicationStatusUpdate
from app.agents.message_agent import generate_messages

router = APIRouter(prefix="/tracker", tags=["Tracker"])


async def _auto_mark_no_reply():
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=14)
    await db.applications.update_many(
        {"status": "applied", "last_updated": {"$lt": cutoff}},
        {"$set": {"status": "no_reply", "last_updated": datetime.utcnow()}},
    )


@router.post("/apply")
async def create_application(payload: ApplicationCreate, background_tasks: BackgroundTasks):
    db = get_db()

    match_doc = await db.matches.find_one({"_id": payload.match_id})
    if not match_doc:
        raise HTTPException(status_code=404, detail="Match not found.")
    profile_doc = await db.profiles.find_one({"_id": payload.profile_id})
    if not profile_doc:
        raise HTTPException(status_code=404, detail="Profile not found.")

    messages = await generate_messages(
        name=profile_doc.get("name", ""),
        role=payload.role,
        company=payload.company,
        top_skills=profile_doc.get("skills", [])[:3],
    )

    doc = {
        "_id":              str(uuid.uuid4()),
        "profile_id":       payload.profile_id,
        "match_id":         payload.match_id,
        "company":          payload.company,
        "role":             payload.role,
        "status":           "applied",
        "linkedin_message": messages["linkedin_message"],
        "whatsapp_message": messages["whatsapp_message"],
        "notes":            payload.notes,
        "applied_at":       datetime.utcnow(),
        "last_updated":     datetime.utcnow(),
    }
    await db.applications.insert_one(doc)
    background_tasks.add_task(_auto_mark_no_reply)

    return {"id": doc["_id"], **messages}


@router.patch("/{application_id}/status")
async def update_status(application_id: str, payload: ApplicationStatusUpdate):
    db = get_db()
    update = {"status": payload.status, "last_updated": datetime.utcnow()}
    if payload.notes is not None:
        update["notes"] = payload.notes

    result = await db.applications.update_one({"_id": application_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"id": application_id, "status": payload.status}


@router.get("/{profile_id}")
async def get_board(profile_id: str):
    db = get_db()
    docs = await db.applications.find({"profile_id": profile_id}).sort("applied_at", -1).to_list(100)
    for d in docs:
        d["id"] = d.pop("_id")
    return {"profile_id": profile_id, "total": len(docs), "applications": docs}


@router.delete("/{application_id}")
async def delete_application(application_id: str):
    db = get_db()
    result = await db.applications.delete_one({"_id": application_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"deleted": application_id}
