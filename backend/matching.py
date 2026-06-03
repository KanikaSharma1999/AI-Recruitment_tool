"""
Enterprise ATS Ranking Engine v2 - Anti-Inflation Edition
==========================================================
Scoring weights:
  Skills Match       40%  (required skills heavily penalized when missing)
  Experience Match   25%  (hard penalty when below minimum)
  Semantic Similarity 15% (document-level cosine, REDUCED influence)
  Project Relevance  10%
  Certifications      5%
  Resume Quality      5%

Target distribution:
  90-100  Exceptional
  80-89   Strong Hire
  70-79   Good Match
  60-69   Moderate Match
  40-59   Weak Match
  20-39   Poor Match
  0-19    Not Suitable
"""

import asyncio
import re
import logging
import datetime
import os
import json
from typing import List, Tuple, Dict

from services.llm_parser import (
    parse_resume_with_llm, parse_jd_with_llm,
    get_groq_client, safe_json_loads,
    _set_groq_rate_limited, _is_groq_rate_limited
)

logger = logging.getLogger(__name__)

_model = None

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"[Matching] Model load failed: {e}")
            _model = None
    return _model


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return min(hi, max(lo, float(val)))


# ---------------------------------------------------------------------------
# Skill synonym map (normalisation)
# ---------------------------------------------------------------------------
SYNONYMS = {
    "reactjs": "react", "react.js": "react", "react js": "react",
    "angularjs": "angular", "angular js": "angular",
    "vuejs": "vue", "vue.js": "vue",
    "ml": "machine learning", "ai": "machine learning",
    "node": "node.js", "nodejs": "node.js",
    "ts": "typescript", "js": "javascript",
    "golang": "go", "k8s": "kubernetes",
    "containerization": "docker",
    "aws": "amazon web services", "gcp": "google cloud",
    "cicd": "ci/cd", "nlp": "natural language processing",
    "dl": "deep learning", "postgres": "postgresql",
    "postgresql": "postgresql",
    "sql": "postgresql",
    "mongo": "mongodb",
    "pytest": "unit testing",
    "unittest": "unit testing",
    "rest": "rest api",
}

def normalize_skill(skill: str) -> str:
    s = skill.lower().strip()
    return SYNONYMS.get(s, s)


# ---------------------------------------------------------------------------
# Experience engine
# ---------------------------------------------------------------------------
def calculate_experience_breakdown(timeline: list, explicit_exp: float,
                                   required_skills: list,
                                   ignore_internships: bool = True) -> dict:
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month

    def to_month(date_str, default_year):
        if not date_str or not isinstance(date_str, str):
            return default_year * 12 + 1
        ds = date_str.lower().strip()
        if any(w in ds for w in ["present", "current", "till date", "now", "ongoing"]):
            return current_year * 12 + current_month
        year_m = re.search(r'\b(19\d\d|20\d\d)\b', ds)
        year = int(year_m.group(1)) if year_m else default_year
        months_map = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                      "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
        month = 1
        for mn, mv in months_map.items():
            if mn in ds:
                month = mv
                break
        return year * 12 + month

    total_months = set()
    relevant_months = set()
    internship_months = set()
    freelance_months = set()

    for entry in timeline:
        comp = entry.get("company", "").lower()
        title = entry.get("title", "").lower()
        is_intern = entry.get("is_internship", False) or "intern" in title or "intern" in comp
        is_free = entry.get("is_freelance", False) or any(
            w in title for w in ["freelance", "contract", "contractor"])

        s = to_month(entry.get("start_date"), current_year - 5)
        e = to_month(entry.get("end_date"), current_year)
        if s > e:
            s, e = e, s

        is_relevant = False
        if title:
            for sk in required_skills:
                if normalize_skill(sk) in title or normalize_skill(sk) in comp:
                    is_relevant = True
                    break
            relevant_roles = ["developer","engineer","architect","lead","scientist",
                              "analyst","designer","consultant","programmer","manager"]
            if any(r in title for r in relevant_roles):
                is_relevant = True

        for m in range(s, e + 1):
            if is_intern:
                internship_months.add(m)
                if not ignore_internships:
                    total_months.add(m)
            else:
                total_months.add(m)
                if is_free:
                    freelance_months.add(m)
                if is_relevant:
                    relevant_months.add(m)

    total_yrs = len(total_months) / 12.0
    relevant_yrs = len(relevant_months) / 12.0
    freelance_yrs = len(freelance_months) / 12.0
    internship_yrs = len(internship_months) / 12.0

    # Fallback to explicit only when timeline is sparse
    total_exp = max(total_yrs, explicit_exp) if total_yrs > 0 else explicit_exp
    relevant_exp = min(total_exp, max(relevant_yrs, explicit_exp * 0.7))

    return {
        "total_experience": round(total_exp, 1),
        "relevant_experience": round(relevant_exp, 1),
        "freelance_experience_years": round(freelance_yrs, 1),
        "internship_experience_years": round(internship_yrs, 1),
        "has_freelance": freelance_yrs > 0,
        "has_internship": internship_yrs > 0,
    }


