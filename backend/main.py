from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import io
import sys
import os
import uuid
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, db_manager, candidates_col, jobs_col, users_col
from auth import verify_password, create_access_token, get_current_user
from models import JobCreate, StatusUpdate, InterviewSchedule, NoteCreate
from resume_parser import parse_resume_file
from matching import rank_all_resumes
from feedback import get_resume_feedback
from reports import generate_csv_report, generate_pdf_report
from routes.candidates import router as candidates_router
from services.vector_store import init_vector_store, bulk_index_resumes
from services.hiring_summary import generate_hiring_summary

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.email_service import send_email, get_reminder_template

scheduler = AsyncIOScheduler()

async def check_upcoming_interviews():
    """Background task: send 15-min reminder to HR only. Never emails the candidate."""
    if not db_manager.is_connected:
        return

    now = datetime.utcnow()
    try:
        async for candidate in candidates_col.find({
            "status": "interview_scheduled",
            "interview.date": {"$exists": True},
            "interview.time": {"$exists": True}
        }):
            interview = candidate.get("interview", {})
            try:
                dt_str = f"{interview['date']}T{interview['time']}:00"
                interview_time = datetime.fromisoformat(dt_str)
                diff_minutes = (interview_time - now).total_seconds() / 60

                logs = interview.get("reminders_sent_logs", [])
                sent_types = [l["type"] for l in logs if l.get("status") == "success"]

                from services.email_service import get_db_email_settings, get_fallback_settings, send_email, get_reminder_template
                settings = await get_db_email_settings() or get_fallback_settings()
                app_name = settings.get("app_name", "AI Hiring Platform")

                # 15-minute HR reminder only
                if 12 <= diff_minutes <= 18 and "15m" not in sent_types:
                    recruiter_email = interview.get("recruiter_email") or candidate.get("scheduled_by_email")
                    if not recruiter_email:
                        print(f"[Scheduler] No recruiter email for {candidate.get('name')} — skipping reminder")
                        continue
                    
                    job_title = "Scheduled Role"
                    try:
                        job = await jobs_col.find_one({"_id": ObjectId(candidate["job_id"])})
                        if job:
                            job_title = job.get("title", job_title)
                    except Exception:
                        pass
                    
                    html = get_reminder_template(
                        candidate['name'], job_title,
                        interview['time'], interview.get('link'), 15, app_name
                    )
                    subject = f"🔔 Interview in 15 mins — {candidate['name']} | {job_title}"
                    
                    print(f"[Scheduler] Sending 15min HR reminder to {recruiter_email} for candidate {candidate['name']}")
                    success = await send_email(recruiter_email, subject, html)
                    
                    log_entry = {"type": "15m", "sent_at": datetime.utcnow(), "status": "success" if success else "failed", "recipient": recruiter_email}
                    await candidates_col.update_one(
                        {"_id": candidate["_id"]},
                        {"$push": {"interview.reminders_sent_logs": log_entry}}
                    )

            except (ValueError, KeyError) as e:
                print(f"⚠️ [Scheduler] Skipping invalid interview data for {candidate.get('_id')}: {e}")
    except Exception as e:
        print(f"❌ [Scheduler] Batch processing failed: {e}")

# Global state tracking for background vector sync
vector_sync_status = {
    "status": "idle",       # "idle", "syncing", "completed", "failed"
    "processed": 0,
    "total": 0,
    "started_at": None,
    "completed_at": None,
    "error": None
}

