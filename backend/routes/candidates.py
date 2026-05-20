from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
import os
from bson import ObjectId
from datetime import datetime

from database import candidates_col, jobs_col
from auth import get_current_user
from models import StatusUpdate, InterviewSchedule, NoteCreate

router = APIRouter(prefix="/candidates", tags=["candidates"])

def serialize(doc: dict) -> dict:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for key, val in doc.items():
        if isinstance(val, datetime):
            doc[key] = val.isoformat()
    return doc

@router.get("/search")
async def search_candidates(
    q: str = Query(..., description="Semantic search query"),
    limit: int = Query(20, description="Max results to return"),
    current_user=Depends(get_current_user),
):
    """
    Global semantic search across all candidates in the ATS using FAISS.
    """
    from services.vector_store import search_resumes
    hits = await search_resumes(q, top_k=limit)
    
    if not hits:
        return []
        
    # hits looks like: [{"id": cid, "name": name, "similarity": 0.85, ...}]
    candidate_ids = [ObjectId(h["id"]) for h in hits if "id" in h]
    
    # Fetch full candidate details from DB
    candidates_dict = {}
    async for c in candidates_col.find({"_id": {"$in": candidate_ids}}):
        candidates_dict[str(c["_id"])] = serialize(c)
        
    results = []
    for h in hits:
        cid = h.get("id")
        if cid in candidates_dict:
            c = candidates_dict[cid]
            c["semantic_similarity"] = h.get("similarity", 0)
            # Add job context if available
            if c.get("job_id"):
                job = await jobs_col.find_one({"_id": ObjectId(c["job_id"])})
                if job:
                    c["original_job_title"] = job.get("title")
            results.append(c)
            
    return results

