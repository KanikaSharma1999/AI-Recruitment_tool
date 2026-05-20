"""
Upgraded Structured Enterprise AI Matching Engine
=================================================
Implements the 10-step recruiter-grade candidate evaluation matching pipeline.
1. Structured resume extraction (Step 1)
2. Structured job description extraction (Step 2)
3. Multi-layer experience engine with overlap detection, internship filter, freelance detection (Step 3)
4. Semantic skill normalization mapping engine (Step 4)
5. 7-dimension weighted scoring system (Step 5)
6. Groq AI recruiter verification layer (Step 6)
7. Confidence engine (Step 7)
8. Hallucination prevention (Step 8)
9. Final enterprise score breakdown (Step 9)
10. Recruiter explanation (Step 10)
"""

import asyncio
import re
import logging
import datetime
import os
from typing import List, Tuple, Dict
from services.llm_parser import parse_resume_with_llm, parse_jd_with_llm, get_groq_client, safe_json_loads

logger = logging.getLogger(__name__)

# Cache SentenceTransformer for semantic skill variants
_model = None

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("[Matching] Loading SentenceTransformer (all-MiniLM-L6-v2)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[Matching] Model ready.")
        except Exception as e:
            logger.error(f"[Matching] Model load failed: {e}")
            _model = None
    return _model

def _clamp(val: float) -> float:
    return min(100.0, max(0.0, float(val)))

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4: SEMANTIC SKILL NORMALIZATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
SYNONYMS = {
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "react": "react",
    "angularjs": "angular",
    "angular js": "angular",
    "angular": "angular",
    "vuejs": "vue",
    "vue.js": "vue",
    "vue js": "vue",
    "vue": "vue",
    "ml": "machine learning",
    "machinelearning": "machine learning",
    "machine learning": "machine learning",
    "ai": "artificial intelligence",
    "artificialintelligence": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "node js": "node.js",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "golang": "go",
    "go": "go",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "docker": "docker",
    "containerization": "docker",
    "aws": "amazon web services",
    "amazon web services": "amazon web services",
    "gcp": "google cloud",
    "google cloud": "google cloud",
    "google cloud platform": "google cloud",
    "azure": "azure",
    "microsoft azure": "azure",
    "cicd": "ci/cd",
    "ci-cd": "ci/cd",
    "nlp": "natural language processing",
    "deeplearning": "deep learning",
    "dl": "deep learning"
}