async def run_background_vector_sync():
    """Performs non-blocking, async-safe incremental vector sync on startup."""
    global vector_sync_status
    
    # Wait for database reconnection to succeed if it's currently offline
    for _ in range(30):
        if db_manager.is_connected:
            break
        await asyncio.sleep(1)
        
    if not db_manager.is_connected:
        vector_sync_status["status"] = "failed"
        vector_sync_status["error"] = "Database connection offline at startup"
        return
        
    try:
        from services.vector_store import get_store_stats, get_indexed_candidate_ids, bulk_index_resumes, rebuild_resume_index, _store
        
        # 1. Fetch all candidates with raw_text
        candidates = []
        async for c in candidates_col.find({"raw_text": {"$exists": True}}, {"_id": 1, "name": 1, "raw_text": 1, "job_id": 1, "status": 1, "skills": 1, "score": 1}):
            c["id"] = str(c.pop("_id"))
            candidates.append(c)
            
        if not candidates:
            vector_sync_status["status"] = "idle"
            return
            
        # 2. Self-Healing Rebuild: If FAISS index count doesn't match metadata length, auto-rebuild from database!
        if _store.resume_index and _store.resume_index.ntotal != len(_store.resume_meta):
            print(f"[VectorStore Startup] WARNING: FAISS index count ({_store.resume_index.ntotal}) does not match metadata length ({len(_store.resume_meta)}). Auto-triggering self-healing index rebuild...")
            vector_sync_status["status"] = "syncing"
            vector_sync_status["total"] = len(candidates)
            vector_sync_status["processed"] = 0
            vector_sync_status["started_at"] = datetime.utcnow().isoformat()
            
            await rebuild_resume_index(candidates)
            
            vector_sync_status["status"] = "completed"
            vector_sync_status["processed"] = len(candidates)
            vector_sync_status["completed_at"] = datetime.utcnow().isoformat()
            print("[VectorStore Startup] Self-healing rebuild complete!")
            return

        # 3. Standard Incremental Sync: Get already indexed IDs from disk cache
        indexed_ids = get_indexed_candidate_ids()
        
        # Filter to only get candidates NOT yet indexed (incremental sync)
        to_index = [c for c in candidates if c["id"] not in indexed_ids]
        
        if not to_index:
            print("[VectorStore Startup] FAISS index is fully synchronized. No new resumes to index.")
            vector_sync_status["status"] = "completed"
            vector_sync_status["total"] = len(candidates)
            vector_sync_status["processed"] = len(candidates)
            return

        print(f"[VectorStore Startup] Incremental sync: {len(to_index)} of {len(candidates)} candidates need indexing.")
        vector_sync_status["status"] = "syncing"
        vector_sync_status["total"] = len(candidates)
        vector_sync_status["processed"] = len(candidates) - len(to_index)
        vector_sync_status["started_at"] = datetime.utcnow().isoformat()
        
        # Index in small chunks to prevent event loop blocking
        chunk_size = 10
        for i in range(0, len(to_index), chunk_size):
            chunk = to_index[i:i+chunk_size]
            await bulk_index_resumes(chunk)
            
            vector_sync_status["processed"] += len(chunk)
            # Cooperatively yield control back to the FastAPI event loop
            await asyncio.sleep(0.02)
            
        print("[VectorStore Startup] Incremental sync complete!")
        vector_sync_status["status"] = "completed"
        vector_sync_status["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        print(f"[VectorStore Startup] Sync failed: {e}")
        vector_sync_status["status"] = "failed"
        vector_sync_status["error"] = str(e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Print env diagnostics immediately so we can see SMTP config on startup
    from services.email_service import print_env_diagnostics
    print_env_diagnostics()

    # Initialize DB with retries (will not block startup if connection is offline)
    success = await init_db()
    if not success:
        print("[Startup] Application starting in Degraded Mode (Database Offline)")

    
    # Start background reconnection regardless of initial success
    db_manager.start_background_reconnection()
    
    # Initialize Vector Store (will load existing caches from disk instantly)
    await init_vector_store()
    
    # Background Task
    scheduler.add_job(check_upcoming_interviews, 'interval', minutes=1)
    scheduler.start()
    
    # Vector Sync - run completely non-blocking in background
    asyncio.create_task(run_background_vector_sync())
    
    yield
    scheduler.shutdown()
    db_manager.stop_background_reconnection()


app = FastAPI(title="ATS Platform API", version="1.0.0", lifespan=lifespan)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    from database import get_db_status
    from services.vector_store import get_store_stats
    from services.email_service import get_db_email_settings
    
    db_status = get_db_status()
    vector_stats = get_store_stats()
    
    # Check if email is configured
    try:
        email_settings = await get_db_email_settings()
        email_status = "configured" if email_settings else "demo_fallback"
    except:
        email_status = "unavailable"

    return {
        "status": "ok" if db_status["status"] == "connected" else "degraded",
        "database": db_status,
        "vector_store": {
            **vector_stats,
            "sync_status": vector_sync_status
        },
        "email_service": email_status,
        "scheduler": "running" if scheduler.running else "stopped"
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────── DEBUG ────────────────────────────────────────────

# ─────────────────────── DEBUG DIRECT EMAIL ────────────────────────────────

@app.post("/debug/direct-email")
async def debug_direct_email(current_user=Depends(get_current_user)):
    """
    Bypasses interview scheduling completely.
    Directly calls send_email() to sandhyagowda506@gmail.com.
    Use this to isolate whether SMTP works independently of the interview flow.
    """
    print("\n[DEBUG ROUTE] /debug/direct-email called")
    print(f"[DEBUG ROUTE] Logged-in user: {current_user.get('email')}")

    from services.email_service import send_email, get_fallback_settings

    target = "sandhyagowda506@gmail.com"
    subject = "TEST EMAIL FROM HIREIQ"
    html = """
    <div style="font-family:sans-serif;padding:24px;border:2px solid #4f46e5;border-radius:12px;max-width:500px">
        <h2 style="color:#4f46e5;margin-top:0">✅ HireIQ Direct Email Test</h2>
        <p>This email was sent directly from the <b>/debug/direct-email</b> route,
        bypassing all interview scheduling logic.</p>
        <p>If you received this, <b>SMTP is working correctly</b>.</p>
        <p>The issue would then be in the interview scheduling flow, not SMTP.</p>
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0">
        <p style="font-size:12px;color:#94a3b8">Sent at: {}</p>
    </div>
    """.format(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))

    print(f"[DEBUG ROUTE] Calling send_email() to {target}...")
    result = await send_email(target, subject, html)
    print(f"[DEBUG ROUTE] send_email() returned: {result}")

    settings = get_fallback_settings()
    return {
        "email_sent": result,
        "target": target,
        "smtp_host": settings.get("smtp_host"),
        "smtp_port": settings.get("smtp_port"),
        "smtp_user": settings.get("smtp_user"),
        "from_email": settings.get("from_email"),
        "smtp_password_set": bool(settings.get("smtp_password")),
        "message": "Check your inbox AND the backend terminal for step-by-step logs."
    }


@app.post("/debug/test-db")
async def test_db_connection():
    """Manual trigger for DB diagnostics."""
    success, info = db_manager.verify_dns()
    status = db_manager.get_status()
    
    return {
        "dns_diagnostics": info if success else {"error": info},
        "db_manager_status": status,
        "is_connected": db_manager.is_connected,
        "recommendations": [
            "Check if cluster0.a2fjt.mongodb.net is correct",
            "Verify Atlas Whitelist (Allow access from anywhere 0.0.0.0/0 for testing)",
            "Try Standard Connection String (mongodb://) if SRV fails",
            "Check for typos in .env MONGO_URI"
        ]
    }


@app.get("/debug/groq-test")
async def debug_groq_test():
    """Direct Groq credentials and model execution diagnostics."""
    import os
    import traceback
    from groq import AsyncGroq
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    api_key = os.getenv("GROQ_API_KEY")
    
    diagnostics = {
        "groq_api_key_exists": bool(api_key),
        "groq_api_key_prefix": api_key[:10] if api_key else None,
        "model_used": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1"
    }
    
    if not api_key:
        return {
            "success": False,
            "error": "GROQ_API_KEY is not set in environment variables.",
            "diagnostics": diagnostics
        }
        
    try:
        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=20,
            temperature=0.2
        )
        return {
            "success": True,
            "response": response.choices[0].message.content.strip(),
            "diagnostics": diagnostics
        }
    except Exception as e:
        tb = traceback.format_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": tb,
            "diagnostics": diagnostics
        }


