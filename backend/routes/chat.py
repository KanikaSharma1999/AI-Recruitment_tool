"""
Intelligent HR Chatbot — routes/chat.py
Complete fallback: works without any external API.
Architecture: Intent Classification → DB Query → (Cohere | Template) Response
Conversation memory: last 10 turns stored per session.
"""

import re
import os
import logging
from collections import defaultdict
import traceback
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import get_current_user
from database import candidates_col, jobs_col

logger = logging.getLogger(__name__)

# --- DIAGNOSTICS FOR GROQ ---
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

api_key = os.environ.get("GROQ_API_KEY")
# print("\n[GROQ DEBUG]")
# if api_key:
#     print("KEY EXISTS: YES")
#     # first 10 chars
#     prefix = api_key[:10] if len(api_key) >= 10 else api_key
#     print(f"KEY PREFIX: {prefix}")
# else:
#     print("KEY EXISTS: NO")
#     print("KEY PREFIX: None")
# print("MODEL: llama-3.3-70b-versatile")
# print("BASE URL: https://api.groq.com/openai/v1\n")

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Session memory (in-memory, keyed by user email) ──────────────────────────
_session_memory: dict[str, list] = defaultdict(list)
MAX_MEMORY = 10


class ChatQuery(BaseModel):
    query: str
    session_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  INTENT CLASSIFIER  (pure rule-based, zero API cost)
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS = {
    "top_candidates": [
        r"top\s*\d*\s*candidate",
        r"best\s+candidate",
        r"highest\s+(score|match|rank)",
        r"rank(ed|ing)?\s+candidate",
    ],
    "candidate_search": [
        r"(show|find|list|get)\s+.*(candidate|developer|engineer|analyst|scientist)",
        r"candidate[s]?\s+with\s+",
        r"who\s+(know[s]?|has|have|can|use[s]?)",
        r"(python|java|react|node|sql|aws|docker|ml|ai|data)\s+(developer|engineer|expert|specialist)",
        r"skilled\s+in",
        r"experience\s+in",
    ],
    "candidate_profile": [
        r"(summarize|summary|profile|tell me about|describe)\s+.*candidate",
        r"what\s+(are|is)\s+.*(strength|skill|project|experience)",
        r"does\s+.*(know|have|use|work)",
        r"candidate.*cloud|cloud.*candidate",
    ],
    "experience_filter": [
        r"\d+\+?\s*years?\s*(of\s+)?experience",
        r"experience\s+(more|greater|above|over|at least|minimum)",
        r"senior|junior|mid.?level|fresher|entry.?level",
    ],
    "status_query": [
        r"shortlisted",
        r"rejected",
        r"pending",
        r"interview.scheduled",
        r"selected\s+candidate",
        r"how many.*(status|shortlist|reject)",
    ],
    "job_query": [
        r"(show|list|get|find)\s+.*job",
        r"job\s+(description|requirement|role|opening)",
        r"(skills?|requirement[s]?)\s+for\s+",
        r"available\s+(role|position|job)",
        r"jd\s+for",
    ],
    "ranking_query": [
        r"top\s+\d+\s+for\s+",
        r"best\s+.*for\s+",
        r"rank.*for\s+",
    ],
    "analytics": [
        r"(most\s+common|frequent)\s+skill",
        r"average\s+(experience|score|match)",
        r"skill\s+gap",
        r"missing\s+skill",
        r"how many\s+candidate",
        r"count\s+(of\s+)?candidate",
        r"analytics|statistics|stats",
        r"distribution",
    ],

    "candidate_comparison": [
        r"compare\s+\w[\w\s]+and\s+\w",
        r"\bvs\b|\bversus\b",
        r"difference\s+between",
        r"who\s+is\s+better",
        r"side.by.side",
    ],
    "hiring_recommendation": [
        r"(who|which)\s+(should|shall|would)\s+(i|we|you)\s+hire",
        r"recommend.*hire",
        r"hiring\s+(decision|recommendation)",
        r"should\s+(i|we)\s+hire",
        r"(best|top)\s+(candidate|person)\s+to\s+hire",
    ],
    "why_low_rank": [
        r"why.*(rank|score).*(low|poor|weak|bad)",
        r"why.*(low|poor|bad|weak).*(score|rank)",
        r"reason.*(low|poor).*(score|rank)",
        r"why.*not.*shortlist",
    ],
    "interview_performance": [
        r"how.*did.*perform.*interview",
        r"interview\s+(score|result|analysis|feedback|performance)",
        r"(communication|confidence)\s+(score|level|rating)",
        r"cheating\s+risk",
    ],
    "generate_questions": [
        r"(generate|create|give|make|suggest).*interview.*question",
        r"what.*should.*i.*ask",
        r"question.*to.*ask",
        r"prepare.*interview",
    ],

    "greeting": [
        r"^(hi|hello|hey|howdy|greetings)[\s!.]*$",
        r"^(good\s+(morning|afternoon|evening))[\s!.]*$",
    ],
    "help": [
        r"(what can you|help me|what do you|capabilities|commands?)",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SEMANTIC INTENT CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticClassifier:
    def __init__(self):
        self.anchors = {
            "top_candidates": ["show the best candidates", "who are the top ranked people", "highest matching resumes", "rank candidates for me"],
            "candidate_search": ["find python developers", "look for engineers with react", "who knows docker", "search for cloud experts"],
            "candidate_profile": ["tell me about this candidate", "summarize ravi's profile", "what are his strengths", "describe john doe"],
            "candidate_comparison": ["compare alice and bob", "who is better ravi or priya", "alice vs bob side by side", "difference between candidates"],
            "hiring_recommendation": ["who should i hire for this role", "give me a hiring recommendation", "which applicant is best to hire", "suggest a hire"],
            "why_low_rank": ["why did ravi rank low", "reason for poor score", "what is missing in this profile", "why was she rejected"],
            "interview_performance": ["how did ravi perform in the interview", "was the interview good", "check communication score", "cheating risk status"],
            "generate_questions": ["generate interview questions", "what should i ask a marketing manager", "create questions for backend role", "prep for interview"],
            "analytics": ["most common skills", "average match score", "hiring funnel stats", "how many candidates in total"],
            "help": ["what can you do", "show capabilities", "help me use the assistant", "available commands"],
            "greeting": ["hello", "hi there", "hey ai", "good morning"],
        }
        self._anchor_embeds = None

    def _get_embeds(self):
        if self._anchor_embeds is None:
            try:
                from services.vector_store import get_embedding_model
                model = get_embedding_model()
                if not model: return None
                
                self._anchor_embeds = {}
                for intent, phrases in self.anchors.items():
                    self._anchor_embeds[intent] = model.encode(phrases, convert_to_numpy=True, normalize_embeddings=True)
            except Exception as e:
                logger.error(f"SemanticClassifier init failed: {e}")
                return None
        return self._anchor_embeds

    def classify(self, query: str) -> Optional[str]:
        embeds = self._get_embeds()
        if not embeds: return None
        
        try:
            from services.vector_store import get_embedding_model
            from sentence_transformers import util
            model = get_embedding_model()
            q_vec = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
            
            best_intent = None
            best_score = 0
            
            for intent, v_matrix in embeds.items():
                sims = util.cos_sim(q_vec, v_matrix)
                max_sim = float(sims.max())
                if max_sim > best_score:
                    best_score = max_sim
                    best_intent = intent
            
            if best_score > 0.55: # Threshold for semantic match
                return best_intent
        except Exception as e:
            logger.error(f"Semantic classification failed: {e}")
        return None

_classifier = SemanticClassifier()

def classify_intent(query: str, memory: list) -> str:
    q = query.lower().strip()

    # 1. Context-aware: follow-up detection
    if memory:
        last_intent = memory[-1].get("intent", "")
        if len(q.split()) <= 3 and last_intent in ("candidate_search", "top_candidates"):
            if any(w in q for w in ["which", "who", "that", "they", "their", "him", "her"]):
                return "candidate_profile"

    # 2. Hard Regex matches (Fast, high confidence)
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, q):
                return intent

    # 3. Semantic Fallback (Conversational intelligence)
    semantic_intent = _classifier.classify(q)
    if semantic_intent:
        logger.info("[Chat] Semantic match: %s (score fallback)", semantic_intent)
        return semantic_intent

    return "general"


# ═══════════════════════════════════════════════════════════════════════════════
#  DB QUERY BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_skill_from_query(query: str) -> Optional[str]:
    """Extract skill name from natural language query."""
    # Pattern: "show Python developers", "who knows Docker", "React experience"
    patterns = [
        r"(show|find|list|get)\s+(\w+)\s+(developer|engineer|candidate)",
        r"who\s+know[s]?\s+(\w+)",
        r"skilled\s+in\s+(\w+)",
        r"(\w+)\s+developer",
        r"(\w+)\s+engineer",
        r"(\w+)\s+experience",
        r"experience\s+in\s+(\w+)",
        r"know[s]?\s+(\w+)",
        r"(\w+)\s+expert",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            candidate = m.group(m.lastindex)
            # Filter out common non-skill words
            skip = {"developer", "engineer", "candidate", "candidates", "the", "a", "an",
                    "who", "what", "show", "find", "list", "get", "with", "and", "or"}
            if candidate.lower() not in skip and len(candidate) > 1:
                return candidate
    return None


def _extract_exp_years(query: str) -> Optional[float]:
    m = re.search(r'(\d+)\+?\s*years?', query, re.IGNORECASE)
    return float(m.group(1)) if m else None


async def _extract_job_title_semantic(query: str) -> Optional[dict]:
    """Uses FAISS semantic search to find the most likely job matching the query."""
    # First, try to extract a title-like string using regex
    patterns = [
        r"(?:for|role|position|job)\s+([\w\s]{3,})",
        r"(?:questions\s+for|ask\s+a)\s+([\w\s]{3,})",
        r"jd\s+for\s+([\w\s]{3,})",
    ]
    extracted = None
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            break
    
    search_term = extracted or query
    
    try:
        from services.vector_store import search_jobs
        hits = await search_jobs(search_term, top_k=1)
        if hits and hits[0]["similarity"] > 0.45:
            job = await jobs_col.find_one({"_id": ObjectId(hits[0]["id"])})
            if job:
                return job
    except Exception as e:
        logger.error(f"Semantic job extraction failed: {e}")
    
    # Final fallback: text search in DB
    if extracted:
        job = await jobs_col.find_one({"title": {"$regex": extracted, "$options": "i"}})
        if job: return job
        
    return None


def _extract_limit(query: str) -> int:
    m = re.search(r'top\s+(\d+)', query, re.IGNORECASE)
    return int(m.group(1)) if m else 5


# ═══════════════════════════════════════════════════════════════════════════════
#  RESPONSE BUILDERS  (pure DB — no LLM needed)
# ═══════════════════════════════════════════════════════════════════════════════

async def _response_top_candidates(query: str, memory: list) -> str:
    limit = _extract_limit(query)
    job = await _extract_job_title_semantic(query)
    
    db_query = {}
    job_label = "all roles"
    
    if job:
        db_query["job_id"] = str(job["_id"])
        job_label = job["title"]

    results = []
    async for c in candidates_col.find(db_query).sort("score", -1).limit(limit):
        results.append(c)

    if not results:
        return f"I couldn't find any ranked candidates for **{job_label}**. Please ensure you've uploaded resumes and ran the AI ranking process."

    # Build context for Cohere
    context = f"Top {len(results)} candidates for {job_label}:\n"
    for i, c in enumerate(results):
        context += f"{i+1}. {c['name']} (Score: {c.get('score',0):.0f}%, Exp: {c.get('experience_years',0):.0f} yrs, Skills: {', '.join(c.get('skills',[])[:5])})\n"

    llm_res = await _enhance_with_cohere(query, context)
    if llm_res: return llm_res

    # Fallback to template
    lines = [f"🏆 **Top Candidates for {job_label}:**\n"]
    for i, c in enumerate(results):
        lines.append(f"{i+1}. **{c['name']}** — {c.get('score',0):.0f}% match | {c.get('experience_years',0):.0f} yrs")
    return "\n".join(lines)


async def _response_candidate_search(query: str, memory: list) -> str:
    skill = _extract_skill_from_query(query)
    exp_years = _extract_exp_years(query)

    # Normalise skill with synonym map
    if skill:
        try:
            from resume_parser import SKILL_SYNONYMS
            skill_norm = SKILL_SYNONYMS.get(skill.lower(), skill.lower())
        except Exception:
            skill_norm = skill.lower()
    else:
        skill_norm = None

    db_query = {}
    label_parts = []

    if skill_norm:
        db_query["skills"] = {"$regex": skill_norm, "$options": "i"}
        label_parts.append(skill_norm.title())

    if exp_years:
        db_query["experience_years"] = {"$gte": exp_years}
        label_parts.append(f"{exp_years:.0f}+ years exp")

    label = " with " + " & ".join(label_parts) if label_parts else ""

    results = []
    async for c in candidates_col.find(db_query).sort("score", -1).limit(8):
        score = c.get("score", 0)
        exp = c.get("experience_years", 0)
        status = c.get("status", "pending")
        results.append(f"**{c['name']}** — {score:.0f}% | {exp:.0f} yrs | {status}")

    if not results:
        return f"No candidates found{label}. Try uploading more resumes or checking the skill name."

    return f"👥 **Candidates{label}:**\n\n" + "\n".join(
        f"{i+1}. {r}" for i, r in enumerate(results)
    )


async def _response_experience_filter(query: str, memory: list) -> str:
    exp_years = _extract_exp_years(query)
    if not exp_years:
        # Try senior/junior keywords
        if "senior" in query.lower():
            exp_years = 5.0
        elif "junior" in query.lower() or "fresher" in query.lower():
            exp_years = 0.0
            results = []
            async for c in candidates_col.find({"experience_years": {"$lte": 1.5}}).sort("score", -1).limit(8):
                results.append(f"**{c['name']}** — {c.get('experience_years', 0):.0f} yrs | {c.get('score', 0):.0f}%")
            if not results:
                return "No junior/fresher candidates found."
            return "👥 **Junior/Fresher Candidates:**\n\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(results))
        else:
            return "Please specify the experience level (e.g., '3+ years experience' or 'senior candidates')."

    results = []
    async for c in candidates_col.find({"experience_years": {"$gte": exp_years}}).sort("score", -1).limit(8):
        results.append(
            f"**{c['name']}** — {c.get('experience_years', 0):.0f} yrs | Score: {c.get('score', 0):.0f}%"
        )

    if not results:
        return f"No candidates with {exp_years:.0f}+ years of experience found."

    return f"👥 **Candidates with {exp_years:.0f}+ years of experience:**\n\n" + "\n".join(
        f"{i+1}. {r}" for i, r in enumerate(results)
    )


async def _response_status_query(query: str, memory: list) -> str:
    q_lower = query.lower()
    if "shortlist" in q_lower:
        status = "shortlisted"
    elif "reject" in q_lower:
        status = "rejected"
    elif "interview" in q_lower:
        status = "interview_scheduled"
    elif "selected" in q_lower:
        status = "selected"
    else:
        status = "pending"

    count = await candidates_col.count_documents({"status": status})
    results = []
    async for c in candidates_col.find({"status": status}).sort("score", -1).limit(5):
        results.append(f"**{c['name']}** — {c.get('score', 0):.0f}%")

    label = status.replace("_", " ").title()
    if not results:
        return f"No {label} candidates found."

    preview = "\n".join(f"{i+1}. {r}" for i, r in enumerate(results))
    suffix = f"\n\n_Showing top 5 of {count} total_" if count > 5 else ""
    return f"📋 **{label} Candidates ({count} total):**\n\n{preview}{suffix}"


async def _response_job_query(query: str, memory: list) -> str:
    job_title = _extract_job_title(query)
    if job_title:
        job = await jobs_col.find_one({"title": {"$regex": job_title, "$options": "i"}})
        if job:
            skills = ", ".join(job.get("required_skills", [])[:10]) or "Not specified"
            count = await candidates_col.count_documents({"job_id": str(job["_id"])})
            return (
                f"📋 **{job['title']}**\n\n"
                f"**Required Skills:** {skills}\n"
                f"**Candidates:** {count}\n"
                f"**Description:** {job.get('description', '')[:300]}..."
            )
        return f"No job found matching '{job_title}'. Check available roles below."

    # List all jobs
    jobs = []
    async for j in jobs_col.find().sort("created_at", -1).limit(10):
        count = await candidates_col.count_documents({"job_id": str(j["_id"])})
        skills_preview = ", ".join(j.get("required_skills", [])[:4])
        jobs.append(f"**{j['title']}** — {count} candidates | Skills: {skills_preview}")

    if not jobs:
        return "No jobs found. Create a job first from the Jobs page."

    return "💼 **Available Job Roles:**\n\n" + "\n".join(f"{i+1}. {j}" for i, j in enumerate(jobs))


async def _response_analytics(query: str, memory: list) -> str:
    q_lower = query.lower()

    if "common skill" in q_lower or "frequent skill" in q_lower:
        pipeline = [
            {"$unwind": "$skills"},
            {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        results = []
        async for doc in candidates_col.aggregate(pipeline):
            results.append(f"**{doc['_id']}** — {doc['count']} candidates")
        if not results:
            return "No skill data available yet. Upload and rank some resumes first."
        return "📊 **Most Common Skills:**\n\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(results))

    elif "average" in q_lower and "experience" in q_lower:
        pipeline = [{"$group": {"_id": None, "avg_exp": {"$avg": "$experience_years"}}}]
        async for doc in candidates_col.aggregate(pipeline):
            avg = doc.get("avg_exp", 0)
            return f"📊 **Average Experience:** {avg:.1f} years across all candidates."
        return "No candidate data available."

    elif "average" in q_lower and "score" in q_lower:
        pipeline = [{"$group": {"_id": None, "avg_score": {"$avg": "$score"}}}]
        async for doc in candidates_col.aggregate(pipeline):
            avg = doc.get("avg_score", 0)
            return f"📊 **Average AI Match Score:** {avg:.1f}%"
        return "No scored candidates yet."

    elif "missing" in q_lower and "skill" in q_lower:
        skill = _extract_skill_from_query(query)
        if skill:
            count = await candidates_col.count_documents(
                {"skills": {"$not": {"$regex": skill, "$options": "i"}}}
            )
            total = await candidates_col.count_documents({})
            return f"📊 **{count} of {total} candidates** are missing **{skill}** skills."
        return "Please specify which skill to check (e.g., 'candidates missing Docker')."

    elif "how many" in q_lower or "count" in q_lower:
        total = await candidates_col.count_documents({})
        shortlisted = await candidates_col.count_documents({"status": "shortlisted"})
        rejected = await candidates_col.count_documents({"status": "rejected"})
        pending = await candidates_col.count_documents({"status": "pending"})
        return (
            f"📊 **Candidate Pipeline Stats:**\n\n"
            f"• Total: **{total}**\n"
            f"• Shortlisted: **{shortlisted}**\n"
            f"• Rejected: **{rejected}**\n"
            f"• Pending: **{pending}**"
        )

    else:
        total = await candidates_col.count_documents({})
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        breakdown = {}
        async for doc in candidates_col.aggregate(pipeline):
            breakdown[doc["_id"]] = doc["count"]

        lines = [f"• {k.replace('_',' ').title()}: **{v}**" for k, v in breakdown.items()]
        return f"📊 **Pipeline Analytics ({total} total candidates):**\n\n" + "\n".join(lines)


async def _response_candidate_profile(query: str, memory: list) -> str:
    """Profile lookup — try to match candidate name from query or memory."""
    # Try to extract name from query
    name_match = re.search(r"(?:about|summarize|profile|tell me about)\s+(.+?)(?:\?|$)", query, re.IGNORECASE)
    search_name = name_match.group(1).strip() if name_match else None

    # If no name in query, use last mentioned candidate from memory
    if not search_name and memory:
        for turn in reversed(memory):
            if "last_candidates" in turn:
                candidate_name = turn["last_candidates"][0] if turn["last_candidates"] else None
                if candidate_name:
                    search_name = candidate_name
                    break

    if not search_name:
        return "Please specify which candidate you'd like to know about (e.g., 'Summarize John Doe')."

    candidate = await candidates_col.find_one(
        {"name": {"$regex": search_name, "$options": "i"}}
    )
    if not candidate:
        # Try partial match
        parts = search_name.split()
        if parts:
            candidate = await candidates_col.find_one(
                {"name": {"$regex": parts[0], "$options": "i"}}
            )

    if not candidate:
        return f"No candidate found matching '{search_name}'."

    name        = candidate.get("name", "Unknown")
    skills      = ", ".join(candidate.get("skills", [])[:8]) or "Not detected"
    exp         = candidate.get("experience_years", 0)
    score       = candidate.get("score", 0)
    education   = ", ".join(candidate.get("education", [])[:3]) or "Not detected"
    certs       = ", ".join(candidate.get("certifications", [])[:3]) or "None listed"
    projects    = ", ".join(candidate.get("projects", [])[:3]) or "Not detected"
    status      = candidate.get("status", "pending").replace("_", " ").title()
    location    = candidate.get("location", "Not specified")
    missing     = ", ".join(candidate.get("missing_skills", [])[:5]) or "None"
    matched     = ", ".join(candidate.get("matched_skills", [])[:5]) or "None"

    # Interview Analysis (if available)
    interview_summary = ""
    analysis = candidate.get("ai_analysis")
    if analysis:
        interview_summary = (
            f"\n**🧠 AI Interview Insights:**\n"
            f"• **Recommendation:** {analysis.get('recommendation')}\n"
            f"• **Communication:** {analysis.get('communication')}\n"
            f"• **Confidence:** {analysis.get('confidence')}\n"
            f"• **Cheating Risk:** {analysis.get('cheating_risk')}\n"
            f"• **Reasoning:** {analysis.get('reasoning')}\n"
        )
    elif candidate.get("status") == "interview_scheduled":
        interview_summary = "\n**📅 Interview status:** Scheduled (Waiting for results)\n"

    return (
        f"👤 **{name}**\n\n"
        f"• **AI Match Score:** {score:.0f}%\n"
        f"• **Experience:** {exp:.0f} years\n"
        f"• **Status:** {status}\n"
        f"• **Location:** {location}\n"
        f"• **Education:** {education}\n"
        f"• **Key Skills:** {skills}\n"
        f"• **Certifications:** {certs}\n"
        f"• **Projects:** {projects}\n"
        f"• **Matched Req Skills:** {matched}\n"
        f"• **Missing Req Skills:** {missing}\n"
        f"{interview_summary}"
    )


def _response_greeting() -> str:
    return (
        "👋 **Hello! I'm your AI Recruitment Analyst.**\n\n"
        "I can help you with:\n"
        "• 🔍 **Find candidates** — 'Show Python developers'\n"
        "• 🏆 **Rankings** — 'Top 5 for Data Scientist'\n"
        "• ⚖️ **Compare** — 'Compare Alice and Ravi'\n"
        "• 🎯 **Hire decision** — 'Who should I hire for Backend?'\n"
        "• 📉 **Explain score** — 'Why did Ravi rank low?'\n"
        "• 🎥 **Interview** — 'How did Priya perform in the interview?'\n"
        "• 📝 **Questions** — 'Generate interview questions for ML Engineer'\n"
        "• 📊 **Analytics** — 'Most common skills'\n\n"
        "What would you like to know?"
    )


def _response_help() -> str:
    return (
        "🤖 **AI Recruitment Analyst — Full Capabilities**\n\n"
        "**🔍 Candidate Search:**\n"
        "• 'Show Python developers'\n"
        "• 'Candidates with React and Node experience'\n"
        "• 'Candidates with 3+ years experience'\n\n"
        "**🏆 Rankings & Recommendations:**\n"
        "• 'Top 5 candidates for Backend Developer'\n"
        "• 'Who should I hire for Data Analyst?'\n"
        "• 'Best candidate for this role'\n\n"
        "**⚖️ Candidate Comparison:**\n"
        "• 'Compare Alice and Ravi'\n"
        "• 'Alice vs Bob for Backend role'\n"
        "• 'Who is better between Priya and Sam?'\n\n"
        "**📉 Score Explanation:**\n"
        "• 'Why did Ravi rank low?'\n"
        "• 'What skills is Alice missing?'\n"
        "• 'Why was this candidate not shortlisted?'\n\n"
        "**🎥 Interview Intelligence:**\n"
        "• 'How did Ravi perform in the interview?'\n"
        "• 'What was Priya communication score?'\n"
        "• 'Show cheating risk for this candidate'\n\n"
        "**📝 Interview Prep:**\n"
        "• 'Generate interview questions for ML Engineer'\n"
        "• 'What should I ask a Backend Developer?'\n\n"
        "**📊 Analytics:**\n"
        "• 'Most common skills'\n"
        "• 'Average experience of shortlisted candidates'\n"
        "• 'How many candidates missing Docker?'"
    )



# ═══════════════════════════════════════════════════════════════════════════════
#  NEW RECRUITER INTELLIGENCE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_names_from_query(query: str):
    """Extract candidate names from a comparison query like 'Compare Alice and Bob'."""
    # Pattern: compare X and Y / X vs Y
    m = re.search(r"compare\s+([\w\s]+?)\s+(?:and|vs|versus)\s+([\w\s]+?)(?:\s+for|\s*$)", query, re.IGNORECASE)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    m = re.search(r"([\w]+)\s+(?:vs|versus)\s+([\w]+)", query, re.IGNORECASE)
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
                "Please specify which candidates to compare.\n"
                "Example: **'Compare Alice and Ravi'** or **'Alice vs Bob for Backend role'**"
            )
        found = [c["name"] for c in candidates]
        missing = [n for n in names if not any(n.lower() in c["name"].lower() for c in candidates)]
        return f"Could not find candidate(s): **{', '.join(missing)}**. Please check the name spelling."

    lines = [f"⚖️ **Candidate Comparison**\n"]
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
            f"\n**{c['name']}**\n"
            f"• AI Score: **{c.get('score', 0):.0f}%** | Recommendation: **{rec}**\n"
            f"• Experience: {c.get('experience_years', 0):.0f} yrs | "
            f"Technical Fit: {c.get('technical_fit', 0):.0f}%\n"
            f"• Top Skills: {skills}\n"
            f"• Missing Skills: {', '.join(c.get('missing_skills', [])[:3]) or 'None'}\n"
            f"• Status: {c.get('status', 'pending').replace('_', ' ').title()}"
        )

    # Winner determination
    best = max(candidates, key=lambda x: x.get("score", 0))
    lines.append(f"\n🏆 **Winner: {best['name']}** — {best.get('score', 0):.0f}% overall match")
    return "\n".join(lines)


async def _response_hiring_recommendation(query: str, memory: list) -> str:
    """Handle: 'Who should I hire for Backend Developer?' — top candidates with reasoning."""
    job = await _extract_job_title_semantic(query)
    limit = _extract_limit(query) or 3

    db_query = {}
    job_label = "this role"
    if job:
        db_query["job_id"] = str(job["_id"])
        job_label = job["title"]

    results = []
    async for c in candidates_col.find(db_query).sort("score", -1).limit(limit):
        results.append(c)

    if not results:
        return f"I don't have enough data to make a recommendation for **{job_label}**. Try asking about a specific skill or role that has ranked candidates."

    # Build rich context for Cohere
    context = f"Hiring recommendations for {job_label}:\n"
    for c in results:
        h_summary = c.get("hiring_summary", {})
        context += (
            f"- {c['name']}: {c.get('score',0):.0f}% match. Recommendation: {h_summary.get('recommendation')}. "
            f"Strengths: {', '.join(h_summary.get('strengths',[])[:2])}. Gaps: {', '.join(c.get('missing_skills',[])[:2])}\n"
        )

    llm_res = await _enhance_with_cohere(query, context)
    if llm_res: return llm_res

    # Template fallback
    return f"🎯 **Recommendation for {job_label}:**\n\n" + "\n".join([f"• **{c['name']}** ({c.get('score',0):.0f}%) — {c.get('hiring_summary',{}).get('recommendation')}" for c in results])


async def _response_why_low_rank(query: str, memory: list) -> str:
    """Handle: 'Why did Ravi rank low?' — evidence-based low-score explanation."""
    # Extract candidate name
    m = re.search(r"why.*?(?:did|does|is)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+", query)
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
        f"📉 **Why {name} ranked low ({score:.0f}% match):**\n\n"
        + "\n".join(reasons)
        + f"\n\n**AI Recommendation:** {verdict}\n"
        "_To improve ranking, candidate needs to upskill in the missing areas._"
    )


async def _response_interview_performance(query: str, memory: list) -> str:
    """Handle: 'How did Ravi perform in the interview?' — AI analysis summary."""
    m = re.search(r"(?:how|what).{0,10}(?:did|was|is)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+", query)
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
        f"🎥 **Interview Performance: {name}**\n\n"
        f"• **Communication:** {comm} ({metrics.get('comm_score', 'N/A')}% speaking ratio)\n"
        f"• **Confidence:** {conf} ({metrics.get('eye_contact', 'N/A')}% eye contact)\n"
        f"• **Cheating Risk:** {risk}\n"
        f"• **AI Recommendation:** {rec}\n"
        + (f"\n_{reasoning}_" if reasoning else "")
    )