@router.get("/list")
async def list_candidates(
    job_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    skill: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    query = {}
    if job_id:
        query["job_id"] = job_id
    if status_filter:
        query["status"] = status_filter
    if min_score is not None or max_score is not None:
        query["score"] = {}
        if min_score is not None:
            query["score"]["$gte"] = min_score
        if max_score is not None:
            query["score"]["$lte"] = max_score
    if skill:
        query["skills"] = {"$regex": skill, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    candidates = []
    async for c in candidates_col.find(query).sort("score", -1):
        candidates.append(serialize(c))
    return candidates

@router.get("/compare")
async def compare_candidates(
    ids: str = Query(..., description="Comma-separated candidate IDs"),
    current_user=Depends(get_current_user),
):
    """Side-by-side comparison of 2-3 candidates."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:3]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 candidate IDs")

    result = []
    for cid in id_list:
        try:
            c = await candidates_col.find_one({"_id": ObjectId(cid)})
        except Exception:
            continue
        if not c:
            continue
        s = serialize(c)
        result.append({
            "id": s["id"],
            "name": s.get("name", "Unknown"),
            "score": s.get("score", 0),
            "technical_fit": s.get("technical_fit", 0),
            "experience_relevance": s.get("experience_relevance", 0),
            "resume_quality": s.get("resume_quality", 0),
            "experience_years": s.get("experience_years", 0),
            "skills": s.get("skills", []),
            "matched_skills": s.get("matched_skills", []),
            "missing_skills": s.get("missing_skills", []),
            "bonus_skills": s.get("bonus_skills", []),
            "risk_flags": s.get("risk_flags", []),
            "status": s.get("status", "pending"),
            "education": s.get("education", []),
            "certifications": s.get("certifications", []),
            "hiring_summary": s.get("hiring_summary", {}),
            "ai_analysis": s.get("ai_analysis", {}),
            "job_id": s.get("job_id", ""),
        })

    if len(result) < 2:
        raise HTTPException(status_code=404, detail="Could not find enough candidates")
    return result

@router.get("/compare-insights")
async def compare_insights(
    ids: str = Query(..., description="Comma-separated candidate IDs"),
    current_user=Depends(get_current_user),
):
    from fastapi.responses import StreamingResponse
    from groq import AsyncGroq
    import os
    import traceback
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:3]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 candidate IDs")

    candidates = []
    for cid in id_list:
        try:
            c = await candidates_col.find_one({"_id": ObjectId(cid)})
            if c: candidates.append(c)
        except Exception:
            continue
            
    if len(candidates) < 2:
        raise HTTPException(status_code=404, detail="Could not find enough candidates")
        
    job_id = candidates[0].get("job_id")
    job = None
    if job_id:
        job = await jobs_col.find_one({"_id": ObjectId(job_id)})
        
    prompt = "You are an expert Enterprise AI Recruiter Copilot.\n"
    prompt += f"Please provide a final hiring recommendation comparing the following {len(candidates)} candidates"
    if job:
        prompt += f" for the role of '{job.get('title')}'.\n\n"
    else:
        prompt += ".\n\n"
        
    for c in candidates:
        prompt += f"Candidate: {c.get('name', 'Unknown')}\n"
        prompt += f"AI Match Score: {c.get('score', 0):.0f}%\n"
        prompt += f"Experience: {c.get('experience_years', 0):.0f} years\n"
        prompt += f"Top Skills: {', '.join(c.get('skills', [])[:5])}\n"
        analysis = c.get("ai_analysis", {})
        if analysis:
            prompt += f"Interview Comm. Score: {analysis.get('communication_score', c.get('communication_score', 'N/A'))}\n"
            prompt += f"Interview Confidence: {analysis.get('confidence_score', 'N/A')}\n"
            prompt += f"Behavioral Risk: {analysis.get('cheating_risk', 'Low')}\n"
        prompt += f"Missing Skills: {', '.join(c.get('missing_skills', [])[:3])}\n"
        prompt += "\n"
        
    prompt += "Instructions:\n"
    prompt += "1. Write a 2-3 sentence extremely sharp and concise comparison.\n"
    prompt += "2. Explicitly name the candidates.\n"
    prompt += "3. Highlight who is the stronger technical fit, and who has better communication or lower behavioral risk.\n"
    prompt += "4. Conclude with a clear bottom-line recommendation (e.g. who to hire or advance).\n"
    prompt += "Keep it strictly professional and recruiter-focused. Do not output any markdown headers, just the text."

    try:
        groq_client = AsyncGroq(
            api_key=os.environ.get("GROQ_API_KEY")
        )
    except Exception as init_err:
        import logging
        logging.error(f"[GROQ ERROR] Initialization failed:\n{traceback.format_exc()}")
        async def err_gen():
            yield f"⚠️ Backend Configuration Error: Could not initialize Groq client. Check API key."
        return StreamingResponse(err_gen(), media_type="text/plain")

    async def generate():
        try:
            response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                temperature=0.3,
                max_tokens=250
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            err_msg = f"\n\n⚠️ AI Error: {str(e)}"
            print("[GROQ ERROR] Full Traceback:\n", traceback.format_exc())
            yield err_msg

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    c = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    result = serialize(c)

    # Enrich with job's required_skills for the profile skill breakdown
    job_id = result.get("job_id")
    if job_id:
        try:
            job = await jobs_col.find_one({"_id": ObjectId(job_id)})
            result["job_required_skills"] = job.get("required_skills", []) if job else []
        except Exception:
            result["job_required_skills"] = []
    else:
        result["job_required_skills"] = []

    return result

@router.put("/{candidate_id}/status")
async def update_status(
    candidate_id: str,
    update: StatusUpdate,
    current_user=Depends(get_current_user),
):
    from database import jobs_col
    from services.email_service import send_email, get_status_update_template
    
    valid = ["applied", "screening", "shortlisted", "interview_scheduled", "interviewed", "selected", "rejected", "on_hold"]
    if update.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    activity = {
        "action": f"Moved to {update.status}",
        "timestamp": datetime.utcnow().isoformat(),
        "author": current_user["name"]
    }
    
    result = await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"status": update.status, "updated_at": datetime.utcnow()},
         "$push": {"activity_history": activity}},
    )
    
    # Email to candidate is explicitly disabled based on user request (HR productivity focus)
    # if result.matched_count > 0 and update.status in ["shortlisted", "rejected"]:
    #     from services.email_service import get_db_email_settings, get_fallback_settings
    #     settings = await get_db_email_settings() or get_fallback_settings()
    #     app_name = settings.get("app_name", "AI Hiring Platform")
    #
    #     job = await jobs_col.find_one({"_id": ObjectId(candidate.get("job_id"))})
    #     html = get_status_update_template(
    #         candidate["name"],
    #         job.get("title", "Job Role") if job else "Job Role",
    #         update.status,
    #         app_name
    #     )
    #     await send_email(candidate.get("email"), f"Update on your application: {job.get('title', 'Role') if job else ''}", html)

    return {"message": f"Status updated to '{update.status}'"}

from pydantic import BaseModel
from typing import List

class BulkStatusUpdate(BaseModel):
    candidate_ids: List[str]
    status: str

@router.put("/bulk-status")
async def bulk_update_status(
    update: BulkStatusUpdate,
    current_user=Depends(get_current_user),
):
    valid = ["applied", "screening", "shortlisted", "interview_scheduled", "interviewed", "selected", "rejected", "on_hold"]
    if update.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    object_ids = [ObjectId(cid) for cid in update.candidate_ids]
    
    activity = {
        "action": f"Bulk moved to {update.status}",
        "timestamp": datetime.utcnow().isoformat(),
        "author": current_user["name"]
    }

    result = await candidates_col.update_many(
        {"_id": {"$in": object_ids}},
        {"$set": {"status": update.status, "updated_at": datetime.utcnow()},
         "$push": {"activity_history": activity}},
    )

    return {"message": f"Status updated to '{update.status}' for {result.modified_count} candidates"}


@router.post("/{candidate_id}/notes")
async def add_note(
    candidate_id: str,
    note: NoteCreate,
    current_user=Depends(get_current_user),
):
    note_doc = {
        "text": note.text,
        "author": current_user["name"],
        "created_at": datetime.utcnow().isoformat(),
    }
    result = await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$push": {"notes": note_doc}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"message": "Note added"}

@router.delete("/{candidate_id}")
async def delete_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    try:
        candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid candidate ID format")
        
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Delete from database
    result = await candidates_col.delete_one({"_id": ObjectId(candidate_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # 1. Clean up physical resume file from disk
    resume_path_val = candidate.get("resume_path")
    if resume_path_val:
        try:
            from config import UPLOAD_DIR
            import os
            file_path = UPLOAD_DIR / resume_path_val
            if file_path.exists():
                os.remove(file_path)
                print(f"[File Cleanup] Physical resume file removed: {file_path}")
        except Exception as file_err:
            print(f"[File Cleanup] Warning: Failed to delete physical resume: {file_err}")

    # 2. Decrement associated job's candidate count
    job_id = candidate.get("job_id")
    if job_id:
        try:
            await jobs_col.update_one(
                {"_id": ObjectId(job_id)},
                {"$inc": {"candidate_count": -1}}
            )
        except Exception as job_err:
            print(f"[Job Update] Warning: Failed to decrement candidate count: {job_err}")
            
    # 3. Schedule background FAISS vector cleanup
    try:
        import asyncio
        from services.vector_store import delete_candidate_vector
        asyncio.create_task(delete_candidate_vector(candidate_id))
    except Exception as e:
        print(f"[VectorStore] Background delete warning for candidate {candidate_id}: {e}")
        
    return {"message": "Candidate deleted successfully"}



@router.get("/{candidate_id}/resume")
async def get_candidate_resume(candidate_id: str):
    from config import UPLOAD_DIR
    import logging
    logger = logging.getLogger(__name__)

    try:
        candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid candidate ID format")

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    resume_path_val = candidate.get("resume_path")
    if not resume_path_val:
        raise HTTPException(status_code=404, detail="Resume reference missing in database")

    file_path = UPLOAD_DIR / resume_path_val
    
    if not file_path.exists():
        stripped = resume_path_val.replace("uploads/", "").replace("uploads\\", "")
        file_path = UPLOAD_DIR / stripped

    if not file_path.exists():
        logger.error(f"Resume file NOT FOUND. ID: {candidate_id}, Stored Path: {resume_path_val}, Resolved: {file_path}")
        filename = os.path.basename(resume_path_val)
        search_results = list(UPLOAD_DIR.glob(f"**/{filename}"))
        if search_results:
            file_path = search_results[0]
            logger.info(f"Fuzzy match found: {file_path}")
        else:
            raise HTTPException(status_code=404, detail=f"Resume file not found at {file_path.name}")

    ext = file_path.suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain'
    }
    media_type = mime_types.get(ext, 'application/octet-stream')
    logger.info(f"Serving resume: {file_path} as {media_type}")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=candidate.get("filename", file_path.name),
        content_disposition_type="inline"
    )
