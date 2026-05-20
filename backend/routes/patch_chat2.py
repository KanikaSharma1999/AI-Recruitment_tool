"""Patch: add new response handler functions to chat.py before COHERE section"""
import os, re

path = os.path.join(os.path.dirname(__file__), "chat.py")
content = open(path, "r", encoding="utf-8").read()

NEW_HANDLERS = '''
# ═══════════════════════════════════════════════════════════════════════════════
#  NEW RECRUITER INTELLIGENCE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_names_from_query(query: str):
    """Extract candidate names from a comparison query like 'Compare Alice and Bob'."""
    # Pattern: compare X and Y / X vs Y
    m = re.search(r"compare\\s+([\\w\\s]+?)\\s+(?:and|vs|versus)\\s+([\\w\\s]+?)(?:\\s+for|\\s*$)", query, re.IGNORECASE)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    m = re.search(r"([\\w]+)\\s+(?:vs|versus)\\s+([\\w]+)", query, re.IGNORECASE)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return []


async def _response_candidate_comparison(query: str, memory: list) -> str:
    """Handle: 'Compare Alice and Bob' — side-by-side summary from DB."""
    names = _extract_names_from_query(query)

    candidates = []
    for name in names:
        c = await candidates_col.find_one({"name": {"$regex": name, "$options": "i"}})
        if not c:
            # Try first word
            first = name.split()[0] if name.split() else name
            c = await candidates_col.find_one({"name": {"$regex": first, "$options": "i"}})
        if c:
            candidates.append(c)

    if len(candidates) < 2:
        if not names:
            return (
                "Please specify which candidates to compare.\\n"
                "Example: **'Compare Alice and Ravi'** or **'Alice vs Bob for Backend role'**"
            )
        found = [c["name"] for c in candidates]
        missing = [n for n in names if not any(n.lower() in c["name"].lower() for c in candidates)]
        return f"Could not find candidate(s): **{', '.join(missing)}**. Please check the name spelling."

    lines = [f"⚖️ **Candidate Comparison**\\n"]
    dims = [
        ("AI Match Score", "score"),
        ("Technical Fit", "technical_fit"),
        ("Experience", "experience_relevance"),
        ("Resume Quality", "resume_quality"),
    ]
    for c in candidates:
        rec = c.get("hiring_summary", {}).get("recommendation", "Not ranked")
        skills = ", ".join(c.get("skills", [])[:4]) or "None listed"
        lines.append(
            f"\\n**{c['name']}**\\n"
            f"• AI Score: **{c.get('score', 0):.0f}%** | Recommendation: **{rec}**\\n"
            f"• Experience: {c.get('experience_years', 0):.0f} yrs | "
            f"Technical Fit: {c.get('technical_fit', 0):.0f}%\\n"
            f"• Top Skills: {skills}\\n"
            f"• Missing Skills: {', '.join(c.get('missing_skills', [])[:3]) or 'None'}\\n"
            f"• Status: {c.get('status', 'pending').replace('_', ' ').title()}"
        )

    # Winner determination
    best = max(candidates, key=lambda x: x.get("score", 0))
    lines.append(f"\\n🏆 **Winner: {best['name']}** — {best.get('score', 0):.0f}% overall match")
    return "\\n".join(lines)


async def _response_hiring_recommendation(query: str, memory: list) -> str:
    """Handle: 'Who should I hire for Backend Developer?' — top candidates with reasoning."""
    job_title = _extract_job_title(query)
    limit = _extract_limit(query) or 3

    db_query = {}
    job_label = "this role"
    if job_title:
        job = await jobs_col.find_one({"title": {"$regex": job_title, "$options": "i"}})
        if job:
            db_query["job_id"] = str(job["_id"])
            job_label = job["title"]

    results = []
    async for c in candidates_col.find(db_query).sort("score", -1).limit(limit):
        summary = c.get("hiring_summary", {})
        rec = summary.get("recommendation", "Not evaluated")
        conf = summary.get("confidence", "")
        strengths = summary.get("strengths", [])
        narrative = summary.get("narrative", "")
        top_strength = strengths[0] if strengths else "Relevant experience"
        missing = ", ".join(c.get("missing_skills", [])[:2]) or "None"

        results.append(
            f"**{len(results)+1}. {c['name']}** — {c.get('score', 0):.0f}% match\\n"
            f"   Recommendation: **{rec}** ({conf} confidence)\\n"
            f"   Strength: {top_strength}\\n"
            f"   Missing: {missing}"
        )

    if not results:
        return f"No ranked candidates found for {job_label}. Please run ranking first."

    return (
        f"🎯 **Hiring Recommendation for {job_label}:**\\n\\n"
        + "\\n\\n".join(results)
        + f"\\n\\n_Rankings based on AI match scores. Run ranking to refresh._"
    )


async def _response_why_low_rank(query: str, memory: list) -> str:
    """Handle: 'Why did Ravi rank low?' — evidence-based low-score explanation."""
    # Extract candidate name
    m = re.search(r"why.*?(?:did|does|is)?\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)\\s+", query)
    search_name = m.group(1).strip() if m else None

    if not search_name and memory:
        for turn in reversed(memory):
            if "last_candidates" in turn:
                search_name = turn["last_candidates"][0] if turn["last_candidates"] else None
                break

    if not search_name:
        return "Please specify which candidate you're asking about. Example: **'Why did Ravi rank low?'**"

    c = await candidates_col.find_one({"name": {"$regex": search_name, "$options": "i"}})
    if not c:
        first_word = search_name.split()[0]
        c = await candidates_col.find_one({"name": {"$regex": first_word, "$options": "i"}})
    if not c:
        return f"Could not find candidate matching **'{search_name}'**."

    name = c.get("name", search_name)
    score = c.get("score", 0)
    missing = c.get("missing_skills", [])
    risk_flags = c.get("risk_flags", [])
    exp_years = c.get("experience_years", 0)
    tech_fit = c.get("technical_fit", 0)
    exp_rel = c.get("experience_relevance", 0)
    summary = c.get("hiring_summary", {})
    weaknesses = summary.get("weaknesses", [])

    reasons = []
    if missing:
        reasons.append(f"• **Missing {len(missing)} required skills**: {', '.join(missing[:4])}")
    if tech_fit < 50:
        reasons.append(f"• **Low technical fit** ({tech_fit:.0f}%) — resume content doesn't closely match the JD")
    if exp_rel < 50:
        reasons.append(f"• **Experience gap** — only {exp_years:.0f} year(s) detected")
    for w in weaknesses[:2]:
        reasons.append(f"• {w}")
    for rf in risk_flags[:2]:
        reasons.append(f"• ⚠ {rf}")
    if not reasons:
        reasons.append("• Scores are relatively balanced but below shortlisting threshold")

    verdict = summary.get("recommendation", "Hold")
    return (
        f"📉 **Why {name} ranked low ({score:.0f}% match):**\\n\\n"
        + "\\n".join(reasons)
        + f"\\n\\n**AI Recommendation:** {verdict}\\n"
        "_To improve ranking, candidate needs to upskill in the missing areas._"
    )


async def _response_interview_performance(query: str, memory: list) -> str:
    """Handle: 'How did Ravi perform in the interview?' — AI analysis summary."""
    m = re.search(r"(?:how|what).{0,10}(?:did|was|is)?\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?)\\s+", query)
    search_name = m.group(1).strip() if m else None

    if not search_name and memory:
        for turn in reversed(memory):
            if "last_candidates" in turn:
                search_name = turn["last_candidates"][0] if turn["last_candidates"] else None
                break

    if not search_name:
        return "Please specify the candidate name. Example: **'How did Ravi perform in the interview?'**"

    c = await candidates_col.find_one({"name": {"$regex": search_name, "$options": "i"}})
    if not c:
        first = search_name.split()[0]
        c = await candidates_col.find_one({"name": {"$regex": first, "$options": "i"}})
    if not c:
        return f"Candidate **'{search_name}'** not found."

    name = c.get("name", search_name)
    analysis = c.get("ai_analysis")
    if not analysis:
        status = c.get("status", "pending")
        if status == "interview_scheduled":
            return f"**{name}**'s interview is scheduled but hasn't taken place yet. Analysis will be generated after the session."
        return f"No interview analysis available for **{name}**. The interview may not have been completed yet."

    comm = analysis.get("communication", "N/A")
    conf = analysis.get("confidence", "N/A")
    risk = analysis.get("cheating_risk", "N/A")
    rec = analysis.get("recommendation", "Pending")
    reasoning = analysis.get("reasoning", "")
    metrics = analysis.get("metrics", {})

    return (
        f"🎥 **Interview Performance: {name}**\\n\\n"
        f"• **Communication:** {comm} ({metrics.get('comm_score', 'N/A')}% speaking ratio)\\n"
        f"• **Confidence:** {conf} ({metrics.get('eye_contact', 'N/A')}% eye contact)\\n"
        f"• **Cheating Risk:** {risk}\\n"
        f"• **AI Recommendation:** {rec}\\n"
        + (f"\\n_{reasoning}_" if reasoning else "")
    )


async def _response_generate_questions(query: str, memory: list) -> str:
    """Handle: 'Generate interview questions for Backend Developer' — call Q generator."""
    job_title = _extract_job_title(query)

    job = None
    if job_title:
        job = await jobs_col.find_one({"title": {"$regex": job_title, "$options": "i"}})

    if not job:
        # List available jobs to help user
        job_list = []
        async for j in jobs_col.find().limit(5):
            job_list.append(f"• **{j['title']}**")
        if job_list:
            return (
                f"I need a job title to generate questions.\\n"
                f"Available roles:\\n" + "\\n".join(job_list) +
                "\\n\\nTry: **'Generate interview questions for {role name}'**"
            )
        return "No jobs found. Please create a job first, then ask for interview questions."

    skills = job.get("required_skills", [])
    job_label = job.get("title", "this role")

    # Template-based questions (fast, no API needed)
    questions = []
    for skill in skills[:4]:
        questions.append(f"• **Technical:** Walk me through your experience with {skill} and a complex problem you solved with it.")
    questions += [
        f"• **Behavioral:** Tell me about a time you delivered a difficult project under pressure.",
        f"• **Behavioral:** Describe a situation where you disagreed with a colleague. How did you resolve it?",
        f"• **Situational:** How would you handle a critical production bug discovered 30 minutes before a release?",
        f"• **Culture Fit:** What does your ideal working environment look like?",
        f"• **Motivation:** Why are you interested in this {job_label} role specifically?",
    ]

    return (
        f"📝 **Interview Questions for {job_label}:**\\n\\n"
        + "\\n".join(questions[:10])
        + "\\n\\n_Tip: Visit the Candidate Profile page to generate personalized questions for a specific candidate._"
    )

'''

# Insert before the COHERE section
marker = "# ═══════════════════════════════════════════════════════════════════════════════\n#  COHERE ENHANCED RESPONSE"
if marker not in content:
    # Try alternative
    marker = "async def _enhance_with_cohere"

if marker not in content:
    print("ERROR: insertion marker not found")
else:
    result = content.replace(marker, NEW_HANDLERS + "\n\n" + marker, 1)
    open(path, "w", encoding="utf-8").write(result)
    print("OK: new handler functions inserted")
