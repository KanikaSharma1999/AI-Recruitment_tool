"""
LLM Parser — services/llm_parser.py
=====================================
Resume and Job Description structured extraction using Groq + LLaMA-3.3.

All calls go through services/llm_service.py.

Zero-hallucination policy:
  - Every extracted field must be directly observed in the source text.
  - Missing fields default to safe empty values, never invented data.
  - Local regex/spaCy fallback runs when Groq is unavailable.
"""

import os
import json
import re
import logging
from typing import Optional

from services.llm_service import (
    llm_generate_json,
    llm_generate_json_async,
    is_groq_available,
    sanitize_prompt_input,
    _parse_json,
)

logger = logging.getLogger(__name__)


# ── JSON safety helper (kept for backward compatibility) ─────────────────────
def safe_json_loads(text: str) -> dict:
    """Safely extract and parse a JSON block from LLM output."""
    return _parse_json(text)


# ── Stubs kept for backward-compatible imports in matching.py ────────────────
def get_groq_client():
    """Deprecated stub — always returns None. Use llm_service instead."""
    return None

def _is_groq_rate_limited() -> bool:
    return False

def _set_groq_rate_limited(duration: int = 300):
    pass


# ── Resume Parser ─────────────────────────────────────────────────────────────
RESUME_PARSE_PROMPT = """You are an elite resume extraction engine with a strict zero-hallucination policy.
Extract ONLY information explicitly present in the resume text below.

CRITICAL RULES:
1. NEVER invent, infer, guess, or hallucinate any field.
2. If a field is not present, use empty values: "" / [] / 0.0 / false.
3. Extract technical_skills ONLY from explicit skill sections (Skills, Key Skills, Technical Skills, Core Competencies).
4. Do NOT add skills based on job title or company name alone.
5. candidate_name: The person's full name, usually at the very top (2-4 proper noun words).
   - REJECT lines that are job titles, social platforms (LinkedIn, GitHub), or email prefixes.
   - If unclear, derive from email username (e.g. john.doe@gmail.com → "John Doe").
6. total_experience_years: Sum employment date ranges. Return as float.
7. confidence_score: Your self-assessment 0-100 of extraction accuracy.
8. extraction_reliability: "High" if clearly structured, "Medium" if partially unclear, "Low" if noisy.

Respond with ONLY this JSON object (no markdown, no explanation):
{
  "candidate_name": "",
  "email": "",
  "phone": "",
  "location": "",
  "total_experience_years": 0.0,
  "current_title": "",
  "companies": [],
  "job_titles": [],
  "technical_skills": [],
  "soft_skills": [],
  "certifications": [],
  "education": [{"degree": "", "institution": "", "year": "", "field": ""}],
  "projects": [{"name": "", "description": "", "technologies": []}],
  "employment_timeline": [
    {"company": "", "title": "", "start_date": "", "end_date": "", "duration_months": 0,
     "description": "", "is_internship": false, "is_freelance": false}
  ],
  "leadership_experience": false,
  "domain_experience": [],
  "communication_indicators": [],
  "tools": [],
  "technologies": [],
  "languages_spoken": [],
  "awards_achievements": [],
  "github_url": "",
  "linkedin_url": "",
  "portfolio_url": "",
  "summary_or_objective": "",
  "confidence_score": 0.0,
  "ambiguity_detection": [],
  "extraction_reliability": "High"
}

RESUME TEXT:
"""

_RESUME_DEFAULTS = {
    "candidate_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "total_experience_years": 0.0,
    "current_title": "",
    "companies": [],
    "job_titles": [],
    "technical_skills": [],
    "soft_skills": [],
    "certifications": [],
    "education": [],
    "projects": [],
    "employment_timeline": [],
    "leadership_experience": False,
    "domain_experience": [],
    "communication_indicators": [],
    "tools": [],
    "technologies": [],
    "languages_spoken": [],
    "awards_achievements": [],
    "github_url": "",
    "linkedin_url": "",
    "portfolio_url": "",
    "summary_or_objective": "",
    "confidence_score": 70.0,
    "ambiguity_detection": [],
    "extraction_reliability": "Medium",
}


