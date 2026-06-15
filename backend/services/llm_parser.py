import os
import json
import re
import logging
import time
from typing import Optional
from services.ollama_client import ollama_generate_sync

logger = logging.getLogger(__name__)

def safe_json_loads(text: str) -> dict:
    """Safely extracts and parses JSON block from text."""
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception as e:
        logger.error(f"[LLMParser] JSON parse error: {e}. Raw text: {text}")
        raise

def get_rate_limit_sleep_time(err_msg: str) -> Optional[float]:
    err_msg_lower = err_msg.lower()
    # Pattern 1: Please try again in X.XXs
    m_sec = re.search(r'try again in (\d+(?:\.\d+)?)\s*s', err_msg_lower)
    if m_sec:
        return float(m_sec.group(1))
    # Pattern 2: Please try again in XXXms
    m_ms = re.search(r'try again in (\d+(?:\.\d+)?)\s*ms', err_msg_lower)
    if m_ms:
        return float(m_ms.group(1)) / 1000.0
    return None

# ── Groq stubs kept for import compatibility with matching.py ──────────────
_groq_rate_limited_until: float = 0.0
_model_rate_limits = {}
_groq_rate_limited = False

def _is_groq_rate_limited() -> bool: return False
def _set_groq_rate_limited(duration_seconds: int = 300): pass
def _is_model_rate_limited(model_name: str) -> bool: return False
def _set_model_rate_limited(model_name: str, duration: int = 600): pass
def get_groq_client(): return None  # Always returns None — Ollama used instead
# ─────────────────────────────────────────────────────────────────────────────


