import asyncio
import os
import sys
import time
from bson import ObjectId
from dotenv import load_dotenv

# Add backend to sys.path so we can import modules
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.append(backend_path)

env_path = os.path.join(backend_path, ".env")
load_dotenv(dotenv_path=env_path, override=True)

from database import jobs_col, candidates_col, db_manager
from resume_parser import (
    extract_candidate_details, extract_skills, extract_experience_years,
    extract_education, extract_location, extract_certifications, extract_projects,
    BANNED_WORDS
)
from matching import rank_all_resumes
from main import get_resume_feedback, generate_hiring_summary

def reparse_candidate_text(raw_text: str, filename: str) -> dict:
    details        = extract_candidate_details(raw_text, filename)
    skills         = extract_skills(raw_text)
    experience_yrs = extract_experience_years(raw_text)
    education      = extract_education(raw_text)
    location       = extract_location(raw_text)
    certifications = extract_certifications(raw_text)
    projects       = extract_projects(raw_text)

    # Try LLM parse first
    try:
        from services.llm_parser import parse_resume_with_llm
        parsed_llm = parse_resume_with_llm(raw_text, filename)
    except Exception as e:
        print(f"[Parser] LLM resume parse failed: {e}")
        parsed_llm = {}

    return {
        "name":             parsed_llm.get("candidate_name") or details["name"],
        "email":            parsed_llm.get("email") or details["email"],
        "phone":            parsed_llm.get("phone") or details["phone"],
        "skills":           parsed_llm.get("technical_skills") or skills,
        "experience_years": parsed_llm.get("total_experience_years") or experience_yrs,
        "education":        parsed_llm.get("education") or education,
        "location":         location,
        "certifications":   parsed_llm.get("certifications") or certifications,
        "projects":         parsed_llm.get("projects") or projects,
        "raw_text":         raw_text,

        # Structured candidate fields
        "candidate_name":   parsed_llm.get("candidate_name") or details["name"],
        "total_experience_years": parsed_llm.get("total_experience_years") or experience_yrs,
        "companies":        parsed_llm.get("companies") or [],
        "job_titles":       parsed_llm.get("job_titles") or [],
        "technical_skills": parsed_llm.get("technical_skills") or skills,
        "soft_skills":      parsed_llm.get("soft_skills") or [],
        "leadership_experience": parsed_llm.get("leadership_experience") or False,
        "domain_experience": parsed_llm.get("domain_experience") or [],
        "communication_indicators": parsed_llm.get("communication_indicators") or [],
        "employment_timeline": parsed_llm.get("employment_timeline") or [],
        "tools":            parsed_llm.get("tools") or [],
    }