def parse_resume_with_llm(raw_text: str, filename: str) -> dict:
    """
    Parse a resume using Groq/LLaMA-3.3.
    Falls back to local regex/spaCy parser if Groq is unavailable.
    """
    safe_text = sanitize_prompt_input(raw_text, max_chars=8000)
    prompt = RESUME_PARSE_PROMPT + safe_text

    try:
        if not is_groq_available():
            logger.info("[LLMParser] Groq not reachable — using local fallback.")
            return parse_resume_local_fallback(raw_text, filename)

        parsed = llm_generate_json(prompt, temperature=0.0, max_tokens=3000)
        # Fill missing keys with safe defaults
        for key, default in _RESUME_DEFAULTS.items():
            parsed.setdefault(key, default)

        # Ensure candidate name is set
        if not parsed.get("candidate_name"):
            parsed["candidate_name"] = filename.split(".")[0].replace("_", " ").title()

        return parsed

    except Exception as e:
        logger.error("[LLMParser] Groq resume parse failed: %s. Using local fallback.", e)
        return parse_resume_local_fallback(raw_text, filename)


# ── JD Parser ────────────────────────────────────────────────────────────────
JD_PARSE_PROMPT = """You are an elite Job Description parser with a strict zero-hallucination policy.
Extract ONLY requirements explicitly stated in the job description below.

RULES:
1. required_skills: ONLY skills listed under "required", "must have", "qualifications", "responsibilities".
2. preferred_skills: ONLY skills under "preferred", "nice to have", "bonus", "good to have".
3. minimum_experience: Extract the number from phrases like "5+ years". If not stated, use 0.
4. certifications_required: Only if explicitly mentioned as required.
5. Do NOT add skills based on job title alone.
6. domain_requirements: Infer domain from context (e.g. "fintech", "healthcare", "e-commerce").

Respond with ONLY this JSON object (no markdown, no explanation):
{
  "role_name": "",
  "minimum_experience": 0.0,
  "required_skills": [],
  "preferred_skills": [],
  "domain_requirements": [],
  "leadership_required": false,
  "communication_required": false,
  "certifications_required": [],
  "project_requirements": [],
  "management_requirements": [],
  "key_responsibilities": [],
  "benefits": []
}

JOB DESCRIPTION:
"""

_JD_DEFAULTS = {
    "role_name": "Software Engineer",
    "minimum_experience": 0.0,
    "required_skills": [],
    "preferred_skills": [],
    "domain_requirements": [],
    "leadership_required": False,
    "communication_required": False,
    "certifications_required": [],
    "project_requirements": [],
    "management_requirements": [],
    "key_responsibilities": [],
    "benefits": [],
}


def parse_jd_with_llm(jd_text: str) -> dict:
    """
    Parse a Job Description using Groq/LLaMA-3.3.
    Falls back to local keyword parser if Groq is unavailable.
    """
    safe_text = sanitize_prompt_input(jd_text, max_chars=6000)
    prompt = JD_PARSE_PROMPT + safe_text

    try:
        if not is_groq_available():
            logger.info("[LLMParser] Groq not reachable — using local JD fallback.")
            return parse_jd_local_fallback(jd_text)

        parsed = llm_generate_json(prompt, temperature=0.0, max_tokens=2000)
        for key, default in _JD_DEFAULTS.items():
            parsed.setdefault(key, default)
        return parsed

    except Exception as e:
        logger.error("[LLMParser] Groq JD parse failed: %s. Using local fallback.", e)
        return parse_jd_local_fallback(jd_text)


# ── Candidate Intelligence Generator ─────────────────────────────────────────
INTELLIGENCE_PROMPT_TEMPLATE = """You are a senior technical recruiter with 20+ years of experience.
Your task is to write a professional recruiter intelligence report for the candidate below.

CRITICAL RULES:
- Base your analysis STRICTLY on the provided data. Do NOT invent skills or experience.
- Do NOT recalculate or second-guess the match score. Accept it as a given.
- Your job is ONLY to explain WHY the score was assigned using evidence from the profile.
- Mention matching skills by name. Mention missing skills by name.
- Strengths, Weaknesses, and Risks MUST each contain AT LEAST 3 detailed, evidence-based points.
- Keep feedback concise and recruiter-friendly.

CANDIDATE PROFILE:
Name: {name}
Experience: {exp} years
Current Title: {title}
Technical Skills: {tech_skills}
Soft Skills: {soft_skills}
Education: {education}
Certifications: {certifications}
Companies: {companies}
Job Titles: {job_titles}
Projects: {projects}
Domain Experience: {domain}
Leadership: {leadership}

JOB REQUIREMENTS:
Role: {role}
Required Skills: {req_skills}
Preferred Skills: {pref_skills}
Min Experience: {min_exp} years
Domain: {domain_req}

PRE-COMPUTED MATCH SCORES (do NOT change these):
Overall Score: {final_score}%
Skills Score:  {skill_score}%
Experience Score: {exp_score}%
Semantic Score: {sem_score}%

Respond with ONLY this JSON object (no markdown, no explanation):
{{
  "recommendation": "Strong Hire",
  "recommendation_confidence": "High",
  "executive_summary": "3-4 sentence professional assessment grounded in the evidence above.",
  "strengths": [
    "Specific strength with evidence from the profile",
    "Another specific evidence-based strength",
    "Third specific evidence-based strength"
  ],
  "weaknesses": [
    "Specific gap with context (e.g. Missing AWS — required for this role)",
    "Another specific concern",
    "Third specific concern"
  ],
  "risks": [
    "Specific hiring risk with evidence",
    "Another risk",
    "Third risk"
  ],
  "opportunities": [
    "Growth potential or upside",
    "Another opportunity"
  ],
  "interview_focus_areas": [
    "Specific technical area to probe",
    "Another focus area",
    "Another focus area"
  ],
  "hiring_red_flags": [],
  "hiring_green_flags": [],
  "culture_fit_indicators": [],
  "salary_range_fit": "Mid",
  "onboarding_complexity": "Medium",
  "time_to_productivity": "1-2 weeks"
}}
"""