def parse_resume_with_llm(raw_text: str, filename: str) -> dict:
    """
    Parses a resume using Mistral 7B via local Ollama.
    NEVER invents, assumes, or hallucinates any field. Every value must be directly
    observed in the resume text.
    Cost: ₹0 — runs on local hardware.
    """

    prompt = f"""You are a resume extraction engine. Extract ONLY what is explicitly written.
Your task is to extract ONLY what is explicitly written in the resume text below.

CRITICAL EXTRACTION RULES:
1. NEVER invent, infer, guess, or hallucinate any data — not skills, not companies, not dates.
2. If a field is not present in the resume, use empty values: "" / [] / 0.0 / false.
3. Extract skills ONLY from explicit mentions in the resume. Do not add skills based on company name or role title.
4. For technical_skills: extract ALL skills from "Skills", "Key Skills", "Technical Skills", "Core Competencies", "Areas of Expertise" sections. Be comprehensive — include every tool, language, platform, framework listed.
5. For soft_skills: only include if candidate explicitly writes them (leadership, communication, etc).
6. Employment timeline MUST match actual companies/dates written. If ambiguous, flag in ambiguity_detection.
7. For education: extract the EXACT degree name, institution, and year as written.
8. For projects: extract actual project titles/descriptions as written, NOT invented summaries.
9. For certifications: only include if the candidate explicitly lists a certification by name.
10. candidate_name: Extract the PERSON's FULL NAME from the VERY TOP of the resume (usually largest/first text).
    - It is typically 2-4 proper noun words (First Last or First Middle Last).
    - REJECT any line that is a job title, role designation, or social platform text.
    - If the PDF contains "Link Edin", "LinkedIn", "GitHub", "Twitter" near the top — IGNORE those lines entirely.
    - If name is unclear, derive from the email username (e.g. monosmitb@gmail.com → "Monosmit B").
11. total_experience_years: Calculate by summing employment date ranges from the Work Experience section. Also check explicit statements (e.g., "9+ years of experience"). Return as a float.
12. confidence_score: your self-assessment 0-100 of extraction accuracy for this resume.
13. extraction_reliability: "High" if resume is clearly structured, "Medium" if partially unclear, "Low" if very noisy.

Return ONLY this exact JSON (no explanation, no markdown):
{{
  "candidate_name": "string",
  "email": "string or empty",
  "phone": "string or empty",
  "location": "string or empty",
  "total_experience_years": 0.0,
  "current_title": "string or empty",
  "companies": ["string"],
  "job_titles": ["string"],
  "technical_skills": ["string (lowercase, canonical)"],
  "soft_skills": ["string (lowercase)"],
  "certifications": ["string (exact name as in resume)"],
  "education": [
    {{
      "degree": "string",
      "institution": "string",
      "year": "string or empty",
      "field": "string or empty"
    }}
  ],
  "projects": [
    {{
      "name": "string",
      "description": "string (1-2 sentences max, directly from resume)",
      "technologies": ["string"]
    }}
  ],
  "employment_timeline": [
    {{
      "company": "string",
      "title": "string",
      "start_date": "string (e.g. Jan 2020 or 2020)",
      "end_date": "string (e.g. Mar 2023 or Present)",
      "duration_months": 0,
      "description": "string (brief role summary from resume)",
      "is_internship": false,
      "is_freelance": false
    }}
  ],
  "leadership_experience": false,
  "domain_experience": ["string"],
  "communication_indicators": ["string"],
  "tools": ["string"],
  "technologies": ["string"],
  "languages_spoken": ["string"],
  "awards_achievements": ["string"],
  "github_url": "string or empty",
  "linkedin_url": "string or empty",
  "portfolio_url": "string or empty",
  "summary_or_objective": "string (candidate's own written summary, verbatim or paraphrased closely)",
  "confidence_score": 0.0,
  "ambiguity_detection": ["string"],
  "extraction_reliability": "High"
}}

RESUME TEXT:
{raw_text[:8000]}
"""

    parsed = ollama_generate_sync(prompt, temperature=0.0, max_tokens=1000, expect_json=True)
    if not parsed:
        logger.warning("[LLMParser] Ollama resume parse failed or unavailable. Using local fallback.")
        return parse_resume_local_fallback(raw_text, filename)

    # Normalize / fill defaults
    parsed.setdefault("candidate_name", filename.split(".")[0])
    parsed.setdefault("email", "")
    parsed.setdefault("phone", "")
    parsed.setdefault("location", "")
    parsed.setdefault("total_experience_years", 0.0)
    parsed.setdefault("current_title", "")
    parsed.setdefault("companies", [])
    parsed.setdefault("job_titles", [])
    parsed.setdefault("technical_skills", [])
    parsed.setdefault("soft_skills", [])
    parsed.setdefault("certifications", [])
    parsed.setdefault("education", [])
    parsed.setdefault("projects", [])
    parsed.setdefault("employment_timeline", [])
    parsed.setdefault("leadership_experience", False)
    parsed.setdefault("domain_experience", [])
    parsed.setdefault("communication_indicators", [])
    parsed.setdefault("tools", [])
    parsed.setdefault("technologies", [])
    parsed.setdefault("languages_spoken", [])
    parsed.setdefault("awards_achievements", [])
    parsed.setdefault("github_url", "")
    parsed.setdefault("linkedin_url", "")
    parsed.setdefault("portfolio_url", "")
    parsed.setdefault("summary_or_objective", "")
    parsed.setdefault("confidence_score", 70.0)
    parsed.setdefault("ambiguity_detection", [])
    parsed.setdefault("extraction_reliability", "Medium")

    return parsed


