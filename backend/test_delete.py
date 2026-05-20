import asyncio
import os
from database import init_db, jobs_col, candidates_col, db_manager

async def test_delete():
    print("Initializing Database connection...")
    success = await init_db()
    if not success:
        print("Database connection failed!")
        return

    print("Creating dummy job...")
    dummy_job = {
        "title": "Test Deletion Job",
        "company": "Test Company",
        "description": "Dummy description",
        "location": "Remote",
        "required_experience_years": 1,
        "created_at": None,
        "created_by": "test@example.com"
    }
    
    job_result = await jobs_col.insert_one(dummy_job)
    job_id = str(job_result.inserted_id)
    print(f"Created Job ID: {job_id}")

    print("Creating dummy candidate...")
    dummy_candidate = {
        "name": "Test Delete Candidate",
        "email": "test_del@example.com",
        "job_id": job_id,
        "status": "pending",
        "score": 0.0
    }
    cand_result = await candidates_col.insert_one(dummy_candidate)
    cand_id = str(cand_result.inserted_id)
    print(f"Created Candidate ID: {cand_id}")

    print("Verifying candidate exists in database...")
    cand_check = await candidates_col.find_one({"_id": cand_result.inserted_id})
    if cand_check:
        print("Candidate exists: YES")
    else:
        print("Candidate exists: NO")

    print("Deleting candidate...")
    del_cand_result = await candidates_col.delete_one({"_id": cand_result.inserted_id})
    print(f"Deleted Candidate count: {del_cand_result.deleted_count}")

    print("Deleting job (and testing cascade candidates deletion)...")
    # Delete cascade candidates
    del_cascade_candidates = await candidates_col.delete_many({"job_id": job_id})
    print(f"Cascade deleted candidates: {del_cascade_candidates.deleted_count}")
    
    del_job_result = await jobs_col.delete_one({"_id": job_result.inserted_id})
    print(f"Deleted Job count: {del_job_result.deleted_count}")

if __name__ == "__main__":
    asyncio.run(test_delete())