async def reparse_and_rerank_all():
    print("=== STARTING CANDIDATE RE-PARSING AND RE-RANKING ===")
    
    # Initialize DB connection
    connected = await db_manager.connect()
    if not connected:
        print("Failed to connect to MongoDB Atlas cluster.")
        return
        
    # 1. Fetch all candidates
    candidates = []
    async for c in candidates_col.find():
        candidates.append(c)
        
    print(f"Found {len(candidates)} candidates in database.")
    
    # 2. Re-parse each candidate's raw_text
    for i, c in enumerate(candidates):
        cid = c["_id"]
        filename = c.get("filename", "resume.pdf")
        raw_text = c.get("raw_text", "")
        
        current_name = c.get("name", "")
        timeline = c.get("employment_timeline", [])
        
        # Check if timeline is empty or fallback dummy
        is_fallback_timeline = False
        if not timeline:
            is_fallback_timeline = True
        elif len(timeline) == 1 and timeline[0].get("company") == "Previous Employment":
            is_fallback_timeline = True
            
        # Check if current name contains banned headers / junk words
        name_words = [w.lower() for w in current_name.split()]
        has_banned_words = any(w in BANNED_WORDS for w in name_words)
        
        is_bad_name = (
            not current_name 
            or current_name in ("John Doe", "Candidate Profile", "Unknown") 
            or current_name.endswith(".pdf") 
            or has_banned_words
        )
        
        # We ONLY skip if they have a valid name AND a fully extracted timeline
        if not is_bad_name and not is_fallback_timeline:
            print(f"  Skipping parsing: already successfully parsed as {current_name}")
            continue
            
        if not raw_text or not raw_text.strip():
            print(f"Skipping {filename}: raw_text is empty.")
            continue
            
        try:
            print(f"  Reparsing candidate {current_name} (ID: {cid})...")
            # Re-parse text directly (no pdf decoding)
            parsed = reparse_candidate_text(raw_text, filename)
            
            # Prepare update document with correct normalization
            education_raw = parsed.get("education", [])
            education_strings = [e.get("degree", "") if isinstance(e, dict) else e for e in education_raw]
            education_structured = education_raw if (education_raw and isinstance(education_raw[0], dict)) else [{"degree": e, "institution": "", "year": "", "field": ""} for e in education_raw]

            projects_raw = parsed.get("projects", [])
            projects_strings = [p.get("name", "") if isinstance(p, dict) else p for p in projects_raw]
            projects_structured = projects_raw if (projects_raw and isinstance(projects_raw[0], dict)) else [{"name": p, "description": "", "technologies": []} for p in projects_raw]

            update_fields = {
                "name": parsed["name"],
                "email": parsed["email"],
                "phone": parsed["phone"],
                "skills": parsed["skills"],
                "experience_years": parsed["experience_years"],
                "education": education_strings,
                "education_structured": education_structured,
                "location": parsed["location"],
                "certifications": parsed.get("certifications", []),
                "projects": projects_strings,
                "projects_structured": projects_structured,
                "candidate_name": parsed["candidate_name"],
                "total_experience_years": parsed["total_experience_years"],
                "companies": parsed.get("companies", []),
                "job_titles": parsed.get("job_titles", []),
                "technical_skills": parsed.get("technical_skills", []),
                "soft_skills": parsed.get("soft_skills", []),
                "leadership_experience": parsed.get("leadership_experience", False),
                "domain_experience": parsed.get("domain_experience", []),
                "communication_indicators": parsed.get("communication_indicators", []),
                "employment_timeline": parsed.get("employment_timeline", []),
                "tools": parsed.get("tools", []),
            }
            
            # Perform update
            await candidates_col.update_one({"_id": cid}, {"$set": update_fields})
            print(f"  SUCCESS: Updated {parsed['name']} (Email: {parsed['email']}, Exp: {parsed['experience_years']} yrs)")
            
            # Wait 6.0s to prevent Groq RPM rate limits
            time.sleep(6.0)
            
        except Exception as e:
            print(f"  ERROR parsing {filename}: {e}")

    # 3. Re-rank candidates for each job
    print("\n=== STARTING RE-RANKING ===")
    
    # Disable LLM client during ranking to prevent rate limit lags and reuse parsed DB fields
    import services.llm_parser
    services.llm_parser._groq_rate_limited_until = time.time() + 999999
    
    jobs = []
    async for j in jobs_col.find():
        jobs.append(j)
        
    print(f"Found {len(jobs)} jobs in database.")
    
    for job in jobs:
        jid = str(job["_id"])
        job_title = job.get("title", "Unknown Job")
        jd_text = job.get("description", "")
        
        print(f"\nRe-ranking candidates for job: {job_title} (ID: {jid})...")
        
        job_candidates = []
        async for c in candidates_col.find({"job_id": jid}):
            job_candidates.append(c)
            
        if not job_candidates:
            print(f"  No candidates found for this job.")
            continue
            
        print(f"  Ranking {len(job_candidates)} candidates...")
        
        try:
            # Refresh database records so ranking receives newly updated candidate profiles
            refreshed_candidates = []
            async for c in candidates_col.find({"job_id": jid}):
                refreshed_candidates.append(c)

            ranked = await rank_all_resumes(jd_text, refreshed_candidates, job=job)
            for item in ranked:
                cid = item["_id"]
                feedback = get_resume_feedback(item.get("raw_text", ""), jd_text)
                
                # Generate hiring summary
                hiring_sum = item.get("hiring_summary", {})
                if not hiring_sum or not hiring_sum.get("narrative"):
                    try:
                        hiring_sum = await generate_hiring_summary(
                            candidate=item,
                            job=job,
                            match_explanation=item.get("match_explanation", {}),
                        )
                    except Exception as hs_err:
                        print(f"  Failed hiring summary for {item.get('name')}: {hs_err}")
                
                ai_verdict = item.get("ai_verdict")
                if not ai_verdict:
                    ai_verdict = hiring_sum.get("recommendation", "Hold") if hiring_sum else "Hold"
                    
                update_fields = {
                    "ai_match_score": item.get("ai_match_score"),
                    "ai_verdict": ai_verdict,
                    "score": item.get("score"),
                    "semantic_score": item.get("semantic_score"),
                    "skill_score": item.get("skill_score"),
                    "skills_score": item.get("skills_score"),
                    "experience_score": item.get("experience_score"),
                    "projects_score": item.get("projects_score"),
                    "certification_score": item.get("certification_score"),
                    "certifications_score": item.get("certifications_score"),
                    "resume_quality": item.get("resume_quality"),
                    "technical_fit": item.get("technical_fit"),
                    "experience_relevance": item.get("experience_relevance"),
                    "matched_skills": item.get("matched_skills"),
                    "missing_skills": item.get("missing_skills"),
                    "exact_matches": item.get("exact_matches"),
                    "semantic_matches": item.get("semantic_matches"),
                    "partial_matches": item.get("partial_matches"),
                    "bonus_skills": item.get("bonus_skills"),
                    "match_explanation": item.get("match_explanation"),
                    "score_breakdown": item.get("score_breakdown"),
                    "confidence_score": item.get("confidence_score"),
                    "ambiguity_detection": item.get("ambiguity_detection"),
                    "extraction_reliability": item.get("extraction_reliability"),
                    "leadership_match": item.get("leadership_match"),
                    "communication_match": item.get("communication_match"),
                    "recruiter_explanation": item.get("recruiter_explanation"),
                    "feedback": feedback,
                    "hiring_summary": hiring_sum,
                    "last_ranked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ranked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                
                await candidates_col.update_one({"_id": cid}, {"$set": update_fields})
                print(f"  SUCCESS: Updated ranking for candidate {item.get('name')} - Score: {item.get('score')}%")
                
        except Exception as e:
            print(f"  ERROR ranking candidates for job {job_title}: {e}")
            
    print("\n=== RE-PARSING AND RE-RANKING COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(reparse_and_rerank_all())