def parse_jd_with_llm(jd_text: str) -> dict:
    """
    Parses a Job Description using Mistral 7B via local Ollama.
    Extracts only what is explicitly in the JD — zero hallucination.
    Cost: ₹0 — runs on local hardware.
    """

    prompt = f"""You are an elite Job Description parser with zero-hallucination policy.
Extract ONLY requirements explicitly stated in the job description below.

RULES:
1. required_skills: ONLY skills explicitly listed under "required", "must have", "qualifications", "responsibilities". No inferences.
2. preferred_skills: ONLY skills under "preferred", "nice to have", "bonus", "good to have". No inferences.
3. minimum_experience: Extract the number from phrases like "5+ years" or "minimum 3 years". If not stated, use 0.
4. certifications_required: Only if explicitly mentioned as required.
5. Do NOT add skills based on job title alone.
6. domain_requirements: infer domain from job description context (e.g. "fintech", "healthcare", "e-commerce").

Return ONLY this exact JSON:
{{
  "role_name": "string",
  "minimum_experience": 0.0,
  "required_skills": ["string (lowercase canonical)"],
  "preferred_skills": ["string (lowercase canonical)"],
  "domain_requirements": ["string"],
  "leadership_required": false,
  "communication_required": false,
  "certifications_required": ["string"],
  "project_requirements": ["string"],
  "management_requirements": ["string"],
  "key_responsibilities": ["string (top 5 responsibilities as listed)"],
  "benefits": ["string"]
}}

JOB DESCRIPTION:
{jd_text}
"""

    parsed = ollama_generate_sync(prompt, temperature=0.0, max_tokens=1000, expect_json=True)
    if not parsed:
        logger.warning("[LLMParser] Ollama JD parse failed or unavailable. Using local fallback.")
        return parse_jd_local_fallback(jd_text)

    parsed.setdefault("role_name", "Software Engineer")
    parsed.setdefault("minimum_experience", 0.0)
    parsed.setdefault("required_skills", [])
    parsed.setdefault("preferred_skills", [])
    parsed.setdefault("domain_requirements", [])
    parsed.setdefault("leadership_required", False)
    parsed.setdefault("communication_required", False)
    parsed.setdefault("certifications_required", [])
    parsed.setdefault("project_requirements", [])
    parsed.setdefault("management_requirements", [])
    parsed.setdefault("key_responsibilities", [])
    parsed.setdefault("benefits", [])

    return parsed


def generate_candidate_intelligence(candidate_profile: dict, jd_profile: dict, score_breakdown: dict) -> dict:
    """
    Generate AI-powered candidate intelligence report using Mistral 7B via Ollama.
    Cost: ₹0 — runs on local hardware.
    """

    prompt = f"""You are a world-class senior technical recruiter with 20+ years experience at top tech companies.
Analyze this candidate profile against the job requirements and generate an elite-level recruiter intelligence report.

IMPORTANT: Base your analysis STRICTLY on the data provided. Do not invent skills or experiences not shown.

CANDIDATE PROFILE:
Name: {candidate_profile.get('candidate_name', 'Unknown')}
Experience: {candidate_profile.get('total_experience_years', 0)} years
Current Title: {candidate_profile.get('current_title', 'N/A')}
Technical Skills: {', '.join(candidate_profile.get('technical_skills', [])[:20])}
Soft Skills: {', '.join(candidate_profile.get('soft_skills', [])[:10])}
Education: {json.dumps(candidate_profile.get('education', [])[:3])}
Certifications: {', '.join(candidate_profile.get('certifications', [])[:5])}
Companies: {', '.join(candidate_profile.get('companies', [])[:5])}
Job Titles: {', '.join(candidate_profile.get('job_titles', [])[:5])}
Projects: {json.dumps(candidate_profile.get('projects', [])[:4])}
Domain Experience: {', '.join(candidate_profile.get('domain_experience', [])[:5])}
Leadership: {candidate_profile.get('leadership_experience', False)}

JOB REQUIREMENTS:
Role: {jd_profile.get('role_name', 'N/A')}
Required Skills: {', '.join(jd_profile.get('required_skills', [])[:20])}
Preferred Skills: {', '.join(jd_profile.get('preferred_skills', [])[:10])}
Min Experience: {jd_profile.get('minimum_experience', 0)} years
Domain: {', '.join(jd_profile.get('domain_requirements', []))}

MATCH SCORES:
Overall: {score_breakdown.get('final_score', 0):.1f}%
Skills: {score_breakdown.get('skill_score', 0):.1f}%
Experience: {score_breakdown.get('experience_score', 0):.1f}%
Semantic: {score_breakdown.get('semantic_score', 0):.1f}%

Return ONLY this exact JSON (no markdown, no explanation).
CRITICAL: You MUST provide AT LEAST 3 detailed, evidence-based strengths, AT LEAST 3 detailed weaknesses/gaps, and AT LEAST 3 detailed hiring risks in their respective arrays. Do not return empty arrays or fewer than 3 elements under any circumstance.

{{
  "recommendation": "Strong Hire | Hire | Hold | Reject",
  "recommendation_confidence": "High | Medium | Low",
  "executive_summary": "3-4 sentence professional assessment of this candidate for this specific role. Be specific and evidence-based.",
  "strengths": [
    "Specific strength with evidence from their profile (e.g. '5+ years Python + FastAPI, directly matching backend stack requirement')",
    "Another specific, evidence-based strength",
    "Third specific, evidence-based strength"
  ],
  "weaknesses": [
    "Specific gap or concern with context (e.g. 'No cloud experience (AWS/GCP) — required for this role')",
    "Another specific concern",
    "Third specific concern"
  ],
  "risks": [
    "Specific hiring risk (e.g. 'Frequent job changes — 4 companies in 3 years may indicate instability')",
    "Another risk if applicable",
    "Third risk if applicable"
  ],
  "opportunities": [
    "Growth potential or upside (e.g. 'Strong ML background could expand into AI features the team is planning')",
    "Another opportunity"
  ],
  "interview_focus_areas": [
    "Specific technical area to probe in interview",
    "Another focus area",
    "Another focus area"
  ],
  "hiring_red_flags": ["string or empty list"],
  "hiring_green_flags": ["string or empty list"],
  "culture_fit_indicators": ["string or empty list"],
  "salary_range_fit": "Senior | Mid | Junior | Executive",
  "onboarding_complexity": "Easy | Medium | Complex",
  "time_to_productivity": "Immediate | 1-2 weeks | 1 month | 2-3 months"
}}
"""

    result = ollama_generate_sync(prompt, temperature=0.2, max_tokens=1000, expect_json=True)
    if not result:
        logger.warning("[LLMParser] Ollama candidate intelligence generation failed. Using fallback.")
        return _fallback_intelligence(candidate_profile, jd_profile, score_breakdown)

    # Set defaults
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