def generate_candidate_intelligence(
    candidate_profile: dict,
    jd_profile: dict,
    score_breakdown: dict,
) -> dict:
    """
    Generate AI-powered candidate intelligence report.
    Uses Groq/LLaMA-3.3 to explain pre-computed scores in natural language.
    Groq DOES NOT COMPUTE THE SCORE — it only explains it.
    """
    prompt = INTELLIGENCE_PROMPT_TEMPLATE.format(
        name        = candidate_profile.get("candidate_name", "Unknown"),
        exp         = candidate_profile.get("total_experience_years", 0),
        title       = candidate_profile.get("current_title", "N/A"),
        tech_skills = ", ".join(candidate_profile.get("technical_skills", [])[:20]),
        soft_skills = ", ".join(candidate_profile.get("soft_skills", [])[:10]),
        education   = json.dumps(candidate_profile.get("education", [])[:3]),
        certifications = ", ".join(candidate_profile.get("certifications", [])[:5]),
        companies   = ", ".join(candidate_profile.get("companies", [])[:5]),
        job_titles  = ", ".join(candidate_profile.get("job_titles", [])[:5]),
        projects    = json.dumps(candidate_profile.get("projects", [])[:4]),
        domain      = ", ".join(candidate_profile.get("domain_experience", [])[:5]),
        leadership  = candidate_profile.get("leadership_experience", False),
        role        = jd_profile.get("role_name", "N/A"),
        req_skills  = ", ".join(jd_profile.get("required_skills", [])[:20]),
        pref_skills = ", ".join(jd_profile.get("preferred_skills", [])[:10]),
        min_exp     = jd_profile.get("minimum_experience", 0),
        domain_req  = ", ".join(jd_profile.get("domain_requirements", [])),
        final_score = score_breakdown.get("final_score", 0),
        skill_score = score_breakdown.get("skill_score", 0),
        exp_score   = score_breakdown.get("experience_score", 0),
        sem_score   = score_breakdown.get("semantic_score", 0),
    )

    try:
        if not is_groq_available():
            logger.info("[LLMParser] Groq unavailable — using fallback intelligence.")
            return _fallback_intelligence(candidate_profile, jd_profile, score_breakdown)

        result = llm_generate_json(prompt, temperature=0.2, max_tokens=2000)
        # Apply defaults
        result.setdefault("recommendation", "Hold")
        result.setdefault("recommendation_confidence", "Medium")
        result.setdefault("executive_summary", "Candidate evaluation completed.")
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("risks", [])
        result.setdefault("opportunities", [])
        result.setdefault("interview_focus_areas", [])
        result.setdefault("hiring_red_flags", [])
        result.setdefault("hiring_green_flags", [])
        result.setdefault("culture_fit_indicators", [])
        result.setdefault("salary_range_fit", "Mid")
        result.setdefault("onboarding_complexity", "Medium")
        result.setdefault("time_to_productivity", "1-2 weeks")
        return result

    except Exception as e:
        logger.error("[LLMParser] Groq intelligence generation failed: %s. Using fallback.", e)
        return _fallback_intelligence(candidate_profile, jd_profile, score_breakdown)


