import asyncio
from database import init_db, jobs_col, candidates_col

async def list_db():
    await init_db()
    
    print("--- JOBS ---")
    jobs = []
    async for j in jobs_col.find():
        jobs.append(j)
        print(f"ID: {str(j['_id'])}, Title: {j.get('title')}, Company: {j.get('company')}")
        
    print("\n--- CANDIDATES ---")
    async for c in candidates_col.find().limit(10):
        print(f"ID: {str(c['_id'])}, Name: {c.get('name')}, Job ID: {c.get('job_id')}, Status: {c.get('status')}")

if __name__ == "__main__":
    asyncio.run(list_db())