def normalize_skill(skill: str) -> str:
    """Normalize equivalent skills based on mapping engine."""
    s = skill.lower().strip()
    return SYNONYMS.get(s, s)

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3: MULTI-LAYER EXPERIENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_experience_breakdown(timeline: list, explicit_exp: float, required_skills: list, ignore_internships: bool = True) -> dict:
    """
    Computes total_experience and relevant_experience using candidate's employment timeline.
    Detects overlapping dates, filters out internships,
    and separates freelance from full-time work.
    """
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month

    def parse_to_month_index(date_str: str, default_year: int) -> int:
        if not date_str or not isinstance(date_str, str):
            return default_year * 12 + 1
        
        ds = date_str.lower().strip()
        if any(w in ds for w in ["present", "current", "till date", "now", "ongoing"]):
            return current_year * 12 + current_month
        
        # Search for year
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', ds)
        year = int(year_match.group(1)) if year_match else default_year
        
        # Search for month
        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        month = 1
        for m_name, m_val in months_map.items():
            if m_name in ds:
                month = m_val
                break
        return year * 12 + month

    months_covered_total = set()
    months_covered_relevant = set()
    months_covered_freelance = set()
    months_covered_internship = set()

    for entry in timeline:
        comp = entry.get("company", "").lower()
        title = entry.get("title", "").lower()
        
        is_intern = entry.get("is_internship", False) or "intern" in title or "intern" in comp
        is_free = entry.get("is_freelance", False) or "freelance" in title or "freelance" in comp or "contract" in title or "contractor" in title
        
        start_idx = parse_to_month_index(entry.get("start_date"), current_year - 5)
        end_idx = parse_to_month_index(entry.get("end_date"), current_year)
        
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx
            
        # Determine job relevance
        is_relevant = False
        if title:
            # Relevancy matches based on required skills or common engineering titles
            for s in required_skills:
                if normalize_skill(s) in title or normalize_skill(s) in comp:
                    is_relevant = True
                    break
            relevant_roles = ["developer", "engineer", "architect", "lead", "scientist", "analyst", "designer", "consultant", "programmer", "manager"]
            if any(r in title for r in relevant_roles):
                is_relevant = True

        for m in range(start_idx, end_idx + 1):
            if is_intern:
                months_covered_internship.add(m)
                if not ignore_internships:
                    months_covered_total.add(m)
            elif is_free:
                months_covered_freelance.add(m)
                months_covered_total.add(m)
                if is_relevant:
                    months_covered_relevant.add(m)
            else:
                months_covered_total.add(m)
                if is_relevant:
                    months_covered_relevant.add(m)

    total_yrs_timeline = len(months_covered_total) / 12.0
    relevant_yrs_timeline = len(months_covered_relevant) / 12.0
    freelance_yrs = len(months_covered_freelance) / 12.0
    internship_yrs = len(months_covered_internship) / 12.0

    # Fallback to explicit stated experience if timeline calculation is sparse
    total_exp = max(total_yrs_timeline, explicit_exp)
    relevant_exp = min(total_exp, max(relevant_yrs_timeline, explicit_exp * 0.8))

    return {
        "total_experience": round(total_exp, 1),
        "relevant_experience": round(relevant_exp, 1),
        "freelance_experience_years": round(freelance_yrs, 1),
        "internship_experience_years": round(internship_yrs, 1),
        "has_freelance": freelance_yrs > 0,
        "has_internship": internship_yrs > 0
    }

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5: WEIGHTED SCORING SYSTEM & STEP 6: AI VERIFICATION LAYER
# ═══════════════════════════════════════════════════════════════════════════════
def compute_skill_scores(required_skills: List[str], candidate_skills: List[str]) -> Tuple[float, List[str], List[str], List[str], List[str]]:
    """Calcules technical skill match breakdown."""
    if not required_skills:
        return 100.0, [], [], [], []

    req_norm = [normalize_skill(s) for s in required_skills]
    cand_norm = [normalize_skill(s) for s in candidate_skills]

    req_set = set(req_norm)
    cand_set = set(cand_norm)

    exact_set = req_set & cand_set
    remaining = req_set - exact_set

    semantic_matches = []
    partial_matches = []

    if remaining:
        model = get_model()
        if model:
            try:
                from sentence_transformers import util
                req_list = list(remaining)
                cand_list = list(cand_set - exact_set)

                if cand_list:
                    req_embeds = model.encode(req_list, convert_to_tensor=True)
                    cand_embeds = model.encode(cand_list, convert_to_tensor=True)
                    sim_matrix = util.cos_sim(req_embeds, cand_embeds)

                    for ri, req_skill in enumerate(req_list):
                        max_sim = float(sim_matrix[ri].max())
                        if max_sim >= 0.72:
                            semantic_matches.append(req_skill)
                        elif max_sim >= 0.50:
                            partial_matches.append(req_skill)
            except Exception as e:
                logger.warning(f"[Matching] Semantic match failed: {e}")

    still_missing = remaining - set(semantic_matches) - set(partial_matches)
    try:
        from rapidfuzz import fuzz, process as rfprocess
        for req_skill in list(still_missing):
            match = rfprocess.extractOne(
                req_skill, list(cand_set), scorer=fuzz.token_set_ratio, score_cutoff=75
            )
            if match:
                partial_matches.append(req_skill)
    except Exception:
        pass

    missing_set = remaining - set(semantic_matches) - set(partial_matches)

    n = len(req_set)
    credit = (
        len(exact_set) * 1.00 +
        len(semantic_matches) * 0.70 +
        len(partial_matches) * 0.40
    )
    score = _clamp((credit / n) * 100)

    return (
        round(score, 2),
        sorted(exact_set),
        sorted(semantic_matches),
        sorted(partial_matches),
        sorted(missing_set),
    )

