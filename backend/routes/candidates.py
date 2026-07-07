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

    # Normalize array fields that may have been stored as strings or dicts
    _array_fields = [
        "skills", "matched_skills", "missing_skills", "exact_matches",
        "semantic_matches", "partial_matches", "bonus_skills", "risk_flags",
        "certifications", "education", "projects", "job_titles", "companies",
        "technical_skills", "soft_skills", "employment_timeline",
        "ambiguity_detection", "notes", "activity_history",
    ]
    for field in _array_fields:
        val = doc.get(field)
        if val is None:
            doc[field] = []
        elif isinstance(val, str):
            # Was stored as comma-joined string — split back
            doc[field] = [s.strip() for s in val.split(",") if s.strip()] if val.strip() else []
        # dicts/objects stay as-is (e.g. employment_timeline entries)

    # Normalize numeric score fields
    _score_fields = [
        "score", "ai_match_score", "skill_score", "skills_score",
        "experience_score", "experience_relevance", "semantic_score",
        "technical_fit", "resume_quality", "projects_score",
        "certification_score", "certifications_score", "confidence_score",
        "leadership_score", "communication_score", "domain_match_score",
    ]
    for field in _score_fields:
        val = doc.get(field)
        if val is not None:
            try:
                doc[field] = round(float(val), 2)
            except (TypeError, ValueError):
                doc[field] = 0.0

    # Normalize hiring_summary — ensure it's a dict not a string
    hs = doc.get("hiring_summary")
    if isinstance(hs, str):
        try:
            import json
            doc["hiring_summary"] = json.loads(hs)
        except Exception:
            doc["hiring_summary"] = {"narrative": hs}
    elif hs is None:
        doc["hiring_summary"] = {}

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
    async for c in candidates_col.find({"_id": {"$in": candidate_ids}, "created_by": current_user["email"]}):
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
    query = {"created_by": current_user["email"]}
    if job_id:
        query["job_id"] = job_id
    if status_filter:
        legacy_map = {
            "pending": "applied",
            "applied": "applied",
            "screening": "screening",
            "shortlisted": "shortlisted",
            "interview_scheduled": "interview_scheduled",
            "interview_live": "interview_scheduled",
            "interview_missed": "interview_scheduled",
            "interviewed": "interview_completed",
            "interview_completed": "interview_completed",
            "selected": "offered",
            "offered": "offered",
            "hired": "hired",
            "rejected": "rejected",
            "on_hold": "screening"
        }
        canonical = legacy_map.get(status_filter.lower().strip(), status_filter)
        query["$or"] = [
            {"pipeline_stage": canonical},
            {"status": canonical},
            {"status": status_filter}
        ]
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

