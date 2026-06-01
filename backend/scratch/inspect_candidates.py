import asyncio
from database import init_db, candidates_col, jobs_col

async def inspect():
    await init_db()
    c = await candidates_col.find_one({"name": "Rumena Bose"})
    if not c:
        c = await candidates_col.find_one()
    if c:
        print("Candidate Name:", c.get("name"))
        print("Score:", c.get("score"))
        print("AI Match Score:", c.get("ai_match_score"))
        print("AI Verdict:", c.get("ai_verdict"))
        print("Skills:", c.get("skills"))
        print("Matched Skills:", c.get("matched_skills"))
        print("Missing Skills:", c.get("missing_skills"))
        print("Score Breakdown:", c.get("score_breakdown"))
        print("Hiring Summary:", c.get("hiring_summary"))
    else:
        print("No candidates found")

    j = await jobs_col.find_one()
    if j:
        print("\nJob Title:", j.get("title"))
        print("Job Description:", j.get("description")[:300] + "...")
        print("Required Skills:", j.get("required_skills"))
        print("Minimum Experience:", j.get("minimum_experience"))

if __name__ == "__main__":
    asyncio.run(inspect())
