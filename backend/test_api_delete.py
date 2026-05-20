import asyncio
import httpx
from database import init_db, users_col, jobs_col
from auth import create_access_token

async def run_api_delete():
    await init_db()
    
    # 1. Get an existing user
    user = await users_col.find_one()
    if not user:
        print("No user found in database! Please run frontend or signup first.")
        return
    
    email = user["email"]
    role = user.get("role", "admin")
    print(f"Using user email: {email} with role: {role}")
    
    # 2. Generate token
    token = create_access_token({"sub": email, "role": role})
    print(f"Generated JWT Token: {token[:20]}...")
    
    # 3. Find the "Delete Me Test" job ID
    job = await jobs_col.find_one({"title": "Delete Me Test"})
    if not job:
        print("Job 'Delete Me Test' not found in database! Let's check for any job to delete.")
        job = await jobs_col.find_one()
        if not job:
            print("No jobs found in database to delete!")
            return
            
    job_id = str(job["_id"])
    print(f"Found job to delete: ID={job_id}, Title='{job.get('title')}'")
    
    # 4. Make HTTP DELETE request to localhost:8000
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/jobs/{job_id}"
    
    print(f"Sending HTTP DELETE to: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(run_api_delete())
