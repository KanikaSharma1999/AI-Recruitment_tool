from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from bson import ObjectId
from datetime import datetime

from database import jobs_col, candidates_col
from auth import get_current_user
from models import JobCreate
from resume_parser import extract_skills   # avoid heavy model load from matching.py

router = APIRouter(prefix="/jobs", tags=["jobs"])

def serialize(doc: dict) -> dict:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for key, val in doc.items():
        if isinstance(val, datetime):
            doc[key] = val.isoformat()
    return doc

@router.post("/create")
async def create_job(job: JobCreate, current_user=Depends(get_current_user)):
    # Advanced JD Parsing
    from resume_parser import parse_job_description
    parsed = parse_job_description(job.description)
    
    required_skills = job.required_skills or parsed["required_skills"]
    preferred_skills = parsed["preferred_skills"]
    detected_roles = parsed["roles"]

    doc = job.model_dump()
    doc["required_skills"] = required_skills
    doc["preferred_skills"] = preferred_skills
    doc["detected_roles"] = detected_roles
    doc["required_experience"] = parsed["experience_years"]
    doc["created_at"] = datetime.utcnow()
    doc["created_by"] = current_user["email"]
    
    result = await jobs_col.insert_one(doc)
    job_id = str(result.inserted_id)

    # Auto-index JD in FAISS vector store
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from services.vector_store import index_job
        import asyncio
        asyncio.create_task(index_job(job_id, job.title, job.description))
    except Exception as e:
        print(f"[VectorStore] JD index warning: {e}")

    return {"id": job_id, "message": "Job created successfully"}

@router.get("/list")
async def list_jobs(current_user=Depends(get_current_user)):
    jobs = []
    async for job in jobs_col.find().sort("created_at", -1):
        j = serialize(job)
        j["candidate_count"] = await candidates_col.count_documents({"job_id": j["id"]})
        jobs.append(j)
    return jobs

@router.get("/{job_id}")
async def get_job(job_id: str, current_user=Depends(get_current_user)):
    job = await jobs_col.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize(job)

@router.delete("/{job_id}")
async def delete_job(job_id: str, current_user=Depends(get_current_user)):
    try:
        job = await jobs_col.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
        
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # 1. Clean up physical resume files from disk for all candidates associated with this job
    try:
        from config import UPLOAD_DIR
        import os
        async for candidate in candidates_col.find({"job_id": job_id}):
            resume_path_val = candidate.get("resume_path")
            if resume_path_val:
                file_path = UPLOAD_DIR / resume_path_val
                if file_path.exists():
                    os.remove(file_path)
                    print(f"[File Cleanup] Physical resume file removed for candidate {candidate.get('name')}: {file_path}")
    except Exception as file_err:
        print(f"[File Cleanup] Warning: Failed to cascade delete physical resumes: {file_err}")

    # 2. Cascade delete candidates and the job posting from the database
    delete_candidates = await candidates_col.delete_many({"job_id": job_id})
    delete_job = await jobs_col.delete_one({"_id": ObjectId(job_id)})
    
    # 3. Run FAISS vector cleanup in background to ensure immediate UI responsiveness
    try:
        import asyncio
        from services.vector_store import delete_job_vector
        asyncio.create_task(delete_job_vector(job_id))
    except Exception as e:
        print(f"[VectorStore] Background delete warning for job {job_id}: {e}")
        
    return {
        "message": "Job and associated data deleted successfully",
        "job_deleted": delete_job.deleted_count,
        "candidates_deleted": delete_candidates.deleted_count
    }


@router.get("/{job_id}/shortlisted-report")
async def get_shortlisted_report(
    job_id: str,
    format: str = Query("pdf", description="Format: pdf or excel"),
    current_user=Depends(get_current_user)
):
    try:
        job = await jobs_col.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = []
    # Temporary fix: Generate report for ALL candidates for this job instead of strictly "shortlisted"
    # This prevents empty reports and includes candidates in various pipeline stages.
    async for c in candidates_col.find({"job_id": job_id}).sort("score", -1):
        candidates.append(c)
        
    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found for this job")

    from services.report_generator import generate_shortlisted_pdf_report, generate_shortlisted_excel_report
    import io

    if format.lower() == "excel":
        file_bytes = generate_shortlisted_excel_report(job, candidates)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"Shortlisted_Report_{job_id}.xlsx"
    else:
        file_bytes = generate_shortlisted_pdf_report(job, candidates)
        media_type = "application/pdf"
        filename = f"Shortlisted_Report_{job_id}.pdf"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
