"""
Feedback Generator — feedback.py
==================================
Generates structured resume-vs-JD evaluation feedback.
Uses Groq/LLaMA-3.3 if available; falls back to rule-based engine.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


def get_resume_feedback(resume_text: str, job_description: str) -> dict:
    """
    Generates a structured, professional evaluation of the candidate.
    Returns a dict with: strengths, weaknesses, suitability, assessment, verdict.
    """
    try:
        from services.llm_service import is_groq_available, llm_generate_json, sanitize_prompt_input
        if is_groq_available():
            safe_jd     = sanitize_prompt_input(job_description, max_chars=1200)
            safe_resume = sanitize_prompt_input(resume_text,     max_chars=3000)
            prompt = (
                "You are an expert HR recruitment specialist. Analyze the resume against the job description.\n"
                "Return ONLY a valid JSON object with these keys:\n"
                "- 'strengths': list of 3-4 evidence-based strength bullets\n"
                "- 'weaknesses': list of 2-3 specific gap bullets\n"
                "- 'suitability': string explaining the match level\n"
                "- 'assessment': list of technical evaluation bullets\n"
                "- 'verdict': one concise summary sentence\n\n"
                f"JOB DESCRIPTION:\n{safe_jd}\n\n"
                f"CANDIDATE RESUME:\n{safe_resume}\n\n"
                "Rules: No raw resume text. Each bullet must be an insight, not a copy-paste."
            )
            data = llm_generate_json(prompt, temperature=0.2, max_tokens=600)
            if data.get("strengths") and resume_text[:150] not in str(data):
                return data
    except Exception as e:
        logger.error("[Feedback] Groq generation failed: %s", e)

    return _rule_based_feedback(resume_text, job_description)


def _rule_based_feedback(resume_text: str, job_description: str) -> dict:
    """Deterministic rule-based fallback. Always returns the same dict structure."""
    try:
        from resume_parser import extract_skills, extract_experience_years
        from matching import compute_skill_scores, extract_required_experience

        job_skills      = extract_skills(job_description)
        candidate_skills = extract_skills(resume_text)
        skill_score, matched, semantic, partial, missing = compute_skill_scores(job_skills, candidate_skills)

        candidate_exp = extract_experience_years(resume_text)
        required_exp  = extract_required_experience(job_description)
    except Exception as e:
        logger.error("[Feedback] Rule-based fallback parse error: %s", e)
        return {
            "strengths":   ["Foundational technical background in industry standards"],
            "weaknesses":  ["Skill alignment verification required"],
            "suitability": "Unable to determine — resume parsing error",
            "assessment":  ["Manual review recommended"],
            "verdict":     "Manual review required due to parsing limitations",
        }

    # Strengths
    strengths = []
    if matched:
        strengths.append(f"Direct proficiency in key required skills: {', '.join(list(matched)[:3])}")
    if semantic:
        strengths.append(f"Strong conceptual alignment with {len(semantic)} related technologies")
    if candidate_exp >= required_exp and required_exp > 0:
        strengths.append(f"Meets target experience ({candidate_exp:.0f} years detected)")
    if not strengths:
        strengths.append("Foundational technical background in industry standards")

    # Weaknesses
    weaknesses = []
    if missing:
        weaknesses.append(f"Missing critical exposure to: {', '.join(list(missing)[:3])}")
    if candidate_exp < required_exp and required_exp > 0:
        weaknesses.append(f"Experience gap: {candidate_exp:.0f} years vs {required_exp:.0f} years required")
    if not weaknesses:
        weaknesses.append("May require upskilling in niche tools mentioned in JD")

    # Assessment
    assessment = []
    if skill_score > 70:
        assessment.append("Strong technical alignment with core JD requirements")
    else:
        assessment.append("Partial technical alignment; some upskilling required")
    if candidate_exp > 5:
        assessment.append("Demonstrated professional maturity and long-term project exposure")

    # Suitability & Verdict
    score_pct = int(skill_score)
    if score_pct >= 80:
        suitability = f"High suitability ({score_pct}% skill match). Strong alignment."
        verdict     = "Excellent profile; prioritize for technical screening."
    elif score_pct >= 50:
        suitability = f"Moderate suitability ({score_pct}% skill match). Meets core requirements."
        verdict     = "Promising profile with addressable skill gaps."
    else:
        suitability = f"Low suitability ({score_pct}% skill match). Significant alignment gaps."
        verdict     = "Profile alignment does not meet the primary role requirements."

    return {
        "strengths":   strengths,
        "weaknesses":  weaknesses,
        "suitability": suitability,
        "assessment":  assessment,
        "verdict":     verdict,
    }
