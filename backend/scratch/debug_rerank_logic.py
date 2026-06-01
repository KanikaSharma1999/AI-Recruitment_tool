import asyncio
import os
import sys
import traceback
from datetime import datetime

# Add parent directories to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from database import init_db, jobs_col, candidates_col
from config import UPLOAD_DIR
from services.llm_parser import parse_resume_with_llm
from matching import rank_all_resumes
from services.hiring_summary import generate_hiring_summary
from feedback import get_resume_feedback
from collections import defaultdict

async def run_debug():
    print("Initializing Database...")
    success = await init_db()
    if not success:
        print("Database connection failed!")
        return

    print("Fetching jobs and candidates...")
    jobs = await jobs_col.find({}).to_list(None)
    job_map = {str(j["_id"]): j for j in jobs}
    candidates = await candidates_col.find({}).to_list(None)
    print(f"Jobs: {len(jobs)}, Candidates: {len(candidates)}")

    candidates_by_job = defaultdict(list)
    for c in candidates:
        job_id = c.get("job_id")
        if job_id:
            candidates_by_job[str(job_id)].append(c)

    no_job_candidates = [c for c in candidates if not c.get("job_id")]
    print(f"Candidates with job_id: {sum(len(v) for v in candidates_by_job.values())}")
    print(f"Candidates without job_id: {len(no_job_candidates)}")

    print("\nStarting reranking simulation...")
    for job_id_str, cand_list in candidates_by_job.items():
        job = job_map.get(job_id_str)
        if not job or not job.get("description") or not job.get("description").strip():
            print(f"Job {job_id_str} is missing JD or description. Updating {len(cand_list)} candidates to Awaiting JD...")
            continue

        jd_text = job["description"]
        prepared_candidates = []
        for cand in cand_list:
            print(f"  - Candidate: {cand.get('name')} | resume_path: {cand.get('resume_path')}")
            resume_path_val = cand.get("resume_path")
            raw_text = ""
            if resume_path_val:
                file_path = UPLOAD_DIR / resume_path_val
                if not file_path.exists():
                    stripped = resume_path_val.replace("uploads/", "").replace("uploads\\", "")
                    file_path = UPLOAD_DIR / stripped
                
                if file_path.exists():
                    try:
                        from resume_parser import parse_resume_file
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                        parsed_file = parse_resume_file(file_bytes, cand.get("filename", "resume.pdf"))
                        raw_text = parsed_file.get("raw_text", "")
                    except Exception as e:
                        print(f"Failed to reload resume file from disk for candidate: {cand.get('name')}: {e}")
                        raw_text = cand.get("raw_text", "")
                else:
                    raw_text = cand.get("raw_text", "")
            
            if not raw_text:
                raw_text = cand.get("raw_text", "")

            prepared_cand = {
                **cand,
                "raw_text": raw_text,
            }
            prepared_cand.pop("employment_timeline", None)
            prepared_candidates.append(prepared_cand)

        if not prepared_candidates:
            continue

        print(f"Running rank_all_resumes for job: {job.get('title')} with {len(prepared_candidates)} candidates...")
        try:
            ranked = await rank_all_resumes(jd_text, prepared_candidates)
            print(f"Ranked {len(ranked)} candidates successfully.")
            
            # Let's break after 1 job to see if the first one succeeds
            print("Rank_all_resumes output preview:")
            for item in ranked[:1]:
                print({
                    "name": item.get("name"),
                    "ai_match_score": item.get("ai_match_score"),
                    "ai_verdict": item.get("ai_verdict"),
                    "score": item.get("score")
                })
            break
        except Exception as e:
            print("CRITICAL ERROR IN rank_all_resumes:")
            traceback.print_exc()
            break

if __name__ == "__main__":
    asyncio.run(run_debug())
