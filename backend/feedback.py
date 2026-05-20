import os
import cohere
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("COHERE_API_KEY")
        if api_key:
            _client = cohere.Client(api_key)
    return _client

def get_resume_feedback(resume_text: str, job_description: str) -> dict:
    """
    Generates a structured, professional evaluation of the candidate.
    Returns a dict with: strengths, weaknesses, suitability, assessment, verdict.
    """
    client = _get_client()
    if client:
        try:
            # We use a JSON prompt to ensure the LLM doesn't dump raw resume text
            prompt = (
                "You are an expert HR recruitment specialist. Analyze the provided resume against the job description.\n"
                "Return your analysis ONLY as a valid JSON object with the following keys:\n"
                "- 'strengths': (list of strings, 3-4 bullets)\n"
                "- 'weaknesses': (list of strings, 2-3 bullets)\n"
                "- 'suitability': (string, explain level and justification)\n"
                "- 'assessment': (list of strings, technical evaluation bullets)\n"
                "- 'verdict': (string, one concise summary sentence)\n\n"
                f"JOB DESCRIPTION:\n{job_description[:1200]}\n\n"
                f"CANDIDATE RESUME:\n{resume_text[:3000]}\n\n"
                "Constraints:\n"
                "1. Strictly NO raw resume text dumping.\n"
                "2. Each bullet must be an insight, not a copy-paste.\n"
                "3. Focus on skill gaps and role alignment."
            )

            response = client.chat(
                model="command-r-plus-08-2024",
                message=prompt,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            data = json.loads(response.text)
            
            # Validation: Ensure lists aren't empty and content isn't just the resume
            if not data.get("strengths") or resume_text[:150] in str(data):
                raise ValueError("Low quality or repetitive LLM response")
                
            return data
            
        except Exception as e:
            logger.error(f"[Feedback] AI generation failed: {e}")

    # Professional Rule-based fallback (Always returns the same dict structure)
    return _rule_based_feedback(resume_text, job_description)

def _rule_based_feedback(resume_text: str, job_description: str) -> dict:
    from resume_parser import extract_skills, extract_experience_years
    from matching import compute_skill_score, extract_required_experience

    job_skills = extract_skills(job_description)
    candidate_skills = extract_skills(resume_text)
    skill_score, matched, semantic, partial, missing = compute_skill_score(job_skills, candidate_skills)
    
    candidate_exp = extract_experience_years(resume_text)
    required_exp = extract_required_experience(job_description)

    # ── Strengths ──────────────────────────────────────────────────────────
    strengths = []
    if matched:
        strengths.append(f"Direct proficiency in key required skills: {', '.join(list(matched)[:3])}")
    if semantic:
        strengths.append(f"Strong conceptual alignment with {len(semantic)} related technologies")
    if candidate_exp >= required_exp and required_exp > 0:
        strengths.append(f"Meets target experience ({candidate_exp:.0f} years detected)")
    if not strengths:
        strengths.append("Foundational technical background in industry standards")

    # ── Weaknesses ──────────────────────────────────────────────────────────
    weaknesses = []
    if missing:
        weaknesses.append(f"Missing critical exposure to: {', '.join(list(missing)[:3])}")
    if candidate_exp < required_exp and required_exp > 0:
        weaknesses.append(f"Experience gap: {candidate_exp:.0f} years detected vs {required_exp:.0f} years required")
    if not weaknesses:
        weaknesses.append("May require upskilling in niche tools mentioned in JD")

    # ── Technical Assessment ────────────────────────────────────────────────
    assessment = []
    if skill_score > 70:
        assessment.append("Strong technical alignment with core JD requirements")
    else:
        assessment.append("Partial technical alignment; some upskilling required")
    
    if candidate_exp > 5:
        assessment.append("Demonstrated professional maturity and long-term project exposure")

    # ── Suitability & Verdict ───────────────────────────────────────────────
    score_pct = int(skill_score)
    if score_pct >= 80:
        suitability = f"High suitability ({score_pct}% skill match). Strong alignment."
        verdict = "Excellent profile; prioritize for technical screening."
    elif score_pct >= 50:
        suitability = f"Moderate suitability ({score_pct}% skill match). Meets core requirements."
        verdict = "Promising profile with addressable skill gaps."
    else:
        suitability = f"Low suitability ({score_pct}% skill match). Significant alignment gaps."
        verdict = "Profile alignment does not meet the primary role requirements."

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suitability": suitability,
        "assessment": assessment,
        "verdict": verdict
    }