def _fallback_intelligence(
    candidate_profile: dict,
    jd_profile: dict,
    score_breakdown: dict,
) -> dict:
    """Deterministic template fallback when Groq is unavailable."""
    score = score_breakdown.get("final_score", 0)

    cand_skills = set(
        s.lower().strip()
        for s in (
            candidate_profile.get("technical_skills", [])
            + candidate_profile.get("soft_skills", [])
            + candidate_profile.get("skills", [])
        )
        if s and isinstance(s, str)
    )

    req_skills   = jd_profile.get("required_skills", [])
    matched      = [s for s in req_skills if s and s.lower().strip() in cand_skills]
    missing      = [s for s in req_skills if s and s.lower().strip() not in cand_skills]
    total_exp    = float(candidate_profile.get("total_experience_years") or 0.0)
    min_exp      = float(jd_profile.get("minimum_experience") or 0.0)
    projects     = candidate_profile.get("projects", [])
    certs        = candidate_profile.get("certifications", [])
    education    = candidate_profile.get("education", [])
    timeline     = candidate_profile.get("employment_timeline", [])
    pref_missing = [s for s in jd_profile.get("preferred_skills", []) if s and s.lower().strip() not in cand_skills]

    # Strengths
    strengths = []
    if matched:
        strengths.append(f"Demonstrates alignment with {len(matched)} required skills: {', '.join(matched[:3])}")
    elif cand_skills:
        strengths.append(f"Possesses relevant technical skills: {', '.join(list(cand_skills)[:3])}")
    else:
        strengths.append("Has baseline technical knowledge for professional workflows")

    if total_exp >= min_exp and min_exp > 0:
        strengths.append(f"Meets experience requirement: {total_exp:.1f} years (required: {min_exp:.1f} years)")
    elif total_exp > 0:
        strengths.append(f"Has {total_exp:.1f} years of professional experience")
    else:
        strengths.append("Academic and project training provides foundational knowledge")

    if projects:
        proj_names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in projects[:2]]
        strengths.append(f"Practical project experience: {', '.join(proj_names)}")
    elif certs:
        strengths.append(f"Holds professional certifications: {', '.join(certs[:2])}")
    elif education:
        degs = [e.get("degree", str(e)) if isinstance(e, dict) else str(e) for e in education[:2]]
        strengths.append(f"Relevant academic credentials: {', '.join(degs)}")
    else:
        strengths.append("Clear, structured resume presentation with verifiable background")

    # Weaknesses
    weaknesses = []
    if missing:
        weaknesses.append(f"Missing key required skills: {', '.join(missing[:3])}")
    else:
        weaknesses.append("No critical required skill gaps identified at this stage")

    if min_exp > 0 and total_exp < min_exp:
        weaknesses.append(f"Experience ({total_exp:.1f} yrs) is below the minimum requirement ({min_exp:.1f} yrs)")
    elif total_exp == 0:
        weaknesses.append("No formal employment timeline documented — verification required")
    else:
        weaknesses.append("May need alignment to team-specific tooling and workflow practices")

    if pref_missing:
        weaknesses.append(f"Missing preferred competencies: {', '.join(pref_missing[:3])}")
    elif not certs:
        weaknesses.append("No industry certifications listed to validate domain depth")
    elif not projects:
        weaknesses.append("Limited portfolio or hands-on project documentation")
    else:
        weaknesses.append("Depth of expertise in matched skills should be verified in interview")

    # Risks
    risks = []
    if missing:
        risks.append(f"Ramp-up risk due to missing skills: {', '.join(missing[:3])}")
    else:
        risks.append("No major skill dependency risks — proficiency depth to be confirmed via assessment")

    if timeline and len(timeline) >= 3 and total_exp < 4.0:
        risks.append(f"Frequent transitions ({len(timeline)} roles in {total_exp:.1f} yrs) — potential retention concern")
    elif min_exp > 0 and total_exp < min_exp * 0.6:
        risks.append(f"Significant experience gap ({total_exp:.1f} vs {min_exp:.1f} required) — extended onboarding likely")
    else:
        risks.append("Standard onboarding overhead — time-to-productivity depends on team dynamics")

    risks.append("Profile data is parser-extracted and should be cross-verified in the interview")

    if score >= 80:
        rec = "Strong Hire"
    elif score >= 65:
        rec = "Hire"
    elif score >= 45:
        rec = "Hold"
    else:
        rec = "Reject"

    return {
        "recommendation": rec,
        "recommendation_confidence": "Medium",
        "executive_summary": (
            f"{candidate_profile.get('candidate_name', 'Candidate')} has {total_exp:.1f} years of experience "
            f"with {len(matched)} of {len(req_skills)} required skills matched. "
            f"Overall AI match score: {score:.0f}%."
        ),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "opportunities": [
            "Candidate profile warrants further technical assessment",
            "Opportunity to assess domain growth potential during the interview",
            "Current skillset may contribute to team projects immediately",
        ],
        "interview_focus_areas": [f"Assess proficiency in {s}" for s in missing[:3]] or [
            "General technical assessment",
            "Core domain skill depth",
            "Team collaboration approach",
        ],
        "hiring_red_flags": [],
        "hiring_green_flags": [f"Has {s}" for s in matched[:3]] or ["Relevant background for initial screening"],
        "culture_fit_indicators": ["Professional resume presentation", "Structured career documentation"],
        "salary_range_fit": "Senior" if total_exp >= 8 else "Mid" if total_exp >= 3 else "Junior",
        "onboarding_complexity": "Easy" if score >= 75 else "Medium" if score >= 50 else "Complex",
        "time_to_productivity": (
            "Immediate" if score >= 80
            else "1-2 weeks" if score >= 65
            else "1 month" if score >= 48
            else "2-3 months"
        ),
    }


