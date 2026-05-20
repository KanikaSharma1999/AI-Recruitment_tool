import asyncio
import httpx
from database import init_db, users_col, candidates_col
from auth import create_access_token

async def run_candidate_delete():
    await init_db()
    
    # 1. Get an existing user
    user = await users_col.find_one()
    if not user:
        print("No user found!")
        return
    
    email = user["email"]
    role = user.get("role", "admin")
    token = create_access_token({"sub": email, "role": role})
    
    # 2. Find a candidate to delete (the one named "1777019358630" or any other candidate)
    candidate = await candidates_col.find_one()
    if not candidate:
        print("No candidates found in database!")
        return
        
    cand_id = str(candidate["_id"])
    print(f"Found candidate to delete: ID={cand_id}, Name='{candidate.get('name')}'")
    
    # 3. Make HTTP DELETE request
    headers = {"Authorization": f"Bearer {token}"}
    url = f"http://localhost:8000/candidates/{cand_id}"
    
    print(f"Sending HTTP DELETE to: {url}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(run_candidate_delete())
