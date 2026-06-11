import asyncio
import os
import sys
import time
from bson import ObjectId
from dotenv import load_dotenv

# Add backend to sys.path
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.append(backend_path)

env_path = os.path.join(backend_path, "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)

from database import db_manager, candidates_col, jobs_col
from services.llm_parser import generate_candidate_intelligence

async def main():
    print("=== STARTING UPDATE OF ALL CANDIDATE INTELLIGENCE REPORTS ===")
    connected = await db_manager.connect()
    if not connected:
        print("Failed to connect to MongoDB Atlas cluster.")
        return

    # Load all jobs into memory for quick lookup
    jobs = {}
    async for j in jobs_col.find():
        jobs[str(j["_id"])] = j

    print(f"Loaded {len(jobs)} jobs from database.")

    # Load all candidates
    candidates = []
    async for c in candidates_col.find():
        candidates.append(c)

    print(f"Loaded {len(candidates)} candidates from database.")

    updated_count = 0
    for idx, c in enumerate(candidates):
        cid = str(c["_id"])
        cname = c.get("name", "Unknown")
        job_id = c.get("job_id")

        if not job_id:
            print(f"[{idx+1}/{len(candidates)}] Candidate {cname} (ID: {cid}) has no job_id — skipping.")
            continue

        job = jobs.get(str(job_id))
        if not job:
            print(f"[{idx+1}/{len(candidates)}] Job not found for candidate {cname} (ID: {cid}) — skipping.")
            continue

        print(f"[{idx+1}/{len(candidates)}] Re-generating intelligence for {cname} (Job: {job.get('title')})...")

        # Re-construct profiles
        candidate_profile = {
            "candidate_name": c.get("candidate_name") or c.get("name"),
            "total_experience_years": c.get("total_experience_years") or c.get("experience_years", 0.0),
            "current_title": c.get("current_title", ""),
            "technical_skills": c.get("technical_skills") or c.get("skills", []),
            "soft_skills": c.get("soft_skills", []),
            "education": c.get("education_structured") or c.get("education", []),
            "certifications": c.get("certifications", []),
            "companies": c.get("companies", []),
            "job_titles": c.get("job_titles", []),
            "projects": c.get("projects_structured") or c.get("projects", []),
            "domain_experience": c.get("domain_experience", []),
            "leadership_experience": c.get("leadership_match") == "Yes",
        }

        jd_profile = {
            "role_name": job.get("title", ""),
            "required_skills": job.get("required_skills") or job.get("skills") or [],
            "preferred_skills": job.get("preferred_skills") or [],
            "minimum_experience": job.get("experience_required") or 0.0,
            "certifications_required": job.get("certifications_required") or [],
            "project_requirements": job.get("project_requirements") or [],
            "domain_requirements": job.get("domain_requirements") or [],
        }

        # Re-construct score breakdown
        score_breakdown = {
            "skill_score": c.get("skill_score") or c.get("skills_score") or 0.0,
            "experience_score": c.get("experience_score") or 0.0,
            "semantic_score": c.get("semantic_score") or 0.0,
            "project_score": c.get("projects_score") or 0.0,
            "cert_score": c.get("certification_score") or c.get("certifications_score") or 0.0,
            "quality_score": c.get("resume_quality") or 0.0,
            "final_score": c.get("score") or 0.0,
        }

        try:
            # Call the intelligence function
            intelligence = generate_candidate_intelligence(candidate_profile, jd_profile, score_breakdown)
            ai_verdict = intelligence.get("recommendation", "Hold")

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
                "confidence":              c.get("extraction_reliability", "Medium"),
                "generated_at":            intelligence.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

            # Update the candidate document in MongoDB
            await candidates_col.update_one(
                {"_id": ObjectId(cid)},
                {"$set": {
                    "hiring_summary": hiring_summary,
                    "ai_verdict": ai_verdict
                }}
            )
            updated_count += 1
            print(f"  -> SUCCESS: Updated {cname}. Strengths: {len(hiring_summary['strengths'])}, Weaknesses: {len(hiring_summary['weaknesses'])}, Risks: {len(hiring_summary['risks'])}")

            # Add a small delay to avoid hitting rate limit if Groq is available
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  -> ERROR updating candidate {cname}: {e}")

    print(f"\n=== COMPLETED: Updated {updated_count} candidates successfully ===")

if __name__ == "__main__":
    asyncio.run(main())