app.include_router(candidates_router)
from routes.jobs import router as jobs_router
app.include_router(jobs_router)
from routes.interviews import router as interviews_router
app.include_router(interviews_router)
from routes.chat import router as chat_router
app.include_router(chat_router)
from routes.audio import router as audio_router
app.include_router(audio_router)
from routes.settings import router as settings_router
app.include_router(settings_router)
from routes.auth import router as auth_router
app.include_router(auth_router)


def serialize(doc: dict) -> dict:
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    # Convert datetime fields to ISO strings
    for key, val in doc.items():
        if isinstance(val, datetime):
            doc[key] = val.isoformat()
    return doc


# ─────────────────────────── PROFILE ──────────────────────────────────────────

@app.get("/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user.get("role", "hr"),
    }


# ─────────────────────── RESUME UPLOAD ─────────────────────────────────────

@app.post("/resumes/upload")
async def upload_resumes(
    job_id: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user),
):
    job = await jobs_col.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    inserted = []
    
    from config import UPLOAD_DIR
    import re

    for file in files:
        # Sanitize filename: replace spaces with underscores, remove special chars
        clean_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
        # Ensure unique filename to prevent overwrites
        unique_filename = f"{uuid.uuid4().hex[:8]}_{clean_filename}"
        
        content = await file.read()
        parsed = parse_resume_file(content, file.filename)

        # Save to disk using pathlib
        save_path = UPLOAD_DIR / unique_filename
        with open(save_path, "wb") as f:
            f.write(content)

        doc = {
            "job_id": job_id,
            "filename": file.filename,
            "resume_path": unique_filename, # Store only the filename (relative to UPLOAD_DIR)
            "name": parsed["name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "skills": parsed["skills"],
            "experience_years": parsed["experience_years"],
            "education": parsed["education"],
            "location": parsed["location"],
            "certifications": parsed.get("certifications", []),
            "projects": parsed.get("projects", []),
            "raw_text": parsed["raw_text"],
            "status": "pending",
            "score": 0.0,
            "semantic_score": 0.0,
            "skill_score": 0.0,
            "experience_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "exact_matches": [],
            "semantic_matches": [],
            "partial_matches": [],
            "bonus_skills": [],
            "match_explanation": {},
            "feedback": {}, # Initialized as object
            "notes": [],
            "interview": None,
            "uploaded_at": datetime.utcnow(),
        }
        result = await candidates_col.insert_one(doc)
        cid = str(result.inserted_id)
        inserted.append(cid)
        # Auto-index in FAISS
        try:
            from services.vector_store import index_resume
            await index_resume(
                candidate_id=cid,
                name=parsed["name"],
                text=parsed["raw_text"],
                extra={"job_id": job_id, "status": "pending", "skills": parsed["skills"]},
            )
        except Exception as ve:
            print(f"[VectorStore] Index warning: {ve}")

    return {"uploaded": len(inserted), "candidate_ids": inserted}


@app.post("/resumes/rank")
async def rank_resumes(
    job_id: str = Form(...),
    current_user=Depends(get_current_user),
):
    job = await jobs_col.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = []
    async for c in candidates_col.find({"job_id": job_id}):
        candidates.append(c)

    if not candidates:
        raise HTTPException(status_code=400, detail="No candidates found for this job")

    ranked = await rank_all_resumes(job["description"], candidates)

    for item in ranked:
        cid = item["_id"]
        feedback = get_resume_feedback(item.get("raw_text", ""), job["description"])

        # Generate AI hiring summary
        hiring_sum = item.get("hiring_summary", {})
        if not hiring_sum:
            try:
                hiring_sum = await generate_hiring_summary(
                    candidate=item,
                    job=job,
                    match_explanation=item.get("match_explanation", {}),
                )
            except Exception as hs_err:
                print(f"[HiringSummary] Failed for {item.get('name')}: {hs_err}")

        await candidates_col.update_one(
            {"_id": cid},
            {"$set": {
                "score":                 item["score"],
                "semantic_score":        item["semantic_score"],
                "skill_score":           item["skill_score"],
                "experience_score":      item["experience_score"],
                "technical_fit":         item.get("technical_fit", 0),
                "experience_relevance":  item.get("experience_relevance", 0),
                "resume_quality":        item.get("resume_quality", 0),
                "risk_flags":            item.get("risk_flags", []),
                "matched_skills":        item["matched_skills"],
                "missing_skills":        item["missing_skills"],
                "exact_matches":         item.get("exact_matches", []),
                "semantic_matches":      item.get("semantic_matches", []),
                "partial_matches":       item.get("partial_matches", []),
                "bonus_skills":          item.get("bonus_skills", []),
                "match_explanation":     item.get("match_explanation", {}),
                "feedback":              feedback,
                "hiring_summary":        hiring_sum,
                "ranked_at":             datetime.utcnow(),
                
                # Upgraded Matching Engine fields
                "confidence_score":      item.get("confidence_score", 75.0),
                "ambiguity_detection":   item.get("ambiguity_detection", []),
                "extraction_reliability":item.get("extraction_reliability", "Medium"),
                "leadership_match":      item.get("leadership_match", "No"),
                "communication_match":   item.get("communication_match", "Baseline"),
                "recruiter_explanation": item.get("recruiter_explanation", ""),
            }},
        )
        # Update FAISS metadata with new score
        try:
            from services.vector_store import index_resume
            await index_resume(
                candidate_id=str(cid),
                name=item.get("name", ""),
                text=item.get("raw_text", ""),
                extra={"job_id": job_id, "score": item["score"],
                       "status": item.get("status", "pending"),
                       "skills": item.get("skills", [])},
            )
        except Exception:
            pass

    return {"ranked": len(ranked), "message": "Ranking complete"}


# ─────────────────────── DASHBOARD ─────────────────────────────────────────

@app.get("/dashboard/stats")
async def dashboard_stats(
    job_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    match_q = {"job_id": job_id} if job_id else {}

    pipeline = [
        {"$match": match_q},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "avg_score": {"$avg": "$score"}}},
    ]

    status_counts = {"applied": 0, "screening": 0, "shortlisted": 0,
                     "interview_scheduled": 0, "interviewed": 0, "selected": 0, "rejected": 0, "on_hold": 0}
    total = 0
    score_sum = 0.0

    async for doc in candidates_col.aggregate(pipeline):
        st = doc["_id"]
        cnt = doc["count"]
        if st in status_counts:
            status_counts[st] = cnt
        total += cnt
        score_sum += (doc.get("avg_score") or 0) * cnt

    avg_score = round(score_sum / total, 2) if total > 0 else 0.0

    # Score distribution buckets (scores stored as 0-100)
    brackets = [(0, 20, "0-20%"), (20, 40, "20-40%"),
                 (40, 60, "40-60%"), (60, 80, "60-80%"), (80, 101, "80-100%")]
    score_dist = []
    for low, high, label in brackets:
        q = {**match_q, "score": {"$gte": low, "$lt": high}}
        count = await candidates_col.count_documents(q)
        score_dist.append({"range": label, "count": count})

    # ── Upcoming Interviews ───────────────────────────────────────────
    upcoming = []
    now_utc = datetime.utcnow()
    
    cursor = candidates_col.find(
        {"status": "interview_scheduled", **match_q},
        {"name": 1, "interview": 1, "job_id": 1}
    )
    
    async for c in cursor:
        interview = c.get("interview", {})
        if not interview or not interview.get("date") or not interview.get("time"):
            continue
        
        job = await jobs_col.find_one({"_id": ObjectId(c["job_id"])})
        
        # Build ISO datetime string from stored date + time
        try:
            dt_str = f"{interview['date']}T{interview['time']}:00"
            interview_dt = datetime.fromisoformat(dt_str)
        except Exception:
            interview_dt = None
        
        # Compute status label relative to now (UTC used as base)
        interview_status = "upcoming"
        countdown = None
        if interview_dt:
            diff_minutes = (interview_dt - now_utc).total_seconds() / 60
            diff_days = diff_minutes / (60 * 24)
            
            if diff_minutes < -30:
                interview_status = "overdue"
                # Also patch candidate status to missed
                await candidates_col.update_one(
                    {"_id": c["_id"], "status": "interview_scheduled"},
                    {"$set": {"status": "interview_missed"}}
                )
            elif diff_minutes < 0:
                interview_status = "missed"
            elif diff_minutes <= 60:
                interview_status = "today"
                countdown = f"Starts in {int(diff_minutes)} mins" if diff_minutes > 1 else "Starting now"
            elif diff_days < 1:
                interview_status = "today"
            elif diff_days < 2:
                interview_status = "tomorrow"
            else:
                interview_status = "upcoming"
        
        upcoming.append({
            "id": str(c["_id"]),
            "candidate_name": c["name"],
            "job_title": job.get("title", "Role") if job else "Role",
            "date": interview.get("date"),
            "time": interview.get("time"),
            "datetime_iso": interview_dt.isoformat() if interview_dt else None,
            "link": interview.get("meeting_link"),
            "mode": interview.get("mode"),
            "interview_status": interview_status,
            "countdown": countdown,
        })
    
    # Sort nearest interview first
    def sort_key(item):
        if item.get("datetime_iso"):
            try:
                return datetime.fromisoformat(item["datetime_iso"])
            except Exception:
                pass
        return datetime(2099, 1, 1)
    
    upcoming.sort(key=sort_key)

    return {
        "total": total,
        "avg_score": avg_score,
        **status_counts,
        "score_distribution": score_dist,
        "status_distribution": [
            {"status": k, "count": v} for k, v in status_counts.items()
        ],
        "upcoming_interviews": upcoming,
    }