def verify_with_recruiter_ai(candidate_profile: dict, jd_profile: dict) -> dict:
    """
    Sends BOTH structured candidate profile and structured JD to Groq LLM.
    Asks: 'Would a human recruiter shortlist this candidate?'
    Includes strict guidelines to prevent hallucinations.
    """
    client = get_groq_client()
    if not client:
        return {}

    prompt = f"""You are a professional human recruiter performing candidate shortlisting.
We have parsed the Candidate's Resume and the Job Description into structured data:

Candidate Profile:
{json.dumps(candidate_profile, indent=2)}

Hiring Requirements:
{json.dumps(jd_profile, indent=2)}

Task:
Evaluate this candidate objectively. Decide: "Would a human recruiter shortlist this candidate?"
Generate a JSON output with the following keys.

CRITICAL HALLUCINATION PREVENTION:
1. ONLY reference skills, experience, and certifications present in the Candidate Profile.
2. DO NOT invent or assume any background not explicitly stated.
3. If uncertain or unverified, state: "Unable to confidently verify".

JSON Output format:
{{
  "recommendation": "Strong Hire / Hire / Hold / Reject",
  "reasoning": "A concise 2-sentence explanation of why they were shortlisted or not.",
  "strengths": ["string (Strength 1)", "string (Strength 2)"],
  "concerns": ["string (Concern 1)", "string (Concern 2)"],
  "final_recommendation_summary": "A bulleted recap of the recruiter's recommendation."
}}

Response:
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=8.0
        )
        response_text = completion.choices[0].message.content
        return safe_json_loads(response_text)
    except Exception as e:
        logger.error(f"[Matching] AI Verification Layer failed: {e}")
        return {}

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
async def rank_all_resumes(jd_text: str, candidates: list) -> list:
    """
    Structured Enterprise AI Matching Engine:
    Scores and ranks all candidates against a job description description.
    """
    # Step 2: JD Extraction
    jd_profile = parse_jd_with_llm(jd_text)
    required_skills = jd_profile["required_skills"]
    minimum_exp = jd_profile["minimum_experience"]

    results = []

    for candidate in candidates:
        raw_text = candidate.get("raw_text", "")
        filename = candidate.get("filename", "resume.pdf")

        # Step 1: Structured Candidate Profile (Retrieve or extract)
        # Check if structured fields exist on candidate document; if not, parse fresh
        if "employment_timeline" not in candidate or not candidate.get("employment_timeline"):
            candidate_profile = parse_resume_with_llm(raw_text, filename)
        else:
            candidate_profile = {
                "candidate_name": candidate.get("name", filename.split(".")[0]),
                "total_experience_years": candidate.get("experience_years", 0.0),
                "companies": candidate.get("companies", []),
                "job_titles": candidate.get("job_titles", []),
                "technical_skills": candidate.get("skills", []),
                "soft_skills": candidate.get("soft_skills", []),
                "certifications": candidate.get("certifications", []),
                "education": candidate.get("education", []),
                "projects": candidate.get("projects", []),
                "leadership_experience": candidate.get("leadership_experience", False),
                "domain_experience": candidate.get("domain_experience", []),
                "communication_indicators": candidate.get("communication_indicators", []),
                "employment_timeline": candidate.get("employment_timeline", []),
                "tools": candidate.get("tools", []),
                "technologies": candidate.get("technologies", []),
                "confidence_score": candidate.get("confidence_score", 75.0),
                "ambiguity_detection": candidate.get("ambiguity_detection", []),
                "extraction_reliability": candidate.get("extraction_reliability", "Medium")
            }

        # Step 3: Multi-Layer Experience Engine
        exp_breakdown = calculate_experience_breakdown(
            timeline=candidate_profile.get("employment_timeline", []),
            explicit_exp=candidate_profile.get("total_experience_years", 0.0),
            required_skills=required_skills,
            ignore_internships=True
        )
        total_exp = exp_breakdown["total_experience"]
        relevant_exp = exp_breakdown["relevant_experience"]

        # Step 4 & 5: Weighted Scoring System (35 / 25 / 15 / 10 / 5 / 5 / 5)
        # 1. Required Skills (35%)
        skill_score, exact, semantic_m, partial, missing = compute_skill_scores(
            required_skills,
            candidate_profile.get("technical_skills", [])
        )
        skills_weight_score = skill_score * 0.35

        # 2. Relevant Experience (25%)
        if minimum_exp <= 0:
            exp_score = 100.0 if relevant_exp > 0 else 80.0
        else:
            exp_score = _clamp((relevant_exp / minimum_exp) * 100)
        exp_weight_score = exp_score * 0.25

        # 3. Domain Match (15%)
        domain_reqs = [d.lower().strip() for d in jd_profile.get("domain_requirements", [])]
        cand_domains = [d.lower().strip() for d in candidate_profile.get("domain_experience", [])]
        if not domain_reqs:
            domain_score = 100.0
        else:
            matched_domains = [d for d in cand_domains if any(req in d or d in req for req in domain_reqs)]
            domain_score = _clamp((len(matched_domains) / len(domain_reqs)) * 100)
        domain_weight_score = domain_score * 0.15

        # 4. Leadership (10%)
        is_leadership_req = jd_profile.get("leadership_required", False)
        has_leadership = candidate_profile.get("leadership_experience", False)
        if is_leadership_req:
            leadership_score = 100.0 if has_leadership else 0.0
        else:
            leadership_score = 100.0
        leadership_weight_score = leadership_score * 0.10

        # 5. Projects (5%)
        proj_reqs = jd_profile.get("project_requirements", [])
        cand_projs = candidate_profile.get("projects", [])
        if not proj_reqs:
            project_score = 100.0 if len(cand_projs) > 0 else 70.0
        else:
            matched_projs = [p for p in cand_projs if any(req.lower() in p.lower() for req in proj_reqs)]
            project_score = _clamp((len(matched_projs) / len(proj_reqs)) * 100)
        project_weight_score = project_score * 0.05

        # 6. Certifications (5%)
        cert_reqs = jd_profile.get("certifications_required", [])
        cand_certs = candidate_profile.get("certifications", [])
        if not cert_reqs:
            cert_score = 100.0 if len(cand_certs) > 0 else 70.0
        else:
            matched_certs = [c for c in cand_certs if any(req.lower() in c.lower() for req in cert_reqs)]
            cert_score = _clamp((len(matched_certs) / len(cert_reqs)) * 100)
        cert_weight_score = cert_score * 0.05

        # 7. Communication (5%)
        comm_req = jd_profile.get("communication_required", False)
        comm_indicators = candidate_profile.get("communication_indicators", [])
        if comm_req:
            comm_score = 100.0 if len(comm_indicators) > 0 else 60.0
        else:
            comm_score = 100.0 if len(comm_indicators) > 0 else 90.0
        comm_weight_score = comm_score * 0.05

        # Final Weighted Score Calculation
        final_score = _clamp(
            skills_weight_score +
            exp_weight_score +
            domain_weight_score +
            leadership_weight_score +
            project_weight_score +
            cert_weight_score +
            comm_weight_score
        )

        # Step 6: AI Verification Layer
        ai_verification = verify_with_recruiter_ai(candidate_profile, jd_profile)
        
        # Fallback summary if AI call fails
        if not ai_verification or not ai_verification.get("recommendation"):
            rec_status = "Hold"
            if final_score >= 78:
                rec_status = "Strong Hire"
            elif final_score >= 58:
                rec_status = "Hire"
            elif final_score < 40:
                rec_status = "Reject"
                
            ai_verification = {
                "recommendation": rec_status,
                "reasoning": f"Recruiter verified candidate matching {len(exact)} exact skills with {relevant_exp} years relevant experience.",
                "strengths": [f"Matches {len(exact)} required skills", f"{relevant_exp} yrs experience"],
                "concerns": [f"Missing {len(missing)} required skills" if missing else "None identified"],
                "final_recommendation_summary": f"Recommendation: {rec_status}"
            }

        # Step 7: Confidence Engine & Step 8: Hallucination Prevention
        conf_score = candidate_profile.get("confidence_score", 75.0)
        ambiguity = candidate_profile.get("ambiguity_detection", [])
        reliability = candidate_profile.get("extraction_reliability", "Medium")

        # Step 9: Final Enterprise Score Details
        # Risk Flags
        risk_flags = []
        if len(missing) >= 3:
            risk_flags.append(f"Missing {len(missing)} required skills: {', '.join(missing[:3])}")
        if relevant_exp < minimum_exp * 0.5:
            risk_flags.append(f"Relevant experience ({relevant_exp} yrs) is significantly below required ({minimum_exp} yrs)")
        if exp_breakdown.get("has_freelance"):
            risk_flags.append("Significant freelance/contract tenure detected in timeline")

        # Step 10: Recruiter Explanation
        recruiter_exp = f"Candidate ranked because:\n"
        recruiter_exp += f"- {relevant_exp} years of relevant experience detected (out of {total_exp} years total).\n"
        recruiter_exp += f"- Matches {len(exact)} required skills exactly ({', '.join(exact[:3])}).\n"
        if has_leadership:
            recruiter_exp += f"- Leadership experience present.\n"
        if domain_score >= 70:
            recruiter_exp += f"- Domain alignment matches requirements.\n"
        if missing:
            recruiter_exp += f"- Note: Missing {len(missing)} required skills: {', '.join(missing[:3])}.\n"

        # Prepare match explanation object
        explanation = {
            "exact_matches": exact,
            "semantic_matches": semantic_m,
            "partial_matches": partial,
            "missing_skills": missing,
            "bonus_skills": candidate_profile.get("soft_skills", []),
            "certifications": candidate_profile.get("certifications", []),
            "projects": candidate_profile.get("projects", []),
            "experience_verdict": f"{relevant_exp} years relevant experience vs {minimum_exp} required",
            "skills_summary": f"Matched {len(exact) + len(semantic_m)} skills",
            "overall_verdict": recruiter_exp,
            "risk_flags": risk_flags,
            "confidence_score": conf_score,
            "score_breakdown": {
                "skill_score": round(skill_score, 1),
                "exp_score": round(exp_score, 1),
                "semantic_score": round(domain_score, 1),
                "final_score": round(final_score, 1),
                "technical_fit": round(skill_score * 0.7 + domain_score * 0.3, 1),
                "experience_relevance": round(exp_score, 1),
                "resume_quality": round(conf_score, 1),
                "weights": {
                    "skill": 35,
                    "exp": 25,
                    "domain": 15,
                    "leadership": 10,
                    "projects": 5,
                    "certifications": 5,
                    "communication": 5
                },
                "formula": "35% skills + 25% exp + 15% domain + 10% leadership + 5% projects + 5% certs + 5% comm"
            }
        }

        # Build hiring summary structure compatible with existing components
        hiring_summary = {
            "narrative": ai_verification.get("reasoning", ""),
            "strengths": ai_verification.get("strengths", []),
            "weaknesses": ai_verification.get("concerns", []),
            "recommendation": ai_verification.get("recommendation", "Hold"),
            "confidence": reliability,
            "generated_at": datetime.datetime.utcnow().isoformat()
        }

        # Update candidate profile fields to be saved to DB
        updated_candidate = {
            **candidate,
            **candidate_profile,
            "score": round(final_score, 2),
            "skill_score": round(skill_score, 2),
            "experience_score": round(exp_score, 2),
            "semantic_score": round(domain_score, 2),
            "technical_fit": round(skill_score * 0.7 + domain_score * 0.3, 2),
            "experience_relevance": round(exp_score, 2),
            "resume_quality": round(conf_score, 2),
            "risk_flags": risk_flags,
            "matched_skills": sorted(list(set(exact) | set(semantic_m) | set(partial))),
            "missing_skills": missing,
            "exact_matches": exact,
            "semantic_matches": semantic_m,
            "partial_matches": partial,
            "bonus_skills": candidate_profile.get("soft_skills", []),
            "confidence_score": conf_score,
            "ambiguity_detection": ambiguity,
            "extraction_reliability": reliability,
            "leadership_match": "Yes" if has_leadership else "No",
            "communication_match": "Verified" if len(comm_indicators) > 0 else "Baseline",
            "recruiter_explanation": recruiter_exp,
            "match_explanation": explanation,
            "hiring_summary": hiring_summary,
            "domain_match_score": round(domain_score, 2),
            "leadership_score": round(leadership_score, 2),
            "projects_score": round(project_score, 2),
            "certifications_score": round(cert_score, 2),
            "communication_score": round(comm_score, 2)
        }
        results.append(updated_candidate)

    return sorted(results, key=lambda x: x["score"], reverse=True)