async def _response_generate_questions(query: str, memory: list) -> str:
    """Handle: 'Generate interview questions for Backend Developer' — call Q generator."""
    job = await _extract_job_title_semantic(query)

    if not job:
        # Suggest available roles
        job_list = []
        async for j in jobs_col.find().limit(5):
            job_list.append(f"• **{j['title']}**")
        
        return (
            "I'd be happy to help generate questions! Which role are you preparing for?\n\n"
            "I see these roles in your pipeline:\n" + ("\n".join(job_list) if job_list else "I don't see any active jobs yet. You can create one in the Jobs section.")
        )

    job_label = job.get("title", "this role")
    skills = job.get("required_skills", [])
    
    # Try LLM first for creative questions
    context = f"Generate 5-8 interview questions for {job_label}. Required skills: {', '.join(skills[:8])}."
    llm_res = await _enhance_with_cohere(query, context)
    if llm_res: return llm_res

    # Template fallback
    questions = [f"• **Technical:** Walk me through your experience with {s}." for s in skills[:4]]
    questions.append("• **Behavioral:** Tell me about a complex project you delivered.")
    
    return f"📝 **Interview Questions for {job_label}:**\n\n" + "\n".join(questions)



# ═══════════════════════════════════════════════════════════════════════════════
#  GROQ LLAMA 3.3 70B INTEGRATION  (primary LLM engine)
# ═══════════════════════════════════════════════════════════════════════════════