@router.post("/rerank/{candidate_id}")
async def rerank_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    """Re-run the full LLM extraction + AI intelligence pipeline for one candidate."""
    import io, datetime
    from services.llm_parser import parse_resume_with_llm, parse_jd_with_llm, generate_candidate_intelligence

    try:
        c = await candidates_col.find_one({"_id": ObjectId(candidate_id), "created_by": current_user["email"]})
    except Exception:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # ── Load resume file ──────────────────────────────────────────────────────
    raw_text = c.get("resume_text") or c.get("raw_text") or ""

    if not raw_text:
        resume_path_val = c.get("resume_path") or c.get("file_path") or c.get("filename")
        if resume_path_val:
            content = None
            is_pdf = False
            
            # Extract filename
            filename_val = c.get("filename") or os.path.basename(resume_path_val)
            relative_path = resume_path_val
            
            is_url = resume_path_val.startswith("http://") or resume_path_val.startswith("https://")
            if is_url:
                if "/uploads/" in resume_path_val:
                    # Local URL format, extract relative path after '/uploads/'
                    relative_path = resume_path_val.split("/uploads/")[-1]
                    is_url = False # Process as local file
                else:
                    # True cloud URL (S3, Supabase), fetch via HTTP
                    try:
                        import httpx
                        resp = httpx.get(resume_path_val)
                        if resp.status_code == 200:
                            content = resp.content
                            is_pdf = resume_path_val.lower().endswith(".pdf")
                    except Exception as e:
                        print(f"[Parser] Failed to fetch remote resume: {e}")

            if not is_url:
                # Clean up relative path separators
                relative_path = relative_path.replace("uploads/", "").replace("uploads\\", "")
                
                from pathlib import Path
                from config import UPLOAD_DIR, PROJECT_ROOT, BACKEND_DIR
                search_dirs = [
                    UPLOAD_DIR,
                    BACKEND_DIR / "uploads",
                    Path("uploads")
                ]
                
                file_path = None
                for s_dir in search_dirs:
                    p1 = s_dir / relative_path
                    if p1.exists() and p1.is_file():
                        file_path = p1
                        break
                        
                    p2 = s_dir / "resumes" / relative_path
                    if p2.exists() and p2.is_file():
                        file_path = p2
                        break
                        
                    results = list(s_dir.glob(f"**/{filename_val}"))
                    if not results:
                        basename = os.path.basename(relative_path)
                        results = list(s_dir.glob(f"**/{basename}"))
                        
                    if results:
                        file_path = results[0]
                        break
                
                if file_path and file_path.exists():
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read()
                        is_pdf = file_path.suffix.lower() == ".pdf"
                    except Exception as e:
                        print(f"[Parser] Failed to read local resume: {e}")

            if content:
                try:
                    from resume_parser import read_pdf_bytes
                    if is_pdf:
                        raw_text = read_pdf_bytes(content)
                    else:
                        raw_text = content.decode("utf-8", errors="ignore")
                except Exception as e:
                    print(f"[Parser] Failed to decode file content: {e}")
                    print(f"Failed to read file: {e}")

    if not raw_text:
        raise HTTPException(status_code=422, detail="No resume text available for re-parsing. Please re-upload.")

    filename = c.get("filename", "resume.pdf")

    # ── Re-parse resume with LLM ──────────────────────────────────────────────
    profile = parse_resume_with_llm(raw_text, filename)

    # ── Load job description ──────────────────────────────────────────────────
    jd_profile = {}
    job_doc = None
    if c.get("job_id"):
        try:
            job_doc = await jobs_col.find_one({"_id": ObjectId(c["job_id"])})
        except Exception:
            pass
    if job_doc:
        job_required_skills = job_doc.get("required_skills") or job_doc.get("skills") or []
        job_preferred_skills = job_doc.get("preferred_skills") or []
        jd_text = job_doc.get("description") or job_doc.get("jd_text") or ""
        if jd_text and not job_required_skills:
            jd_profile = parse_jd_with_llm(jd_text)
        else:
            jd_profile = {
                "role_name": job_doc.get("title", ""),
                "required_skills": job_required_skills,
                "preferred_skills": job_preferred_skills,
                "minimum_experience": job_doc.get("experience_required") or 0.0,
                "certifications_required": job_doc.get("certifications_required") or [],
                "project_requirements": job_doc.get("project_requirements") or [],
                "domain_requirements": job_doc.get("domain_requirements") or [],
            }

    # ── Compute skill matches using matching.py functions ───────────────────
    from matching import (
        compute_skill_scores,
        calculate_experience_breakdown,
        compute_quality_score,
        compute_semantic_similarity
    )

    req_skills = jd_profile.get("required_skills", [])
    minimum_exp = float(jd_profile.get("minimum_experience", 0.0) or 0.0)

    # ── Load recruiter weights ───────────────────────────────────────────────
    from routes.settings import get_recruiter_weights
    weights = await get_recruiter_weights(current_user)

    # ── Skills score ──
    cand_skills_list = []
    if profile.get("technical_skills"):
        cand_skills_list.extend(profile.get("technical_skills", []))
    if profile.get("soft_skills"):
        cand_skills_list.extend(profile.get("soft_skills", []))
    if not cand_skills_list and profile.get("skills"):
        cand_skills_list.extend(profile.get("skills", []))
    cand_skills_list = list(set([s for s in cand_skills_list if s]))

    skill_score, exact, semantic_m, partial, missing = compute_skill_scores(
        req_skills, cand_skills_list
    )
    pref_skills = jd_profile.get("preferred_skills", [])
    bonus = [s for s in pref_skills if any(cs.lower() == s.lower() for cs in cand_skills_list)]
    skills_weight = skill_score * weights.get("skills", 0.40)

    # ── Experience score ──
    exp_breakdown = calculate_experience_breakdown(
        timeline=profile.get("employment_timeline", []),
        explicit_exp=float(profile.get("total_experience_years") or 0.0),
        required_skills=req_skills,
    )
    total_exp = exp_breakdown["total_experience"]
    relevant_exp = exp_breakdown["relevant_experience"]
    effective_exp = max(relevant_exp, total_exp)

    if minimum_exp <= 0:
        exp_score = round(min(100.0, 20.0 + effective_exp * 16.0), 2)
    else:
        if effective_exp >= minimum_exp:
            exp_score = 100.0
        else:
            ratio = effective_exp / minimum_exp
            exp_score = round(ratio * 100.0, 2)
    exp_weight = exp_score * weights.get("experience", 0.25)

    # ── Semantic score ──
    sem_score = compute_semantic_similarity(jd_text, raw_text)
    sem_weight = sem_score * weights.get("semantic", 0.15)

    # ── Projects score ──
    proj_reqs = jd_profile.get("project_requirements", [])
    cand_projs = profile.get("projects", [])
    if not proj_reqs:
        project_score = 70.0 if len(cand_projs) >= 2 else (
            50.0 if len(cand_projs) == 1 else 20.0)
    else:
        matched_p = [p for p in cand_projs if any(r.lower() in p.lower() for r in proj_reqs)]
        project_score = round((len(matched_p) / max(len(proj_reqs), 1)) * 100, 2)
    proj_weight = project_score * weights.get("projects", 0.10)

    # ── Certifications score ──
    cert_reqs = jd_profile.get("certifications_required", [])
    cand_certs = profile.get("certifications", [])
    if not cert_reqs:
        cert_score = 65.0 if cand_certs else 40.0
    else:
        matched_c = [c for c in cand_certs if any(r.lower() in c.lower() for r in cert_reqs)]
        cert_score = round((len(matched_c) / max(len(cert_reqs), 1)) * 100, 2)
    cert_weight = cert_score * weights.get("certifications", 0.05)

    # ── Quality score ──
    quality_score, quality_penalties = compute_quality_score(profile, raw_text)
    quality_weight = quality_score * weights.get("quality", 0.05)

    # ── Weighted sum ──
    raw_final = (
        skills_weight
        + exp_weight
        + sem_weight
        + proj_weight
        + cert_weight
        + quality_weight
    )


    # ── Apply global hard penalties ──
    global_penalties = []
    if req_skills:
        missing_ratio = len(missing) / len(req_skills)
        if missing_ratio >= 0.7:
            deduct = 20
            global_penalties.append(f">70% required skills missing -{deduct}pts")
            raw_final -= deduct
        elif missing_ratio >= 0.5:
            deduct = 12
            global_penalties.append(f">50% required skills missing -{deduct}pts")
            raw_final -= deduct
        elif missing_ratio >= 0.3 and skill_score < 50:
            deduct = 6
            global_penalties.append(f">30% required skills missing -{deduct}pts")
            raw_final -= deduct

    if minimum_exp > 0 and effective_exp < minimum_exp * 0.5:
        raw_final -= 10
        global_penalties.append(
            f"Experience severely below requirement ({effective_exp:.1f} vs {minimum_exp:.1f}yrs) -10pts")

    if len(raw_text) < 500:
        raw_final -= 10
        global_penalties.append("Severely incomplete resume (<500 chars) -10pts")

    conf = profile.get("confidence_score", 75.0) or 75.0
    if conf < 50:
        raw_final -= 8
        global_penalties.append(f"Low extraction confidence ({conf:.0f}) -8pts")

    final_score = round(max(0.0, min(100.0, raw_final)), 2)

    score_breakdown = {
        "skill_score":      round(skill_score, 2),
        "experience_score": round(exp_score, 2),
        "semantic_score":   round(sem_score, 2),
        "project_score":    round(project_score, 2),
        "cert_score":       round(cert_score, 2),
        "quality_score":    round(quality_score, 2),
        "final_score":      round(final_score, 2),
        "penalties":        global_penalties + quality_penalties,
    }

    # ── Generate AI intelligence ──────────────────────────────────────────────
    intelligence = generate_candidate_intelligence(profile, jd_profile, score_breakdown)
    ai_verdict   = intelligence.get("recommendation", "Hold")

    hiring_summary = {
        "narrative":               intelligence.get("executive_summary", ""),
        "strengths":               intelligence.get("strengths", []),
        "weaknesses":              intelligence.get("weaknesses", []),
        "risks":                   intelligence.get("risks", []),
        "opportunities":           intelligence.get("opportunities", []),
        "interview_focus_areas":   intelligence.get("interview_focus_areas", []),
        "hiring_red_flags":        intelligence.get("hiring_red_flags", []),
        "hiring_green_flags":      intelligence.get("hiring_green_flags", []),
        "culture_fit_indicators":  intelligence.get("culture_fit_indicators", []),
        "salary_range_fit":        intelligence.get("salary_range_fit", "Mid"),
        "onboarding_complexity":   intelligence.get("onboarding_complexity", "Medium"),
        "time_to_productivity":    intelligence.get("time_to_productivity", "1-2 weeks"),
        "recommendation":          ai_verdict,
        "recommendation_confidence": intelligence.get("recommendation_confidence", "Medium"),
        "confidence":              profile.get("extraction_reliability", "Medium"),
        "generated_at":            datetime.datetime.utcnow().isoformat(),
    }

    # ── Persist to MongoDB ────────────────────────────────────────────────────
    update_fields = {
        # LLM-extracted structured fields
        "candidate_name":         profile.get("candidate_name", c.get("name")),
        "name":                   profile.get("candidate_name", c.get("name")),
        "email":                  profile.get("email") or c.get("email", ""),
        "phone":                  profile.get("phone") or c.get("phone", ""),
        "location":               profile.get("location") or c.get("location", ""),
        "current_title":          profile.get("current_title", ""),
        "total_experience_years": total_exp,
        "technical_skills":       profile.get("technical_skills", []),
        "soft_skills":            profile.get("soft_skills", []),
        "certifications":         profile.get("certifications", []),
        "education":              [e.get("degree","") if isinstance(e,dict) else e for e in profile.get("education",[])],
        "education_structured":   profile.get("education", []),
        "projects":               [p.get("name","") if isinstance(p,dict) else p for p in profile.get("projects",[])],
        "projects_structured":    profile.get("projects", []),
        "employment_timeline":    profile.get("employment_timeline", []),
        "companies":              profile.get("companies", []),
        "job_titles":             profile.get("job_titles", []),
        "github_url":             profile.get("github_url", ""),
        "linkedin_url":           profile.get("linkedin_url", ""),
        "portfolio_url":          profile.get("portfolio_url", ""),
        "languages_spoken":       profile.get("languages_spoken", []),
        "awards_achievements":    profile.get("awards_achievements", []),
        "summary_or_objective":   profile.get("summary_or_objective", ""),
        "confidence_score":       profile.get("confidence_score", 70.0),
        "ambiguity_detection":    profile.get("ambiguity_detection", []),
        "extraction_reliability": profile.get("extraction_reliability", "Medium"),
        # Skill match results
        "exact_matches":          exact,
        "semantic_matches":       semantic_m,
        "partial_matches":        partial,
        "matched_skills":         sorted(list(set(exact) | set(semantic_m) | set(partial))),
        "missing_skills":         missing,
        "bonus_skills":           bonus,
        # Updated scores aligned with matching.py
        "skill_score":            skill_score,
        "skills_score":           skill_score,
        "experience_score":       exp_score,
        "experience_relevance":   exp_score,
        "resume_quality":         quality_score,
        "projects_score":         project_score,
        "certification_score":    cert_score,
        "certifications_score":   cert_score,
        "score":                  final_score,
        "ai_match_score":         final_score,
        "ai_verdict":             ai_verdict,
        "hiring_summary":         hiring_summary,
        "score_breakdown":        score_breakdown,
        # JD data stored for reference
        "jd_required_skills":     jd_profile.get("required_skills", []),
        "jd_preferred_skills":    jd_profile.get("preferred_skills", []),
        "jd_role_name":           jd_profile.get("role_name", ""),
        "reparsed_at":            datetime.datetime.utcnow().isoformat(),
    }

    await candidates_col.update_one({"_id": ObjectId(candidate_id)}, {"$set": update_fields})
    updated = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    return serialize(updated)


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
            c = await candidates_col.find_one({"_id": ObjectId(cid), "created_by": current_user["email"]})
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
    from services.llm_service import is_groq_available, llm_stream
    id_list = [i.strip() for i in ids.split(",") if i.strip()][:3]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 candidate IDs")

    candidates = []
    for cid in id_list:
        try:
            c = await candidates_col.find_one({"_id": ObjectId(cid), "created_by": current_user["email"]})
            if c: candidates.append(c)
        except Exception:
            continue

    if len(candidates) < 2:
        raise HTTPException(status_code=404, detail="Could not find enough candidates")

    job_id = candidates[0].get("job_id")
    job = None
    if job_id:
        try:
            job = await jobs_col.find_one({"_id": ObjectId(job_id)})
        except Exception:
            pass

    prompt = "You are an expert Enterprise AI Recruiter Copilot.\n"
    prompt += f"Compare {len(candidates)} candidates"
    if job:
        prompt += f" for the role of '{job.get('title', 'this role')}'.\n\n"
    else:
        prompt += ".\n\n"

    for c in candidates:
        analysis = c.get("ai_analysis", {})
        prompt += f"Candidate: {c.get('name', 'Unknown')}\n"
        prompt += f"AI Match Score: {c.get('score', 0):.0f}%\n"
        prompt += f"Experience: {c.get('experience_years', 0):.0f} years\n"
        prompt += f"Top Skills: {', '.join(c.get('skills', [])[:5])}\n"
        if analysis:
            prompt += f"Interview Communication: {analysis.get('communication', 'N/A')}\n"
            prompt += f"Behavioral Risk: {analysis.get('cheating_risk', 'Low')}\n"
        prompt += f"Missing Skills: {', '.join(c.get('missing_skills', [])[:3])}\n\n"

    prompt += (
        "Write a 2-3 sentence sharp, concise comparison naming each candidate explicitly. "
        "Highlight technical fit, communication, and behavioral risk. "
        "Conclude with a clear hiring recommendation. "
        "Professional tone only. No markdown headers."
    )

    if not is_groq_available():
        # Graceful template fallback when Groq is not configured
        names = [c.get("name", "Candidate") for c in candidates]
        scores = [c.get("score", 0) for c in candidates]
        best = names[scores.index(max(scores))]
        async def fallback_gen():
            yield (
                f"Based on AI match scores, {best} appears to be the strongest candidate "
                f"with the highest score ({max(scores):.0f}%). "
                "Review individual profiles for detailed strengths and missing skills. "
                "(GROQ_API_KEY not configured — add it to .env for AI-powered comparison.)"
            )
        return StreamingResponse(fallback_gen(), media_type="text/plain")

    async def generate():
        try:
            async for token in llm_stream(prompt, temperature=0.3):
                yield token
        except Exception as e:
            yield f"\n\n⚠️ AI Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/{candidate_id}")
