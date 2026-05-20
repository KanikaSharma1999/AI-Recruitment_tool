import os
import json
import re
import logging
from groq import Groq

logger = logging.getLogger(__name__)

def safe_json_loads(text: str) -> dict:
    """Safely extracts and parses JSON block from text."""
    try:
        # Search for first { and last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception as e:
        logger.error(f"[LLMParser] JSON parse error: {e}. Raw text: {text}")
        raise

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "your_groq_key" in api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"[LLMParser] Failed to initialize Groq client: {e}")
        return None

def parse_resume_with_llm(raw_text: str, filename: str) -> dict:
    """
    Parses a resume using Groq Llama 3.3 70B into a structured JSON profile.
    If LLM fails, falls back to a clean local parsing dictionary.
    """
    client = get_groq_client()
    if not client:
        logger.info("[LLMParser] Groq client not configured. Using local parser fallback.")
        return parse_resume_local_fallback(raw_text, filename)

    prompt = f"""You are a professional recruiting coordinator. Extract structured candidate profiles from resumes.
Analyze the following resume text and output a valid JSON object matching the exact schema below.

Rules:
1. DO NOT invent or hallucinate any fields, companies, dates, or skills.
2. If any field or timeline is uncertain, set the confidence to low or list under ambiguity_detection.
3. If a value is unknown, use default empty values (e.g. empty lists, empty strings, false).
4. For employment_timeline:
   - Calculate duration of each job (e.g. in months or fractional years).
   - Classify as internship (is_internship: true/false) or freelance (is_freelance: true/false) based on terms like 'Intern', 'Contractor', 'Freelance'.
   - Avoid double-counting overlapping jobs.

JSON Schema to return:
{{
  "candidate_name": "string (Candidate Full Name)",
  "total_experience_years": 0.0,
  "companies": ["string"],
  "job_titles": ["string"],
  "technical_skills": ["string (lowercase canonical)"],
  "soft_skills": ["string (lowercase canonical)"],
  "certifications": ["string"],
  "education": ["string (e.g. Bachelor of Science in Computer Science)"],
  "projects": ["string (Project name or brief title)"],
  "leadership_experience": true/false,
  "domain_experience": ["string (e.g. Fintech, Healthcare, Cloud)"],
  "communication_indicators": ["string (e.g. 'clear written structure', 'strong presentation markers')"],
  "employment_timeline": [
    {{
      "company": "string",
      "title": "string",
      "start_date": "string (e.g. Jan 2018)",
      "end_date": "string (e.g. Present)",
      "duration_months": 0,
      "is_internship": true/false,
      "is_freelance": true/false
    }}
  ],
  "tools": ["string"],
  "technologies": ["string"],
  "confidence_score": 0.0,
  "ambiguity_detection": ["string"],
  "extraction_reliability": "High/Medium/Low"
}}

Resume Text:
{raw_text[:12000]}

Response:
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        response_text = completion.choices[0].message.content
        parsed = safe_json_loads(response_text)
        
        # Validate critical fields
        parsed.setdefault("candidate_name", filename.split(".")[0])
        parsed.setdefault("total_experience_years", 0.0)
        parsed.setdefault("companies", [])
        parsed.setdefault("job_titles", [])
        parsed.setdefault("technical_skills", [])
        parsed.setdefault("soft_skills", [])
        parsed.setdefault("certifications", [])
        parsed.setdefault("education", [])
        parsed.setdefault("projects", [])
        parsed.setdefault("leadership_experience", False)
        parsed.setdefault("domain_experience", [])
        parsed.setdefault("communication_indicators", [])
        parsed.setdefault("employment_timeline", [])
        parsed.setdefault("tools", [])
        parsed.setdefault("technologies", [])
        parsed.setdefault("confidence_score", 85.0)
        parsed.setdefault("ambiguity_detection", [])
        parsed.setdefault("extraction_reliability", "High")
        
        return parsed
    except Exception as e:
        logger.error(f"[LLMParser] LLM Resume Parsing failed: {e}. Falling back to local.")
        return parse_resume_local_fallback(raw_text, filename)

def parse_jd_with_llm(jd_text: str) -> dict:
    """
    Parses a Job Description using Groq Llama 3.3 70B into structured hiring requirements.
    If LLM fails, falls back to a clean local parsing dictionary.
    """
    client = get_groq_client()
    if not client:
        logger.info("[LLMParser] Groq client not configured. Using local parser fallback.")
        return parse_jd_local_fallback(jd_text)

    prompt = f"""You are a professional recruiting coordinator. Parse Job Descriptions into structured hiring requirements.
