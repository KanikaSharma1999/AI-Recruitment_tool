"""
Direct ranking updater — bypasses HTTP, runs the exact same logic as /admin/rerank-all.
Run from backend directory: python scratch/run_rerank_now.py
"""
import asyncio
import os
import sys
import traceback
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from database import init_db, jobs_col, candidates_col
from config import UPLOAD_DIR
from resume_parser import parse_resume_file
from services.llm_parser import parse_resume_with_llm
from matching import rank_all_resumes
from services.hiring_summary import generate_hiring_summary
from feedback import get_resume_feedback


async def run_rerank():
    print("=" * 60)
    print("[RUN_RERANK] Initializing database...")
    success = await init_db()
    if not success:
        print("[FATAL] Database connection failed. Aborting.")
        return

    print("[RUN_RERANK] Fetching jobs and candidates...")
    jobs = await jobs_col.find({}).to_list(None)
    job_map = {str(j["_id"]): j for j in jobs}
    candidates = await candidates_col.find({}).to_list(None)
    print(f"[RUN_RERANK] Jobs: {len(jobs)}, Candidates: {len(candidates)}")

    # Group candidates by job
    candidates_by_job = defaultdict(list)
    for c in candidates:
        job_id = c.get("job_id")
        if job_id:
            candidates_by_job[str(job_id)].append(c)

    no_job = [c for c in candidates if not c.get("job_id")]
    print(f"[RUN_RERANK] Candidates with job: {sum(len(v) for v in candidates_by_job.values())}")
    print(f"[RUN_RERANK] Candidates without job: {len(no_job)}")

    # Mark no-job candidates
    for c in no_job:
        await candidates_col.update_one(
            {"_id": c["_id"]},
            {"$set": {
                "ai_match_score": None,
                "ai_verdict": "Awaiting JD",
                "score": 0.0,
                "ranking_error": "Missing JD",
                "last_ranked_at": datetime.utcnow(),
            }}
        )

    reranked = 0
    errors = 0

    for job_id_str, cand_list in candidates_by_job.items():
        job = job_map.get(job_id_str)
        if not job or not job.get("description", "").strip():
            # No JD — mark all as Awaiting JD
            for cand in cand_list:
                await candidates_col.update_one(
                    {"_id": cand["_id"]},
                    {"$set": {
                        "ai_match_score": None,
                        "ai_verdict": "Awaiting JD",
                        "score": 0.0,
                        "ranking_error": "Missing JD",
                        "last_ranked_at": datetime.utcnow(),
                    }}
                )
            continue

        jd_text = job["description"]
        print(f"\n[RUN_RERANK] Job: '{job.get('title')}' | Candidates: {len(cand_list)}")

        # Prepare candidates — reload resumes from disk
        prepared = []
        for cand in cand_list:
            raw_text = ""
            resume_path_val = cand.get("resume_path")
            if resume_path_val:
                file_path = UPLOAD_DIR / resume_path_val
                if not file_path.exists():
                    stripped = resume_path_val.replace("uploads/", "").replace("uploads\\", "")
                    file_path = UPLOAD_DIR / stripped
                if file_path.exists():
                    try:
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                        parsed_file = parse_resume_file(file_bytes, cand.get("filename", "resume.pdf"))
                        raw_text = parsed_file.get("raw_text", "")
                    except Exception as e:
                        print(f"  [WARN] Could not reload {cand.get('name')}: {e}")
            if not raw_text:
                raw_text = cand.get("raw_text", "")

            prep = {**cand, "raw_text": raw_text}
            prep.pop("employment_timeline", None)  # force re-extraction
            prepared.append(prep)

        # Run ranking
        try:
            ranked = await rank_all_resumes(jd_text, prepared)
            print(f"  [RUN_RERANK] Ranked {len(ranked)} candidates.")
        except Exception as e:
            print(f"  [ERROR] rank_all_resumes failed: {e}")
            traceback.print_exc()
            errors += len(prepared)
            continue

        if not ranked:
            print("  [WARN] rank_all_resumes returned empty list.")
            continue

        # Save to MongoDB
        for item in ranked:
            cid = item["_id"]

            # Generate hiring summary
            hiring_sum = item.get("hiring_summary") or {}
            if not hiring_sum.get("narrative"):
                try:
                    hiring_sum = await generate_hiring_summary(
                        candidate=item,
                        job=job,
                        match_explanation=item.get("match_explanation", {}),
                    )
                except Exception as hse:
                    print(f"  [WARN] hiring_summary failed for {item.get('name')}: {hse}")
                    hiring_sum = {}

            ai_verdict = item.get("ai_verdict")
            if not ai_verdict:
                ai_verdict = hiring_sum.get("recommendation", "Hold") if hiring_sum else "Hold"

            feedback = get_resume_feedback(item.get("raw_text", ""), jd_text)

            update_fields = {
                "ai_match_score":        item.get("ai_match_score"),
                "ai_verdict":            ai_verdict,
                "score":                 item.get("score", 0.0),
                "semantic_score":        item.get("semantic_score"),
                "skills_score":          item.get("skills_score"),
                "skill_score":           item.get("skill_score", 0.0),
                "experience_score":      item.get("experience_score"),
                "projects_score":        item.get("projects_score"),
                "certification_score":   item.get("certification_score"),
                "certifications_score":  item.get("certifications_score", 0.0),
                "last_ranked_at":        datetime.utcnow(),
                "technical_fit":         item.get("technical_fit", 0),
                "experience_relevance":  item.get("experience_relevance", 0),
                "resume_quality":        item.get("resume_quality", 0),
                "risk_flags":            item.get("risk_flags", []),
                "matched_skills":        item.get("matched_skills", []),
                "missing_skills":        item.get("missing_skills", []),
                "exact_matches":         item.get("exact_matches", []),
                "semantic_matches":      item.get("semantic_matches", []),
                "partial_matches":       item.get("partial_matches", []),
                "bonus_skills":          item.get("bonus_skills", []),
                "match_explanation":     item.get("match_explanation", {}),
                "feedback":              feedback,
                "hiring_summary":        hiring_sum,
                "ranked_at":             datetime.utcnow(),
                "confidence_score":      item.get("confidence_score", 75.0),
                "ambiguity_detection":   item.get("ambiguity_detection", []),
                "extraction_reliability": item.get("extraction_reliability", "Medium"),
                "leadership_match":      item.get("leadership_match", "No"),
                "communication_match":   item.get("communication_match", "Baseline"),
                "recruiter_explanation": item.get("recruiter_explanation", ""),
                "ranking_error":         item.get("ranking_error"),
                "score_breakdown":       item.get("score_breakdown"),
            }

            res = await candidates_col.update_one(
                {"_id": cid},
                {"$set": update_fields}
            )

            if res.matched_count == 0:
                print(f"  [ERROR] Mongo update failed for {item.get('name')}")
                errors += 1
            else:
                score = item.get("ai_match_score", 0)
                verdict = ai_verdict
                print(f"  [OK] {item.get('name')}: {score}% | {verdict}")
                reranked += 1

    print("\n" + "=" * 60)
    print(f"[RUN_RERANK] DONE. Updated: {reranked}, Errors: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_rerank())