async def get_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    c = await candidates_col.find_one({"_id": ObjectId(candidate_id), "created_by": current_user["email"]})
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
    
    # All valid statuses including interview sub-states
    valid = [
        "applied", "screening", "shortlisted",
        "interview_scheduled", "interview_live", "interview_completed",
        "interview_analyzing", "interview_analyzed", "interview_incomplete",
        "interview_missed", "offered", "hired", "rejected"
    ]
    # Map all accepted values to their canonical storage value
    legacy_map = {
        "pending": "applied",
        "applied": "applied",
        "screening": "screening",
        "shortlisted": "shortlisted",
        "interview_scheduled": "interview_scheduled",
        "interview_live": "interview_live",
        "interview_missed": "interview_missed",
        "interviewed": "interview_completed",
        "interview_completed": "interview_completed",
        "interview_analyzing": "interview_analyzing",
        "interview_analyzed": "interview_analyzed",
        "interview_incomplete": "interview_incomplete",
        "selected": "offered",
        "offered": "offered",
        "hired": "hired",
        "rejected": "rejected",
        "on_hold": "screening"
    }
    
    status_lower = update.status.lower().strip()
    stage = legacy_map.get(status_lower, status_lower if status_lower in valid else None)
    if not stage:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id), "created_by": current_user["email"]})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    activity = {
        "action": f"Moved to {stage}",
        "timestamp": datetime.utcnow().isoformat(),
        "author": current_user["name"]
    }
    
    result = await candidates_col.update_one(
        {"_id": ObjectId(candidate_id), "created_by": current_user["email"]},
        {"$set": {"pipeline_stage": stage, "status": stage, "updated_at": datetime.utcnow()},
         "$push": {"activity_history": activity}},
    )
    
    return {"message": f"Status updated to '{stage}'"}

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
    valid = ["applied", "screening", "shortlisted", "interview_scheduled", "interview_completed", "offered", "hired", "rejected"]
    legacy_map = {
        "pending": "applied",
        "applied": "applied",
        "screening": "screening",
        "shortlisted": "shortlisted",
        "interview_scheduled": "interview_scheduled",
        "interview_live": "interview_scheduled",
        "interview_missed": "interview_scheduled",
        "interviewed": "interview_completed",
        "interview_completed": "interview_completed",
        "selected": "offered",
        "offered": "offered",
        "hired": "hired",
        "rejected": "rejected",
        "on_hold": "screening"
    }
    
    status_lower = update.status.lower().strip()
    stage = legacy_map.get(status_lower)
    if not stage:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    object_ids = [ObjectId(cid) for cid in update.candidate_ids]
    
    activity = {
        "action": f"Bulk moved to {stage}",
        "timestamp": datetime.utcnow().isoformat(),
        "author": current_user["name"]
    }

    result = await candidates_col.update_many(
        {"_id": {"$in": object_ids}, "created_by": current_user["email"]},
        {"$set": {"pipeline_stage": stage, "status": stage, "updated_at": datetime.utcnow()},
         "$push": {"activity_history": activity}},
    )

    return {"message": f"Status updated to '{stage}' for {result.modified_count} candidates"}


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
        {"_id": ObjectId(candidate_id), "created_by": current_user["email"]},
        {"$push": {"notes": note_doc}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"message": "Note added"}

