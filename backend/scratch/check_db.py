import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from database import init_db, jobs_col, candidates_col

async def run():
    success = await init_db()
    if not success:
        print("DB connect failed")
        return

    jobs = await jobs_col.find({}).to_list(None)
    job_map = {str(j["_id"]): j.get("title") for j in jobs}
    print(f"Jobs in DB: {len(jobs)}")
    for j in jobs:
        print(f"  Job ID: {j['_id']} | Title: {j.get('title')} | Skills: {j.get('description', '')[:50]}...")

    candidates = await candidates_col.find({}).to_list(None)
    print(f"Candidates in DB: {len(candidates)}")
    for c in candidates[:20]:
        job_id = str(c.get("job_id", ""))
        job_title = job_map.get(job_id, "Unknown")
        print(f"Candidate: {c.get('name')} | Job: {job_title} | Score: {c.get('score')} | Match Score: {c.get('ai_match_score')} | Verdict: {c.get('ai_verdict')} | Has Breakdown: {c.get('score_breakdown') is not None}")

if __name__ == "__main__":
    asyncio.run(run())