# ── Local Fallbacks ──────────────────────────────────────────────────────────
def parse_resume_local_fallback(raw_text: str, filename: str) -> dict:
    """Local fallback parser using regex and spaCy patterns."""
    try:
        from resume_parser import (
            extract_candidate_details, extract_skills, extract_experience_years,
            extract_education, extract_certifications, extract_projects, extract_location,
        )
        details      = extract_candidate_details(raw_text, filename)
        skills       = extract_skills(raw_text)
        experience   = extract_experience_years(raw_text)
        education    = [{"degree": e, "institution": "", "year": "", "field": ""} for e in extract_education(raw_text)]
        certifications = extract_certifications(raw_text)
        projects     = [{"name": p, "description": "", "technologies": []} for p in extract_projects(raw_text)]
        location     = extract_location(raw_text)
    except Exception as e:
        logger.error("[LLMParser] Local fallback parse error: %s", e)
        return {**_RESUME_DEFAULTS, "candidate_name": filename.split(".")[0], "confidence_score": 40.0, "extraction_reliability": "Low"}

    soft_db  = {"communication", "leadership", "teamwork", "problem solving", "management", "agile", "scrum"}
    soft     = [s for s in skills if s in soft_db]
    tech     = [s for s in skills if s not in soft_db]

    timeline = []
    if experience > 0:
        timeline.append({
            "company": "Previous Employment", "title": "Professional Role",
            "start_date": "N/A", "end_date": "N/A",
            "duration_months": int(experience * 12), "description": "",
            "is_internship": False, "is_freelance": False,
        })

    return {
        **_RESUME_DEFAULTS,
        "candidate_name":   details.get("name", filename.split(".")[0]),
        "email":            details.get("email", ""),
        "phone":            details.get("phone", ""),
        "location":         location,
        "total_experience_years": experience,
        "technical_skills": tech,
        "soft_skills":      soft,
        "certifications":   certifications,
        "education":        education,
        "projects":         projects,
        "employment_timeline": timeline,
        "technologies":     tech,
        "leadership_experience": "leadership" in skills or "management" in skills,
        "confidence_score": 60.0,
        "ambiguity_detection": ["Extracted via regex fallback — manual review recommended"],
        "extraction_reliability": "Low",
    }


def parse_jd_local_fallback(jd_text: str) -> dict:
    """Local fallback parser for job descriptions."""
    try:
        from resume_parser import extract_skills, extract_experience_years
    except ImportError:
        return {**_JD_DEFAULTS}

    exp = extract_experience_years(jd_text)
    soft_db = {"communication", "leadership", "teamwork", "problem solving", "management"}

    preferred_re = re.compile(
        r"\b(nice\s+to\s+have|preferred|bonus|plus|good\s+to\s+have|desired|advantageous|optionally?)\b",
        re.IGNORECASE,
    )
    required_re = re.compile(
        r"\b(required|must\s+have|mandatory|essential|minimum\s+requirements?|qualifications?|responsibilities?|requirements?)\b",
        re.IGNORECASE,
    )

    lines = jd_text.split("\n")
    req_lines, pref_lines = [], []
    in_pref = False
    for line in lines:
        if preferred_re.search(line):
            in_pref = True
        elif required_re.search(line):
            in_pref = False
        if in_pref:
            pref_lines.append(line)
        else:
            req_lines.append(line)

    req_text  = " ".join(req_lines)
    pref_text = " ".join(pref_lines)

    all_skills  = extract_skills(jd_text)
    req_skills  = [s for s in extract_skills(req_text)  if s not in soft_db]
    pref_skills = [s for s in extract_skills(pref_text) if s not in soft_db]

    if not req_skills:
        req_skills = [s for s in all_skills if s not in soft_db]

    return {
        **_JD_DEFAULTS,
        "minimum_experience": exp,
        "required_skills":    req_skills[:20],
        "preferred_skills":   pref_skills[:10],
    }
