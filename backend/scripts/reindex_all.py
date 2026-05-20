import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent dir to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import jobs_col, candidates_col, init_db
from services.vector_store import init_vector_store, bulk_index_resumes, bulk_index_jobs

async def reindex_all():
    print("Starting full re-indexing...")
    
    # 1. Init
    await init_db()
    await init_vector_store()
    
    # 2. Re-index Jobs
    print("Indexing Jobs...")
    jobs = []
    async for j in jobs_col.find():
        jobs.append({
            "id": str(j["_id"]),
            "title": j.get("title", ""),
            "description": j.get("description", "")
        })
    
    if jobs:
        await bulk_index_jobs(jobs)
        print(f"Indexed {len(jobs)} jobs.")
    else:
        print("No jobs to index.")
        
    # 3. Re-index Resumes
    print("Indexing Resumes...")
    candidates = []
    async for c in candidates_col.find():
        candidates.append({
            "id": str(c["_id"]),
            "name": c.get("name", "Unknown"),
            "raw_text": c.get("raw_text", "")
        })
        
    if candidates:
        await bulk_index_resumes(candidates)
        print(f"Indexed {len(candidates)} resumes.")
    else:
        print("No resumes to index.")
        
    print("Re-indexing complete!")

if __name__ == "__main__":
    asyncio.run(reindex_all())