Analyze the following Job Description and output a valid JSON object matching the exact schema below.

Rules:
1. Extract minimum experience years requested.
2. Group skills into required_skills and preferred_skills.
3. Identify domain, leadership, communication, certifications, project, and management requirements.
4. DO NOT invent requirements. If not explicitly requested, keep them empty.

JSON Schema to return:
{{
  "role_name": "string (e.g. Senior Software Engineer)",
  "minimum_experience": 0.0,
  "required_skills": ["string (lowercase canonical)"],
  "preferred_skills": ["string (lowercase canonical)"],
  "domain_requirements": ["string"],
  "leadership_required": true/false,
  "communication_required": true/false,
  "certifications_required": ["string"],
  "project_requirements": ["string"],
  "management_requirements": ["string"]
}}

Job Description:
{jd_text}

Response:
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        response_text = completion.choices[0].message.content
        parsed = safe_json_loads(response_text)
        
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
        
        return parsed
    except Exception as e:
        logger.error(f"[LLMParser] LLM JD Parsing failed: {e}. Falling back to local.")
        return parse_jd_local_fallback(jd_text)

def parse_resume_local_fallback(raw_text: str, filename: str) -> dict:
    """Local fallback parser using regex/spaCy patterns."""
    from resume_parser import (
        extract_candidate_details, extract_skills, extract_experience_years,
        extract_education, extract_certifications, extract_projects
    )
    details = extract_candidate_details(raw_text, filename)
    skills = extract_skills(raw_text)
    experience_yrs = extract_experience_years(raw_text)
    education = extract_education(raw_text)
    certifications = extract_certifications(raw_text)
    projects = extract_projects(raw_text)
    
    # Heuristics for soft skills, tools, and technologies
    soft_skills_db = ["communication", "leadership", "teamwork", "problem solving", "management", "agile", "scrum"]
    soft_skills = [s for s in soft_skills_db if s in skills]
    tech_skills = [s for s in skills if s not in soft_skills]
    
    # Overlapping years fallback logic
    timeline = []
    if experience_yrs > 0:
        timeline.append({
            "company": "Company / Experience Section",
            "title": "Professional Position",
            "start_date": "N/A",
            "end_date": "N/A",
            "duration_months": int(experience_yrs * 12),
            "is_internship": False,
            "is_freelance": False
        })
        
    return {
        "candidate_name": details.get("name", filename.split(".")[0]),
        "total_experience_years": experience_yrs,
        "companies": ["Company"] if experience_yrs > 0 else [],
        "job_titles": ["Engineer"] if experience_yrs > 0 else [],
        "technical_skills": tech_skills,
        "soft_skills": soft_skills,
        "certifications": certifications,
        "education": education,
        "projects": projects,
        "leadership_experience": "leadership" in skills or "management" in skills,
        "domain_experience": [],
        "communication_indicators": ["standard written format"],
        "employment_timeline": timeline,
        "tools": [],
        "technologies": tech_skills,
        "confidence_score": 75.0,
        "ambiguity_detection": ["extracted via regex parsing fallback"],
        "extraction_reliability": "Medium"
    }

def parse_jd_local_fallback(jd_text: str) -> dict:
    """Local fallback parser for job description."""
    from resume_parser import extract_skills, extract_experience_years
    skills = extract_skills(jd_text)
    exp = extract_experience_years(jd_text)
    
    # Soft skills filter
    soft_skills_db = ["communication", "leadership", "teamwork", "problem solving", "management"]
    required_skills = [s for s in skills if s not in soft_skills_db]
    
    return {
        "role_name": "Job Role",
        "minimum_experience": exp,
        "required_skills": required_skills,
        "preferred_skills": [],
        "domain_requirements": [],
        "leadership_required": "leadership" in skills or "management" in skills,
        "communication_required": "communication" in skills,
        "certifications_required": [],
        "project_requirements": [],
        "management_requirements": []
    }