def _fallback_intelligence(candidate_profile: dict, jd_profile: dict, score_breakdown: dict) -> dict:
    """Fallback when Ollama is unavailable."""
    score = score_breakdown.get("final_score", 0)
    
    # Consolidate all candidate skills just like in matching.py
    cand_skills_list = []
    if candidate_profile.get("technical_skills"):
        cand_skills_list.extend(candidate_profile.get("technical_skills", []))
    if candidate_profile.get("soft_skills"):
        cand_skills_list.extend(candidate_profile.get("soft_skills", []))
    if not cand_skills_list and candidate_profile.get("skills"):
        cand_skills_list.extend(candidate_profile.get("skills", []))
        
    cand_skills_normalized = {s.lower().strip() for s in cand_skills_list if s and isinstance(s, str)}
    
    req_skills = jd_profile.get("required_skills", [])
    
    # Case-insensitive comparison, preserving original required skill casing in matched/missing lists
    missing = [s for s in req_skills if s and isinstance(s, str) and s.lower().strip() not in cand_skills_normalized]
    matched = [s for s in req_skills if s and isinstance(s, str) and s.lower().strip() in cand_skills_normalized]

    # STRENGTHS generation (ensure at least 3 distinct items)
    strengths = []
    # Strength 1: Skill alignment
    if matched:
        strengths.append(f"Demonstrates alignment with {len(matched)} key required skills: {', '.join(matched[:3])}")
    elif cand_skills_list:
        strengths.append(f"Possesses relevant technical skills: {', '.join(cand_skills_list[:3])}")
    else:
        strengths.append("Possesses baseline technical skills for professional workflows")

    # Strength 2: Experience
    total_exp = float(candidate_profile.get('total_experience_years') or 0.0)
    min_exp = float(jd_profile.get('minimum_experience') or 0.0)
    if total_exp >= min_exp and min_exp > 0:
        strengths.append(f"Meets or exceeds the experience requirement with {total_exp:.1f} years of experience (required: {min_exp:.1f} years)")
    elif total_exp > 0:
        strengths.append(f"Has {total_exp:.1f} years of professional experience in technical/professional roles")
    else:
        strengths.append("Shows academic and practical training in candidate domain")

    # Strength 3: Education/Projects/Certifications
    projects = candidate_profile.get("projects", [])
    certs = candidate_profile.get("certifications", [])
    education = candidate_profile.get("education", [])
    if projects:
        proj_names = [p.get('name') if isinstance(p, dict) else str(p) for p in projects]
        strengths.append(f"Practical project experience including: {', '.join(proj_names[:2])}")
    elif certs:
        strengths.append(f"Holds professional certifications: {', '.join(certs[:2])}")
    elif education:
        edu_degs = [e.get('degree') if isinstance(e, dict) else str(e) for e in education]
        strengths.append(f"Completed relevant credentials: {', '.join(edu_degs[:2])}")
    else:
        strengths.append("Clear layout and structured documentation of candidate background")

    # WEAKNESSES generation (ensure at least 3 distinct items)
    weaknesses = []
    # Weakness 1: Missing skills
    if missing:
        weaknesses.append(f"Missing key required skills for this role: {', '.join(missing[:3])}")
    else:
        weaknesses.append("No critical required skill gaps identified")

    # Weakness 2: Experience Gap
    if min_exp > 0 and total_exp < min_exp:
        weaknesses.append(f"Experience level ({total_exp:.1f} years) is below the requested minimum of {min_exp:.1f} years")
    elif total_exp == 0:
        weaknesses.append("No formal employment timeline or industry experience documented")
    else:
        weaknesses.append("May require initial alignment to adapt past experience to this team's exact stack")

    # Weakness 3: Preferred skills gap or certs/projects gap
    pref_skills = jd_profile.get("preferred_skills", [])
    pref_missing = [s for s in pref_skills if s and isinstance(s, str) and s.lower().strip() not in cand_skills_normalized]
    if pref_missing:
        weaknesses.append(f"Missing preferred / nice-to-have competencies: {', '.join(pref_missing[:3])}")
    elif not certs:
        weaknesses.append("No specialized industry certifications listed to validate domain skills")
    elif not projects:
        weaknesses.append("Limited documented hands-on projects or portfolio items")
    else:
        weaknesses.append("Limited exposure to advanced or secondary domain tools")

    # RISKS generation (ensure at least 3 distinct items)
    risks = []
    # Risk 1: Skill coverage
    if missing:
        risks.append(f"Potential ramp-up delay due to missing skillsets: {', '.join(missing[:3])}")
    else:
        risks.append("No major skill dependency risks flagged")

    # Risk 2: Tenure / Onboarding risk
    timeline = candidate_profile.get("employment_timeline", [])
    if timeline and len(timeline) >= 3 and total_exp < 4.0:
        risks.append("Frequent employment transitions in a short timeframe may indicate retention risk")
    elif min_exp > 0 and total_exp < min_exp * 0.5:
        risks.append(f"Significant experience gap ({total_exp:.1f} vs required {min_exp:.1f} years) could require heavy mentoring")
    else:
        risks.append("Standard onboarding overhead for adjusting to a new environment and company processes")

    # Risk 3: Verification
    risks.append("Assessment is based on automated parser results; claims should be verified in interview")

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
        "executive_summary": f"Candidate has {total_exp:.1f} years experience with {len(matched)} of {len(req_skills)} required skills matched.",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "opportunities": [
            "Candidate profile warrants further technical assessment",
            "Potential to develop domain skills through hands-on role execution",
            "Opportunity to contribute to team projects using current skillset"
        ],
        "interview_focus_areas": [f"Assess proficiency in {s}" for s in missing[:3]] or ["General technical assessment", "Core coding skills", "Team collaboration"],
        "hiring_red_flags": [],
        "hiring_green_flags": [f"Has {s}" for s in matched[:3]] if matched else ["Shows relevant background"],
        "culture_fit_indicators": ["Professional presentation", "Structured resume representation"],
        "salary_range_fit": "Mid",
        "onboarding_complexity": "Medium",
        "time_to_productivity": "1-2 weeks",
    }