# ─────────────────────── NOTIFICATIONS ─────────────────────────────────────

@app.get("/notifications/recent")
async def recent_notifications(current_user=Depends(get_current_user)):
    """Aggregates email logs and security alerts into a unified notification feed."""
    notifs = []
    
    # 1. Fetch recent security alerts from all candidates
    cursor = candidates_col.find(
        {"ai_analysis.security_evidence": {"$exists": True, "$ne": []}},
        {"name": 1, "ai_analysis.security_evidence": 1, "ai_analysis.event_log": 1}
    ).sort("ranked_at", -1).limit(5)
    
    async for c in cursor:
        evidence = c.get("ai_analysis", {}).get("security_evidence", [])
        if evidence:
            notifs.append({
                "id": f"sec_{str(c['_id'])}",
                "type": "security",
                "message": f"Integrity Alert: {c['name']} - {evidence[0]}",
                "time": "Just now", # In production, use actual event timestamps
                "read": False
            })

    # 2. Fetch email reminder logs
    cursor = candidates_col.find(
        {"interview.reminders_sent_logs": {"$exists": True, "$ne": []}},
        {"name": 1, "interview.reminders_sent_logs": 1}
    ).limit(5)
    
    async for c in cursor:
        logs = c.get("interview", {}).get("reminders_sent_logs", [])
        if logs:
            last_log = logs[-1]
            notifs.append({
                "id": f"rem_{str(c['_id'])}_{last_log.get('type')}",
                "type": "reminder",
                "message": f"Reminder Sent: {c['name']} ({last_log.get('type')} alert)",
                "time": last_log.get("sent_at").strftime("%I:%M %p"),
                "read": True
            })

    return sorted(notifs, key=lambda x: x["time"], reverse=True)[:10]


# ─────────────────────── EXPORTS ───────────────────────────────────────────

@app.get("/interviews/export/{candidate_id}")
async def export_interview_report(candidate_id: str, current_user=Depends(get_current_user)):
    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if not candidate.get("ai_analysis"):
        raise HTTPException(status_code=400, detail="Interview analysis not available for this candidate")

    job = await jobs_col.find_one({"_id": ObjectId(candidate["job_id"])})
    
    from reports import generate_interview_report
    content = generate_interview_report(candidate, job or {})
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=interview_report_{candidate['name'].replace(' ', '_')}.pdf"},
    )


# ─────────────────────── REPORTS ───────────────────────────────────────────

@app.get("/report/download")
async def download_report(
    format: str = Query("csv"),
    job_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    query = {"job_id": job_id} if job_id else {}
    candidates = []
    async for c in candidates_col.find(query).sort("score", -1):
        candidates.append(c)

    if format == "csv":
        content = generate_csv_report(candidates)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=candidates_report.csv"},
        )
    elif format == "pdf":
        content = generate_pdf_report(candidates)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=candidates_report.pdf"},
        )
    else:
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'pdf'")