async def _build_recruiter_context() -> str:
    """Fetch a rich snapshot of the ATS pipeline to inject as Groq context."""
    lines = []
    # Jobs
    jobs = []
    async for j in jobs_col.find().sort("created_at", -1).limit(10):
        cnt = await candidates_col.count_documents({"job_id": str(j["_id"])})
        skills = ", ".join(j.get("required_skills", [])[:6])
        jobs.append(f"  - {j['title']} ({cnt} candidates) | Required: {skills}")
    lines.append("ACTIVE JOB POSTINGS:")
    lines.extend(jobs or ["  None"])

    # Top candidates
    lines.append("\nTOP CANDIDATES (by AI score):")
    async for c in candidates_col.find().sort("score", -1).limit(15):
        hs = c.get("hiring_summary", {})
        ai = c.get("ai_analysis", {})
        skills = ", ".join(c.get("skills", [])[:5])
        missing = ", ".join(c.get("missing_skills", [])[:3])
        lines.append(
            f"  - {c['name']} | Score: {c.get('score',0):.0f}% | Exp: {c.get('experience_years',0):.0f}y "
            f"| Status: {c.get('status','pending')} | Rec: {hs.get('recommendation','N/A')} "
            f"| Skills: {skills} | Missing: {missing or 'none'} "
            f"| Communication: {ai.get('communication','N/A')} | Risk: {ai.get('cheating_risk','N/A')}"
        )

    # Pipeline stats
    total = await candidates_col.count_documents({})
    shortlisted = await candidates_col.count_documents({"status": "shortlisted"})
    scheduled = await candidates_col.count_documents({"status": "interview_scheduled"})
    selected = await candidates_col.count_documents({"status": "selected"})
    lines.append(f"\nPIPELINE STATS: Total={total} | Shortlisted={shortlisted} | Interviews Scheduled={scheduled} | Selected={selected}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are HireIQ Copilot, an elite AI Recruitment Assistant built for professional HR teams and recruiters.

Your role is to:
- Analyze candidate profiles and AI scores with expert precision
- Provide hiring recommendations with clear reasoning
- Draft professional recruiter emails (offer letters, rejections, interview invites)
- Generate tailored interview questions for any role
- Explain AI rankings and scoring decisions in recruiter-friendly language
- Identify top talent, skill gaps, and hiring risks
- Assist with talent rediscovery across the pipeline
- Answer ANY recruiter question intelligently and conversationally

Tone: Professional, confident, and concise. Use markdown formatting (bold names, bullet points, headers).
Always ground answers in the provided ATS data. If data is missing, state what's needed.
Never hallucinate candidate names or scores — only use what is in the context."""


async def _enhance_with_groq(query: str, db_context: str, conversation_history: list) -> Optional[str]:
    """Call Llama 3.3 70B with full recruiter context and conversation history."""
    import os
    from groq import AsyncGroq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("[Groq] GROQ_API_KEY not set, falling back")
        return None
    try:
        client = AsyncGroq(api_key=api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject DB context as a system message
        if db_context:
            messages.append({"role": "system", "content": f"CURRENT ATS DATA:\n{db_context}"})

        # Add conversation history (last 8 turns)
        for turn in conversation_history[-16:]:
            role = "user" if turn.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": turn.get("text", "")})

        # Add current query
        messages.append({"role": "user", "content": query})

        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[Groq] Failed: {e}")
        return None


async def _enhance_with_cohere(query: str, db_context: str) -> Optional[str]:
    """Cohere fallback — used only when Groq key is missing."""
    import os
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key or api_key == "your_cohere_key":
        return None
    try:
        import cohere
        client = cohere.Client(api_key)
        prompt = (
            "You are an expert AI Recruitment Analyst. Answer recruiter queries using the context below.\n"
            f"Query: {query}\n\nContext:\n{db_context}\n\nRespond with markdown formatting."
        )
        response = client.chat(model="command-r-plus-08-2024", message=prompt, temperature=0.3)
        return response.text.strip()
    except Exception as e:
        logger.error(f"[Cohere] Enhancement failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/query")
async def process_chat_query(
    chat_query: ChatQuery,
    current_user=Depends(get_current_user),
):
    query  = chat_query.query.strip()
    uid    = current_user.get("email", "default")
    memory = _session_memory[uid]

    intent = classify_intent(query, memory)
    logger.info("[Chat] User=%s Intent=%s Query=%s", uid, intent, query)

    # Build full ATS context for Groq (jobs + candidates + stats)
    db_context = await _build_recruiter_context()

    # ── Route to handler ──────────────────────────────────────────────────────

    if intent == "greeting":
        response = _response_greeting()

    elif intent == "help":
        response = _response_help()

    elif intent == "top_candidates":
        response = await _response_top_candidates(query, memory)

    elif intent == "candidate_search":
        response = await _response_candidate_search(query, memory)

    elif intent == "experience_filter":
        response = await _response_experience_filter(query, memory)

    elif intent == "status_query":
        response = await _response_status_query(query, memory)

    elif intent == "job_query":
        response = await _response_job_query(query, memory)

    elif intent == "ranking_query":
        response = await _response_top_candidates(query, memory)

    elif intent == "analytics":
        response = await _response_analytics(query, memory)

    elif intent == "candidate_profile":
        response = await _response_candidate_profile(query, memory)

    elif intent == "candidate_comparison":
        response = await _response_candidate_comparison(query, memory)

    elif intent == "hiring_recommendation":
        response = await _response_hiring_recommendation(query, memory)

    elif intent == "why_low_rank":
        response = await _response_why_low_rank(query, memory)

    elif intent == "interview_performance":
        response = await _response_interview_performance(query, memory)

    elif intent == "generate_questions":
        response = await _response_generate_questions(query, memory)

    else:
        # Groq handles ALL free-form queries: email drafting, rediscovery, summaries, anything
        response = await _enhance_with_groq(query, db_context, memory)
        if not response:
            response = (
                "I can help with candidate analysis, hiring decisions, email drafting, "
                "interview questions, and more. Type **'help'** to see all capabilities."
            )

    # Enrich short structured responses with Groq context
    if intent not in ("greeting", "help") and len(response) < 400:
        enriched = await _enhance_with_groq(query, f"{db_context}\n\nInitial answer: {response}", memory)
        if enriched:
            response = enriched

    # ── Update session memory ─────────────────────────────────────────────────
    memory.append({"role": "user", "text": query, "intent": intent})
    memory.append({"role": "bot",  "text": response})
    if len(memory) > MAX_MEMORY * 2:
        _session_memory[uid] = memory[-(MAX_MEMORY * 2):]

    return {"response": response, "intent": intent}


@router.post("/stream")
async def chat_stream(
    chat_query: ChatQuery,
    current_user=Depends(get_current_user),
):
    query = chat_query.query.strip()
    uid = current_user.get("email", "default")
    memory = _session_memory[uid]

    from fastapi.responses import StreamingResponse
    import os
    from groq import AsyncGroq
    import traceback

    api_key = os.environ.get("GROQ_API_KEY")
    try:
        groq_client = AsyncGroq(
            api_key=api_key
        )
    except Exception as init_err:
        tb = traceback.format_exc()
        print(f"\n[GROQ INIT ERROR] EXCEPTION OCCURRED DURING CLIENT INITIALIZATION!")
        print(f"GROQ KEY EXISTS: {bool(api_key)}")
        print(f"RAW ERROR: {str(init_err)}")
        print(f"TRACEBACK:\n{tb}")
        logger.error(f"[GROQ ERROR] Initialization failed:\n{tb}")
        
        async def err_gen():
            yield f"⚠️ Backend Configuration Error: Could not initialize Groq client. Error: {str(init_err)}"
        return StreamingResponse(err_gen(), media_type="text/plain")

    # 1. Structured DB Query Pipeline (Priority)
    from bson import ObjectId
    from services.vector_store import search_resumes

    # Fetch all job roles from DB
    jobs = []
    try:
        async for j in jobs_col.find({}):
            jobs.append(j)
    except Exception as job_err:
        logger.error(f"[DB ERROR] Failed to fetch jobs: {job_err}")

    # Detect if any job title is mentioned in the query
    selected_job = None
    for j in jobs:
        title = j.get("title", "").strip().lower()
        if not title:
            continue
        # Check direct inclusion
        if title in query.lower():
            selected_job = j
            break
        # Check token overlapping (all words of title length > 3 in query)
        words = [w.lower() for w in title.split() if len(w) > 3]
        if words and all(w in query.lower() for w in words):
            selected_job = j
            break

    # Fetch and sort candidates accordingly
    candidates = []
    try:
        if selected_job:
            job_id_str = str(selected_job["_id"])
            async for c in candidates_col.find({"job_id": job_id_str}):
                candidates.append(c)
        else:
            # Fallback: top candidates across entire database
            async for c in candidates_col.find({}).sort("score", -1).limit(10):
                candidates.append(c)
    except Exception as cand_err:
        logger.error(f"[DB ERROR] Failed to fetch candidates: {cand_err}")

    # Define sorting priority
    def get_rec_priority(cand):
        rec = str(cand.get("hiring_summary", {}).get("recommendation", "")).strip().lower()
        if "strong" in rec:
            return 4
        elif "hire" in rec:
            return 3
        elif "hold" in rec:
            return 2
        elif "reject" in rec:
            return 1
        return 0

    def sort_key(cand):
        return (
            float(cand.get("score") or 0.0),
            get_rec_priority(cand),
            float(cand.get("experience_years") or 0.0)
        )

    candidates.sort(key=sort_key, reverse=True)

    # Format the dynamic database RAG context
    rag_context = "--- DYNAMIC ATS DATABASE RAG CONTEXT ---\n"
    if selected_job:
        rag_context += f"Job Title: {selected_job.get('title')} (ID: {str(selected_job['_id'])})\n"
        rag_context += f"Required Skills: {', '.join(selected_job.get('required_skills', []))}\n\n"
        rag_context += f"Candidates registered in ATS pipeline for '{selected_job.get('title')}':\n"
        if candidates:
            for rank, c in enumerate(candidates, 1):
                hs = c.get("hiring_summary", {}) or {}
                ai = c.get("ai_analysis", {}) or {}
                rec = hs.get("recommendation", "N/A")
                strengths = ", ".join(hs.get("strengths", [])[:3])
                rag_context += (
                    f"{rank}. Name: {c.get('name')} | Match Score: {c.get('score', 0):.0f}% | "
                    f"Rec: {rec} | Status: {c.get('status')} | Exp: {c.get('experience_years', 0):.1f}y | "
                    f"Cheating Risk: {ai.get('cheating_risk', 'N/A')} | "
                    f"Skills: {', '.join(c.get('skills', []))} | Strengths: {strengths}\n"
                )
        else:
            rag_context += "No candidates found in the database for this job role. Report that no candidates exist.\n"
    else:
        rag_context += "Active Jobs in Database:\n"
        for j in jobs:
            rag_context += f"- Job: {j.get('title')} (ID: {str(j['_id'])})\n"
            
        rag_context += "\nTop Candidates across all jobs:\n"
        for rank, c in enumerate(candidates, 1):
            cand_job_title = "Unknown Job"
            for j in jobs:
                if str(j["_id"]) == c.get("job_id"):
                    cand_job_title = j.get("title")
                    break
            hs = c.get("hiring_summary", {}) or {}
            rec = hs.get("recommendation", "N/A")
            rag_context += (
                f"{rank}. {c.get('name')} | Job: {cand_job_title} | Score: {c.get('score', 0):.0f}% | "
                f"Rec: {rec} | Status: {c.get('status')}\n"
            )

    # 2. Semantic vector search (for resume reasoning/rediscovery support)
    try:
        resume_hits = await search_resumes(query, top_k=5)
    except Exception:
        resume_hits = []
        
    semantic_context = ""
    if resume_hits:
        semantic_context += "\n--- SEMANTIC RESUME SEARCH RESULTS (For reference) ---\n"
        for h in resume_hits:
            c = await candidates_col.find_one({"_id": ObjectId(h["id"])})
            if c:
                semantic_context += f"Candidate: {c.get('name')} (Score: {c.get('score', 0):.0f}%)\n"
                semantic_context += f"Matching resume text snippet: {h.get('text', '')[:300]}\n\n"

    system_prompt = """You are HireIQ Copilot, an elite AI Recruitment Assistant powered by Llama 3.3 70B.

Your task is to answer the recruiter's questions about candidate pipelines, matching, and qualifications.

CONCISENESS RULES:
1. ALWAYS keep your response extremely brief and direct (1-3 sentences max).
2. NEVER write long paragraphs, long essays, or lists of bullet points unless explicitly asked by the recruiter.
3. NEVER repeat sentences or duplicate words/phrases.
4. Directly state the top candidates and their scores based strictly on the DYNAMIC ATS DATABASE RAG CONTEXT below.
5. If no candidates exist for a role, state that clearly and suggest uploading resumes."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": rag_context}
    ]
    if semantic_context:
        messages.append({"role": "system", "content": semantic_context})

    for turn in memory[-10:]:
        messages.append({"role": turn["role"], "content": turn["text"]})
        
    messages.append({"role": "user", "content": query})

    async def generate():
        full_text = ""
        try:
            response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
                temperature=0.4,
                max_tokens=800
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    yield text
        except Exception as e:
            tb = traceback.format_exc()
            raw_key = os.environ.get("GROQ_API_KEY")
            print(f"\n[GROQ STREAM ERROR] EXCEPTION OCCURRED DURING API CALL!")
            print(f"GROQ KEY EXISTS: {bool(raw_key)}")
            print(f"MODEL USED: llama-3.3-70b-versatile")
            print(f"RAW GROQ ERROR: {str(e)}")
            print(f"TRACEBACK:\n{tb}")
            
            err_msg = f"\n\n⚠️ AI Error: {str(e)}"
            full_text += err_msg
            yield err_msg
            
        memory.append({"role": "user", "text": query})
        memory.append({"role": "assistant", "text": full_text})
        if len(memory) > MAX_MEMORY * 2:
            _session_memory[uid] = memory[-(MAX_MEMORY * 2):]

    return StreamingResponse(generate(), media_type="text/plain")

@router.delete("/history")
async def clear_chat_history(current_user=Depends(get_current_user)):
    uid = current_user.get("email", "default")
    _session_memory[uid] = []
    return {"message": "Chat history cleared"}