def parse_resume_local_fallback(raw_text: str, filename: str) -> dict:
    """Local fallback parser using regex/spaCy patterns."""
    from resume_parser import (
        extract_candidate_details, extract_skills, extract_experience_years,
        extract_education, extract_certifications, extract_projects, extract_location
    )
    details = extract_candidate_details(raw_text, filename)
    skills = extract_skills(raw_text)
    experience_yrs = extract_experience_years(raw_text)
    education_raw = extract_education(raw_text)
    certifications = extract_certifications(raw_text)
    projects_raw = extract_projects(raw_text)
    location = extract_location(raw_text)

    # Convert raw education list to structured format
    education = [{"degree": e, "institution": "", "year": "", "field": ""} for e in education_raw]
    # Convert raw project list to structured format
    projects = [{"name": p, "description": "", "technologies": []} for p in projects_raw]

    soft_skills_db = ["communication", "leadership", "teamwork", "problem solving", "management", "agile", "scrum"]
    soft_skills = [s for s in soft_skills_db if s in skills]
    tech_skills = [s for s in skills if s not in soft_skills]

    timeline = []
    if experience_yrs > 0:
        timeline.append({
            "company": "Previous Employment",
            "title": "Professional Role",
            "start_date": "N/A",
            "end_date": "N/A",
            "duration_months": int(experience_yrs * 12),
            "description": "",
            "is_internship": False,
            "is_freelance": False
        })

    return {
        "candidate_name": details.get("name", filename.split(".")[0]),
        "email": details.get("email", ""),
        "phone": details.get("phone", ""),
        "location": location,
        "total_experience_years": experience_yrs,
        "current_title": "",
        "companies": [],
        "job_titles": [],
        "technical_skills": tech_skills,
        "soft_skills": soft_skills,
        "certifications": certifications,
        "education": education,
        "projects": projects,
        "employment_timeline": timeline,
        "leadership_experience": "leadership" in skills or "management" in skills,
        "domain_experience": [],
        "communication_indicators": ["standard written format"],
        "tools": [],
        "technologies": tech_skills,
        "languages_spoken": [],
        "awards_achievements": [],
        "github_url": "",
        "linkedin_url": "",
        "portfolio_url": "",
        "summary_or_objective": "",
        "confidence_score": 60.0,
        "ambiguity_detection": ["extracted via regex parsing fallback — manual review recommended"],
        "extraction_reliability": "Low"
    }