# ---------------------------------------------------------------------------
# Skill scoring  (40% of total)
# ---------------------------------------------------------------------------
def compute_skill_scores(required_skills: List[str],
                         candidate_skills: List[str]) -> Tuple[float, List, List, List, List]:
    """
    Returns (score 0-100, exact, semantic, partial, missing).

    HARD RULES (anti-inflation):
    - If no required skills listed AND candidate has <3 skills → 30
    - If no required skills listed AND candidate has skills → 60 (not 100)
    - Exact match  = 1.0 credit
    - Semantic ≥0.78 = 0.6 credit  (raised from 0.72, reduced credit from 0.70)
    - Partial ≥0.55 = 0.3 credit   (raised from 0.50, reduced credit from 0.40)
    - Fuzzy  ≥80    = 0.25 credit
    - Every missing REQUIRED skill subtracts additional penalty from final
    """
    # Guard: no required skills → reduce ceiling
    if not required_skills:
        if not candidate_skills:
            return 25.0, [], [], [], []
        if len(candidate_skills) < 3:
            return 40.0, [], [], [], candidate_skills
        return 60.0, [], [], [], []          # <-- was 100. Now capped at 60

    req_norm = [normalize_skill(s) for s in required_skills]
    cand_norm = [normalize_skill(s) for s in candidate_skills]
    req_set = set(req_norm)
    cand_set = set(cand_norm)

    exact_set = req_set & cand_set
    remaining = req_set - exact_set

    semantic_matches: List[str] = []
    partial_matches: List[str] = []

    if remaining:
        model = get_model()
        if model and cand_set:
            try:
                from sentence_transformers import util
                req_list = list(remaining)
                cand_list = list(cand_set - exact_set)
                if cand_list:
                    req_emb = model.encode(req_list, convert_to_tensor=True)
                    cand_emb = model.encode(cand_list, convert_to_tensor=True)
                    sim = util.cos_sim(req_emb, cand_emb)
                    for ri, rsk in enumerate(req_list):
                        max_sim = float(sim[ri].max())
                        if max_sim >= 0.78:          # raised from 0.72
                            semantic_matches.append(rsk)
                        elif max_sim >= 0.55:        # raised from 0.50
                            partial_matches.append(rsk)
            except Exception as e:
                logger.warning(f"[Matching] Semantic match failed: {e}")

    still_missing = remaining - set(semantic_matches) - set(partial_matches)
    try:
        from rapidfuzz import fuzz, process as rfp
        for rsk in list(still_missing):
            match = rfp.extractOne(rsk, list(cand_set), scorer=fuzz.token_set_ratio, score_cutoff=80)
            if match:
                partial_matches.append(rsk)
    except Exception:
        pass

    missing_set = remaining - set(semantic_matches) - set(partial_matches)

    n = len(req_set)
    credit = (
        len(exact_set) * 1.00
        + len(semantic_matches) * 0.60    # reduced from 0.70
        + len(partial_matches) * 0.30     # reduced from 0.40
    )
    raw_score = (credit / n) * 100

    # Hard penalty: ≥40% required skills missing → additional -10 per 10% missing
    missing_ratio = len(missing_set) / n
    if missing_ratio >= 0.4:
        penalty = ((missing_ratio - 0.3) * 100) * 0.5   # e.g. 70% missing → -20pts
        raw_score = max(0, raw_score - penalty)

    return (
        round(_clamp(raw_score), 2),
        sorted(exact_set),
        sorted(semantic_matches),
        sorted(partial_matches),
        sorted(missing_set),
    )


