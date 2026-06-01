"""
Hiring Summary Generator
========================
Generates recruiter-grade, evidence-based hiring summaries for ranked candidates.
Uses Cohere if configured; falls back to a rich, human-sounding template engine.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Recommendation thresholds ────────────────────────────────────────────────
def _compute_recommendation(final_score: float, risk_flags: list) -> tuple[str, str]:
    """Returns (recommendation, confidence)"""
    critical_flags = [f for f in risk_flags if "critical" in f.lower() or "missing" in f.lower()]
    has_red_flag = len(critical_flags) >= 2

    if has_red_flag and final_score < 55:
        return "Reject", "High"
    elif final_score >= 80:
        return "Strong Hire", "High"
    elif final_score >= 65:
        return "Hire", "High" if len(risk_flags) <= 1 else "Medium"
    elif final_score >= 48:
        return "Hold", "Medium"
    else:
        return "Reject", "Medium"


def _template_summary(
    name: str,
    job_title: str,
    final_score: float,
    technical_fit: float,
    experience_relevance: float,
    resume_quality: float,
    matched_skills: list,
    missing_skills: list,
    experience_years: float,
    required_exp: float,
    recommendation: str,
    confidence: str,
    risk_flags: list,
) -> dict:
    """Generate a recruiter-style summary using template logic."""

    # Strengths
    strengths = []
    if technical_fit >= 70:
        top_skills = ", ".join(matched_skills[:3]) if matched_skills else "relevant technical skills"
        strengths.append(f"Strong technical alignment — demonstrates proficiency in {top_skills}")
    if experience_relevance >= 70 and experience_years >= required_exp:
        strengths.append(f"{experience_years:.0f} years of relevant experience meets or exceeds the {required_exp:.0f}-year requirement")
    if resume_quality >= 70:
        strengths.append("Well-structured resume with clear evidence of education, projects, and certifications")
    if len(matched_skills) >= 4:
        strengths.append(f"Broad skill coverage across {len(matched_skills)} required competencies")
    if not strengths:
        strengths.append("Shows foundational knowledge in at least some relevant areas")

    # Weaknesses
    weaknesses = []
    if missing_skills:
        top_missing = ", ".join(missing_skills[:3])
        weaknesses.append(f"Missing key required skills: {top_missing}")
    if experience_relevance < 50 and required_exp > 0:
        weaknesses.append(f"Experience gap — {experience_years:.0f} years detected vs {required_exp:.0f} required")
    if technical_fit < 50:
        weaknesses.append("Limited technical alignment with the job description")
    if resume_quality < 45:
        weaknesses.append("Resume lacks depth in education, projects, or certifications")
    if risk_flags:
        weaknesses.extend(risk_flags[:2])
    if not weaknesses:
        weaknesses.append("No significant weaknesses identified at this stage")

    # Narrative paragraph
    score_label = "excellent" if final_score >= 75 else "strong" if final_score >= 60 else "moderate" if final_score >= 45 else "limited"
    rec_verb = {
        "Strong Hire": "is a highly competitive candidate and is recommended for fast-track consideration",
        "Hire": "meets the core requirements and is recommended for the next interview stage",
        "Hold": "shows partial alignment and warrants further evaluation before a hiring decision",
        "Reject": "does not sufficiently meet the technical or experience requirements for this role",
    }.get(recommendation, "requires further evaluation")

    narrative = (
        f"{name} demonstrates {score_label} alignment with the {job_title} role, "
        f"achieving a composite match score of {final_score:.0f}%. "
        f"Technical fit is rated at {technical_fit:.0f}%, with experience relevance at {experience_relevance:.0f}%. "
        f"Based on the evidence in this resume, {name} {rec_verb}."
    )

    return {
        "narrative": narrative,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "recommendation": recommendation,
        "confidence": confidence,
    }


async def _cohere_summary(
    name: str,
    job_title: str,
    final_score: float,
    matched_skills: list,
    missing_skills: list,
    experience_years: float,
    resume_quality: float,
    recommendation: str,
) -> Optional[str]:
    """Try to get an LLM-generated recruiter narrative. Returns None on failure."""
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key or api_key == "your_cohere_key":
        return None
    try:
        import cohere
        client = cohere.Client(api_key, timeout=10)
        matched_str = ", ".join(matched_skills[:5]) or "none"
        missing_str = ", ".join(missing_skills[:4]) or "none"
        prompt = (
            f"You are a senior recruiter writing evaluation notes for a hiring manager.\n"
            f"Candidate: {name}\n"
            f"Role: {job_title}\n"
            f"AI Match Score: {final_score:.0f}%\n"
            f"Matched Skills: {matched_str}\n"
            f"Missing Skills: {missing_str}\n"
            f"Experience: {experience_years:.0f} years\n"
            f"Recommendation: {recommendation}\n\n"
            "Write a concise, professional 2-sentence recruiter summary explaining the recommendation. "
            "Reference specific skills and experience. Do not use generic phrases like 'based on the data'. "
            "Write as a human recruiter would in their notes. Be direct and specific."
        )
        resp = client.chat(
            model="command-r-plus-08-2024",
            message=prompt,
            temperature=0.4,
            max_tokens=150,
        )
        text = resp.text.strip()
        return text if len(text) > 30 else None
    except Exception as e:
        logger.debug(f"[HiringSummary] Cohere unavailable: {e}")
        return None


async def generate_hiring_summary(
    candidate: dict,
    job: dict,
    match_explanation: dict,
) -> dict:
    """
    Main entry point. Returns a structured hiring_summary dict to be stored
    on the candidate document.
    """
    if candidate.get("hiring_summary") and candidate["hiring_summary"].get("recommendation"):
        return candidate["hiring_summary"]

    name = candidate.get("name", "Candidate")
    job_title = job.get("title", "this role")
    final_score = float(candidate.get("score", 0))
    experience_years = float(candidate.get("experience_years", 0))

    score_breakdown = match_explanation.get("score_breakdown", {})
    tech_fit = float(score_breakdown.get("technical_fit", 0))
    # 'experience_relevance' is the correct key; 'exp_score' is the fallback for older records
    exp_rel = float(score_breakdown.get("experience_relevance") or score_breakdown.get("exp_score", 0))
    res_quality = float(score_breakdown.get("resume_quality", 0))
    matched_skills = match_explanation.get("exact_matches", []) + match_explanation.get("semantic_matches", [])
    missing_skills = match_explanation.get("missing_skills", [])
    risk_flags = match_explanation.get("risk_flags", [])

    # Compute required exp from job
    from matching import extract_required_experience
    required_exp = extract_required_experience(job.get("description", ""))

    recommendation, confidence = _compute_recommendation(final_score, risk_flags)

    # Build template summary
    summary = _template_summary(
        name=name,
        job_title=job_title,
        final_score=final_score,
        technical_fit=tech_fit,
        experience_relevance=exp_rel,
        resume_quality=res_quality,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        experience_years=experience_years,
        required_exp=required_exp,
        recommendation=recommendation,
        confidence=confidence,
        risk_flags=risk_flags,
    )

    # Try to enhance narrative with Cohere
    enhanced = await _cohere_summary(
        name=name,
        job_title=job_title,
        final_score=final_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        experience_years=experience_years,
        resume_quality=res_quality,
        recommendation=recommendation,
    )
    if enhanced:
        summary["narrative"] = enhanced

    summary["recommendation"] = recommendation
    summary["confidence"] = confidence
    summary["generated_at"] = __import__("datetime").datetime.utcnow().isoformat()

    return summary