def parse_jd_local_fallback(jd_text: str) -> dict:
    """Local fallback parser for job description."""
    from resume_parser import extract_skills, extract_experience_years
    import re
    exp = extract_experience_years(jd_text)
    soft_skills_db = {"communication", "leadership", "teamwork", "problem solving", "management"}

    preferred_markers = re.compile(
        r'\b(nice\s+to\s+have|preferred|bonus|plus|good\s+to\s+have|desired|'
        r'advantageous|optionally?|would\s+be\s+a\s+plus)\b',
        re.IGNORECASE
    )
    required_markers = re.compile(
        r'\b(required|must\s+have|mandatory|essential|minimum\s+requirements?|'
        r'qualifications?|responsibilities|requirements?)\b',
        re.IGNORECASE
    )

    lines = jd_text.split('\n')
    required_lines, preferred_lines = [], []
    current_sec = "required"

    for line in lines:
        if preferred_markers.search(line):
            current_sec = "preferred"
        elif required_markers.search(line):
            current_sec = "required"
        if current_sec == "preferred":
            preferred_lines.append(line)
        else:
            required_lines.append(line)

    req_text = "\n".join(required_lines)
    pref_text = "\n".join(preferred_lines)
    req_skills = [s for s in extract_skills(req_text) if s not in soft_skills_db]
    pref_skills = [s for s in extract_skills(pref_text) if s not in soft_skills_db and s not in req_skills]
    if not req_skills:
        all_skills = extract_skills(jd_text)
        req_skills = [s for s in all_skills if s not in soft_skills_db]

    all_skills_for_flags = extract_skills(jd_text)
    return {
        "role_name": "Job Role",
        "minimum_experience": exp,
        "required_skills": req_skills,
        "preferred_skills": pref_skills,
        "domain_requirements": [],
        "leadership_required": "leadership" in all_skills_for_flags or "management" in all_skills_for_flags,
        "communication_required": "communication" in all_skills_for_flags,
        "certifications_required": [],
        "project_requirements": [],
        "management_requirements": [],
        "key_responsibilities": [],
        "benefits": [],
    }