# ---------------------------------------------------------------------------
# Document-level semantic similarity  (15% of total)
# ---------------------------------------------------------------------------
def compute_semantic_similarity(jd_text: str, resume_text: str) -> float:
    """
    Cosine similarity between JD and resume embeddings.
    Returns 0-100 but SCALED DOWN: raw cosine * 70 so max is ~70
    to prevent semantic score dominating the final score.
    """
    if not jd_text or not resume_text:
        return 30.0
    model = get_model()
    if not model:
        return 40.0
    try:
        from sentence_transformers import util
        emb_jd  = model.encode([jd_text[:3000]], convert_to_tensor=True)
        emb_res = model.encode([resume_text[:3000]], convert_to_tensor=True)
        cos = float(util.cos_sim(emb_jd, emb_res)[0][0])
        # Map cosine [0,1] → score [0,70] instead of [0,100]
        score = _clamp(cos * 70.0, 10.0, 70.0)
        return round(score, 2)
    except Exception as e:
        logger.warning(f"[Matching] Semantic similarity failed: {e}")
        return 35.0


# ---------------------------------------------------------------------------
# Resume quality / completeness score  (5% of total)
# ---------------------------------------------------------------------------
def compute_quality_score(candidate_profile: dict, raw_text: str) -> float:
    score = 100.0
    penalties = []

    email = candidate_profile.get("email") or ""
    if not email or email == "Not Found":
        score -= 20
        penalties.append("missing email (-20)")

    if len(raw_text) < 300:
        score -= 30
        penalties.append("very short resume (<300 chars) (-30)")
    elif len(raw_text) < 700:
        score -= 15
        penalties.append("short resume (<700 chars) (-15)")

    if not candidate_profile.get("employment_timeline") and \
       (candidate_profile.get("total_experience_years", 0) or 0) == 0:
        score -= 15
        penalties.append("no work history detected (-15)")

    conf = candidate_profile.get("confidence_score", 75.0) or 75.0
    if conf < 50:
        score -= 20
        penalties.append(f"low extraction confidence {conf:.0f} (-20)")
    elif conf < 65:
        score -= 10
        penalties.append(f"medium-low confidence {conf:.0f} (-10)")

    reliability = candidate_profile.get("extraction_reliability", "Medium") or "Medium"
    if reliability == "Low":
        score -= 15
        penalties.append("extraction reliability=Low (-15)")

    return _clamp(score), penalties