@router.delete("/{candidate_id}")
async def delete_candidate(candidate_id: str, current_user=Depends(get_current_user)):
    try:
        candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id), "created_by": current_user["email"]})
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
    if resume_path_val and not resume_path_val.startswith("http://") and not resume_path_val.startswith("https://"):
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

    # Resolve the file path: support local URLs, relative paths, and cloud URLs
    filename = candidate.get("filename") or os.path.basename(resume_path_val)
    relative_path = resume_path_val

    is_url = resume_path_val.startswith("http://") or resume_path_val.startswith("https://")
    if is_url:
        if "/uploads/" in resume_path_val:
            # Local URL format, extract relative path after '/uploads/'
            relative_path = resume_path_val.split("/uploads/")[-1]
        else:
            # True cloud URL (S3, Supabase), redirect directly
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=resume_path_val)

    # Clean up relative path separators
    relative_path = relative_path.replace("uploads/", "").replace("uploads\\", "")
    
    from pathlib import Path
    from config import PROJECT_ROOT, BACKEND_DIR
    search_dirs = [
        UPLOAD_DIR,
        BACKEND_DIR / "uploads",
        Path("uploads")
    ]
    
    file_path = None
    for s_dir in search_dirs:
        # Check direct path
        p1 = s_dir / relative_path
        if p1.exists() and p1.is_file():
            file_path = p1
            break
            
        # Check direct subfolder path (like s_dir / "resumes" / relative_path)
        p2 = s_dir / "resumes" / relative_path
        if p2.exists() and p2.is_file():
            file_path = p2
            break
            
        # Check fuzzy filename match within s_dir
        results = list(s_dir.glob(f"**/{filename}"))
        if not results:
            basename = os.path.basename(relative_path)
            results = list(s_dir.glob(f"**/{basename}"))
            
        if results:
            file_path = results[0]
            break

    if not file_path or not file_path.exists():
        logger.error(f"Resume file NOT FOUND. ID: {candidate_id}, Stored Path: {resume_path_val}")
        raise HTTPException(
            status_code=404,
            detail=f"Original resume PDF file not found on storage. (Path: {resume_path_val})"
        )

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