# ---------------------------------------------------------------------------
# AI Verification layer (Groq) - unchanged but fallback verdict is honest
# ---------------------------------------------------------------------------
def verify_with_recruiter_ai(candidate_profile: dict, jd_profile: dict) -> dict:
    client = get_groq_client()
    if not client:
        return {}

    prompt = f"""You are a professional human recruiter. Evaluate this candidate strictly and honestly.

Candidate Profile:
{json.dumps(candidate_profile, indent=2)}

Hiring Requirements:
{json.dumps(jd_profile, indent=2)}

RULES:
1. Only reference skills/experience explicitly in the Candidate Profile.
2. Do NOT inflate or be lenient. A candidate missing 3+ required skills should be "Hold" or "Reject".
3. Match your recommendation to actual skill coverage.

JSON output:
{{
  "recommendation": "Strong Hire / Hire / Hold / Reject",
  "reasoning": "2-sentence factual explanation.",
  "strengths": ["string"],
  "concerns": ["string"],
  "final_recommendation_summary": "bulleted recap"
}}
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
            timeout=30.0,
        )
        return safe_json_loads(completion.choices[0].message.content)
    except Exception as e:
        err_str = str(e).lower()
        if "rate_limit" in err_str or "429" in str(e):
            _set_groq_rate_limited(300)
        elif "connection error" in err_str or "service unavailable" in err_str:
            _set_groq_rate_limited(60)
        logger.error(f"[Matching] AI Verification failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Verdict mapping (honest thresholds)
# ---------------------------------------------------------------------------
def score_to_verdict(score: float) -> str:
    if score >= 90:
        return "Exceptional Candidate"
    elif score >= 80:
        return "Strong Hire"
    elif score >= 70:
        return "Good Match"
    elif score >= 60:
        return "Moderate Match"
    elif score >= 40:
        return "Weak Match"
    elif score >= 20:
        return "Poor Match"
    else:
        return "Not Suitable"


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
async def rank_all_resumes(jd_text: str, candidates: list) -> list:
    """
    Anti-inflation enterprise ranking engine.
    Produces realistic score distribution with hard penalties.
    """
    # Parse JD
    try:
        jd_profile = parse_jd_with_llm(jd_text)
    except Exception:
        jd_profile = {
            "required_skills": [], "minimum_experience": 0.0,
            "domain_requirements": [], "project_requirements": [],
            "certifications_required": [],
        }

    required_skills = jd_profile.get("required_skills", [])
    minimum_exp     = float(jd_profile.get("minimum_experience", 0.0) or 0.0)
    jd_exists       = bool(jd_text and jd_text.strip())

    results = []

    for candidate in candidates:
        raw_text       = candidate.get("raw_text", "")
        filename       = candidate.get("filename", "resume.pdf")
        candidate_id   = str(candidate.get("_id", ""))
        candidate_name = candidate.get("name", filename.split(".")[0])

        print("=" * 50)
        print(f"[RANKING] {candidate_name}  id={candidate_id}")

        try:
            # ── Step 1: Extract candidate profile ──────────────────────
            if "employment_timeline" not in candidate or not candidate.get("employment_timeline"):
                candidate_profile = parse_resume_with_llm(raw_text, filename)
            else:
                candidate_profile = {
                    "candidate_name":         candidate.get("name", ""),
                    "total_experience_years": candidate.get("experience_years", 0.0),
                    "companies":              candidate.get("companies", []),
                    "job_titles":             candidate.get("job_titles", []),
                    "technical_skills":       candidate.get("skills", []),
                    "soft_skills":            candidate.get("soft_skills", []),
                    "certifications":         candidate.get("certifications", []),
                    "education":              candidate.get("education", []),
                    "projects":               candidate.get("projects", []),
                    "leadership_experience":  candidate.get("leadership_experience", False),
                    "domain_experience":      candidate.get("domain_experience", []),
                    "communication_indicators": candidate.get("communication_indicators", []),
                    "employment_timeline":    candidate.get("employment_timeline", []),
                    "tools":                  candidate.get("tools", []),
                    "technologies":           candidate.get("technologies", []),
                    "confidence_score":       candidate.get("confidence_score", 75.0),
                    "ambiguity_detection":    candidate.get("ambiguity_detection", []),
                    "extraction_reliability": candidate.get("extraction_reliability", "Medium"),
                    "email":                  candidate.get("email", ""),
                }

            if not raw_text or not raw_text.strip():
                raise ValueError("empty resume")
            if not jd_exists:
                raise ValueError("no JD attached")

            # ── Step 2: Experience ──────────────────────────────────────
            exp_breakdown = calculate_experience_breakdown(
                timeline=candidate_profile.get("employment_timeline", []),
                explicit_exp=float(candidate_profile.get("total_experience_years") or 0.0),
                required_skills=required_skills,
            )
            total_exp    = exp_breakdown["total_experience"]
            relevant_exp = exp_breakdown["relevant_experience"]

            # ── Step 3: SKILLS (40%) ────────────────────────────────────
            skill_score, exact, semantic_m, partial, missing = compute_skill_scores(
                required_skills,
                candidate_profile.get("technical_skills", []),
            )
            skills_weight = skill_score * 0.40

            # ── Step 4: EXPERIENCE (25%) ────────────────────────────────
            if minimum_exp <= 0:
                # No explicit requirement — score based on what they have
                # 0 yrs → 20, 1 yr → 40, 3 yrs → 65, 5+ yrs → 80
                exp_score = _clamp(min(80.0, 20.0 + relevant_exp * 12.0))
            else:
                ratio = relevant_exp / minimum_exp
                if ratio >= 1.0:
                    exp_score = _clamp(70.0 + (ratio - 1.0) * 15.0, 0, 100)
                else:
                    # Candidate is short on experience — hard penalty
                    exp_score = _clamp(ratio * 70.0)          # e.g. half exp → 35
            exp_weight = exp_score * 0.25

            # ── Step 5: SEMANTIC SIMILARITY (15%) ──────────────────────
            sem_score  = compute_semantic_similarity(jd_text, raw_text)
            sem_weight = sem_score * 0.15

            # ── Step 6: PROJECTS (10%) ─────────────────────────────────
            proj_reqs  = jd_profile.get("project_requirements", [])
            cand_projs = candidate_profile.get("projects", [])
            if not proj_reqs:
                # No explicit project reqs: reward having projects, penalize none
                project_score = 70.0 if len(cand_projs) >= 2 else (
                    50.0 if len(cand_projs) == 1 else 20.0)   # was 100 / 70
            else:
                matched_p = [p for p in cand_projs if any(r.lower() in p.lower() for r in proj_reqs)]
                project_score = _clamp((len(matched_p) / len(proj_reqs)) * 100)
            proj_weight = project_score * 0.10

            # ── Step 7: CERTIFICATIONS (5%) ────────────────────────────
            cert_reqs  = jd_profile.get("certifications_required", [])
            cand_certs = candidate_profile.get("certifications", [])
            if not cert_reqs:
                cert_score = 65.0 if cand_certs else 40.0     # was 100 / 70
            else:
                matched_c = [c for c in cand_certs if any(r.lower() in c.lower() for r in cert_reqs)]
                cert_score = _clamp((len(matched_c) / len(cert_reqs)) * 100)
            cert_weight = cert_score * 0.05

            # ── Step 8: RESUME QUALITY (5%) ────────────────────────────
            quality_score, quality_penalties = compute_quality_score(candidate_profile, raw_text)
            quality_weight = quality_score * 0.05

            # ── Weighted sum ────────────────────────────────────────────
            raw_final = (
                skills_weight
                + exp_weight
                + sem_weight
                + proj_weight
                + cert_weight
                + quality_weight
            )

            # ── Global hard penalties ───────────────────────────────────
            global_penalties = []

            # P1: Graduated penalty for missing required skills
            if required_skills:
                missing_ratio = len(missing) / len(required_skills)
                if missing_ratio >= 0.7:          # >70% skills missing
                    deduct = 20
                    global_penalties.append(f">70% required skills missing -{deduct}pts")
                    raw_final -= deduct
                elif missing_ratio >= 0.5:        # 50-70% skills missing
                    deduct = 12
                    global_penalties.append(f">50% required skills missing -{deduct}pts")
                    raw_final -= deduct
                elif missing_ratio >= 0.3 and skill_score < 50:
                    deduct = 6
                    global_penalties.append(f">30% required skills missing -{deduct}pts")
                    raw_final -= deduct

            # P2: Experience far below requirement
            if minimum_exp > 0 and relevant_exp < minimum_exp * 0.5:
                raw_final -= 10
                global_penalties.append(
                    f"Experience severely below requirement ({relevant_exp:.1f} vs {minimum_exp:.1f}yrs) -10pts")

            # P3: Very short resume
            if len(raw_text) < 500:
                raw_final -= 10
                global_penalties.append("Severely incomplete resume (<500 chars) -10pts")

            # P4: Low extraction confidence
            conf = candidate_profile.get("confidence_score", 75.0) or 75.0
            if conf < 50:
                raw_final -= 8
                global_penalties.append(f"Low extraction confidence ({conf:.0f}) -8pts")

            final_score = _clamp(raw_final)

            # ── Verdict mapping ─────────────────────────────────────────
            ai_verification = verify_with_recruiter_ai(candidate_profile, jd_profile)
            if ai_verification and ai_verification.get("recommendation"):
                ai_verdict = ai_verification["recommendation"]
            else:
                ai_verdict = score_to_verdict(final_score)
                ai_verification = {
                    "recommendation": ai_verdict,
                    "reasoning": f"Score-based verdict. Skill coverage: {skill_score:.0f}%, "
                                 f"Experience: {relevant_exp:.1f}yrs, Semantic: {sem_score:.0f}%.",
                    "strengths": exact[:3],
                    "concerns": missing[:3],
                }

            # ── Build recruiter explanation ──────────────────────────────
            penalty_text = "; ".join(global_penalties + quality_penalties) or "None"
            recruiter_exp = (
                f"Matched {len(exact)} of {len(required_skills)} required skills. "
                f"Experience: {relevant_exp:.1f}yrs (req {minimum_exp:.1f}yrs). "
                f"Penalties: {penalty_text}."
            )
            if missing:
                recruiter_exp += f" Missing required skills: {', '.join(missing[:5])}."

            hiring_summary = {
                "narrative":    ai_verification.get("reasoning", ""),
                "strengths":    ai_verification.get("strengths", []),
                "weaknesses":   ai_verification.get("concerns", []),
                "recommendation": ai_verdict,
                "confidence":   candidate_profile.get("extraction_reliability", "Medium"),
                "generated_at": datetime.datetime.utcnow().isoformat(),
            }

            # ── Score breakdown for UI ───────────────────────────────────
            score_breakdown = {
                "skill_score":         round(skill_score, 2),
                "experience_score":    round(exp_score, 2),
                "semantic_score":      round(sem_score, 2),
                "project_score":       round(project_score, 2),
                "cert_score":          round(cert_score, 2),
                "quality_score":       round(quality_score, 2),
                "penalties":           global_penalties + quality_penalties,
                "final_score":         round(final_score, 2),
            }

            print(f"  skill={skill_score:.1f}  exp={exp_score:.1f}  sem={sem_score:.1f}  "
                  f"proj={project_score:.1f}  cert={cert_score:.1f}  qual={quality_score:.1f}")
            print(f"  FINAL={final_score:.1f}  verdict={ai_verdict}")
            print(f"  missing={missing[:5]}  penalties={global_penalties}")

            updated_candidate = {
                **candidate,
                **candidate_profile,
                "score":               round(final_score, 2),
                "ai_match_score":      round(final_score, 2),
                "ai_verdict":          ai_verdict,
                "ranking_error":       None,
                # Individual component scores
                "skill_score":         round(skill_score, 2),
                "skills_score":        round(skill_score, 2),
                "experience_score":    round(exp_score, 2),
                "semantic_score":      round(sem_score, 2),
                "projects_score":      round(project_score, 2),
                "certification_score": round(cert_score, 2),
                "certifications_score": round(cert_score, 2),
                "resume_quality":      round(quality_score, 2),
                # Skill breakdown
                "matched_skills":      sorted(set(exact) | set(semantic_m) | set(partial)),
                "missing_skills":      missing,
                "exact_matches":       exact,
                "semantic_matches":    semantic_m,
                "partial_matches":     partial,
                "bonus_skills":        candidate_profile.get("soft_skills", []),
                # Metadata
                "confidence_score":    candidate_profile.get("confidence_score", 75.0),
                "ambiguity_detection": candidate_profile.get("ambiguity_detection", []),
                "extraction_reliability": candidate_profile.get("extraction_reliability", "Medium"),
                "risk_flags":          global_penalties,
                "recruiter_explanation": recruiter_exp,
                "hiring_summary":      hiring_summary,
                "score_breakdown":     score_breakdown,
                # Legacy fields
                "technical_fit":       round(skill_score * 0.7 + sem_score * 0.3, 2),
                "experience_relevance": round(exp_score, 2),
                "leadership_match":    "Yes" if candidate_profile.get("leadership_experience") else "No",
                "communication_match": "Verified" if candidate_profile.get("communication_indicators") else "Baseline",
                "match_explanation":   score_breakdown,
                "domain_match_score":  round(sem_score, 2),
                "leadership_score":    100.0 if candidate_profile.get("leadership_experience") else 0.0,
                "communication_score": 80.0 if candidate_profile.get("communication_indicators") else 50.0,
            }
            results.append(updated_candidate)

        except Exception as e:
            error_str = str(e)
            print(f"[FAILURE] {candidate_name}: {error_str}")

            verdict_msg = "Ranking Failed"
            if "empty resume" in error_str:
                verdict_msg = "Resume Parse Failed"
            elif "no JD" in error_str:
                verdict_msg = "Missing JD"

            results.append({
                **candidate,
                "score": 0.0,
                "ai_match_score": None,
                "ai_verdict": verdict_msg,
                "ranking_error": error_str,
                "skill_score": 0.0,
                "skills_score": None,
                "experience_score": None,
                "semantic_score": None,
                "projects_score": None,
                "certification_score": None,
                "certifications_score": None,
                "missing_skills": [],
                "matched_skills": [],
                "hiring_summary": {
                    "recommendation": verdict_msg,
                    "narrative": f"Evaluation failed: {error_str}",
                },
            })

    return sorted(results, key=lambda x: float(x.get("score") or 0.0), reverse=True)


def extract_required_experience(text: str) -> float:
    from resume_parser import extract_experience_years
    return extract_experience_years(text)
