"""
Hiring Summary Generator
========================
Generates recruiter-grade, evidence-based hiring summaries for ranked candidates.
Guarantees MINIMUM 3 detailed, evidence-based points per strengths/weaknesses/risks.
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
    certifications: list = None,
    projects: list = None,
    employment_timeline: list = None,
    soft_skills: list = None,
    semantic_score: float = 0.0,
) -> dict:
    """Generate a rich recruiter-style summary with MINIMUM 3 points per section."""

    certifications = certifications or []
    projects = projects or []
    employment_timeline = employment_timeline or []
    soft_skills = soft_skills or []

    # ── STRENGTHS (minimum 3 detailed points) ────────────────────────────────
    strengths = []

    # Strength 1: Technical skill alignment
    if matched_skills:
        top_skills = ", ".join(matched_skills[:4])
        pct = round(technical_fit)
        strengths.append(
            f"Strong technical alignment at {pct}% — demonstrated proficiency in {top_skills}, "
            f"which are core requirements for this role."
        )
    elif technical_fit >= 50:
        strengths.append(
            f"Acceptable technical fit ({round(technical_fit)}%) with relevant domain skills "
            f"aligned to this position."
        )
    else:
        strengths.append(
            f"Demonstrates foundational technical knowledge applicable to the {job_title} role, "
            f"with room for further skill validation during the interview."
        )

    # Strength 2: Experience
    if experience_years > 0:
        if required_exp > 0 and experience_years >= required_exp:
            strengths.append(
                f"Meets or exceeds the experience requirement — {experience_years:.1f} years of professional "
                f"experience (position requires {required_exp:.0f} years), indicating hands-on readiness."
            )
        elif required_exp > 0:
            strengths.append(
                f"Brings {experience_years:.1f} years of professional experience, providing a practical "
                f"foundation even if slightly below the stated {required_exp:.0f}-year threshold."
            )
        else:
            strengths.append(
                f"Has {experience_years:.1f} years of relevant professional experience, demonstrating "
                f"consistent career growth and real-world problem-solving exposure."
            )
    else:
        strengths.append(
            f"Academic background and project work indicate a strong learning foundation, "
            f"suitable for entry-level or graduate-tier consideration."
        )

    # Strength 3: Qualifications depth (projects / certifications / resume quality)
    if projects:
        proj_names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in projects[:2]]
        strengths.append(
            f"Practical hands-on project experience documented: {', '.join(proj_names)} — "
            f"evidence of applied technical skills beyond theoretical knowledge."
        )
    elif certifications:
        cert_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in certifications[:2]]
        strengths.append(
            f"Holds professional certifications ({', '.join(cert_names)}), demonstrating "
            f"validated domain expertise and commitment to professional development."
        )
    elif resume_quality >= 60:
        strengths.append(
            f"Well-structured resume ({round(resume_quality)}% quality score) with clear evidence "
            f"of education, work history, and skill development — signals professional presentation skills."
        )
    else:
        strengths.append(
            f"Profile shows consistent career trajectory with verifiable employment history "
            f"and documented skill sets relevant to the {job_title} role."
        )

    # Strength 4 (bonus): Semantic fit or soft skills
    if semantic_score >= 65:
        strengths.append(
            f"High semantic similarity ({round(semantic_score)}%) to the job description — resume "
            f"language and domain vocabulary strongly align with the role's expectations."
        )
    elif soft_skills:
        top_soft = ", ".join(soft_skills[:3])
        strengths.append(
            f"Demonstrates valuable interpersonal competencies: {top_soft} — "
            f"traits that support effective team collaboration and project delivery."
        )

    # ── WEAKNESSES (minimum 3 detailed points) ────────────────────────────────
    weaknesses = []

    # Weakness 1: Skill gaps
    if missing_skills:
        top_missing = ", ".join(missing_skills[:4])
        weaknesses.append(
            f"Missing key required skills for this role: {top_missing}. "
            f"These gaps could require onboarding support or upskilling investment from the team."
        )
    else:
        weaknesses.append(
            f"No critical required skill gaps detected at this stage; however, "
            f"proficiency depth in matched skills should be verified during the technical interview."
        )

    # Weakness 2: Experience gap
    if required_exp > 0 and experience_years < required_exp:
        shortfall = required_exp - experience_years
        weaknesses.append(
            f"Experience shortfall of {shortfall:.1f} years — candidate has {experience_years:.1f} years "
            f"but the role requires {required_exp:.0f} years. May need a longer ramp-up period."
        )
    elif experience_years == 0:
        weaknesses.append(
            f"No formal employment timeline documented — it is unclear whether the candidate "
            f"has professional work experience. Further verification is essential."
        )
    else:
        weaknesses.append(
            f"While experience level is adequate, the candidate's background may require alignment "
            f"with this team's specific technology stack and workflow practices."
        )

    # Weakness 3: Resume quality or depth
    if resume_quality < 50:
        weaknesses.append(
            f"Resume quality is below average ({round(resume_quality)}% score) — limited documentation "
            f"of projects, certifications, or education makes it harder to fully evaluate this candidate."
        )
    elif not certifications and not projects:
        weaknesses.append(
            f"No certifications or notable projects listed to validate technical claims. "
            f"Additional portfolio or reference evidence is recommended before final decision."
        )
    else:
        weaknesses.append(
            f"Certain profile sections lack detail depth that would strengthen the overall evaluation, "
            f"particularly around quantified achievements or impact metrics."
        )

    # Weakness 4 (bonus): From risk flags
    if risk_flags:
        for rf in risk_flags[:1]:
            weaknesses.append(f"Identified concern: {rf}")

    # ── RISKS (minimum 3 detailed points) ────────────────────────────────────
    risks = []

    # Risk 1: Skill dependency risk
    if missing_skills:
        risks.append(
            f"Skill dependency risk: gaps in {', '.join(missing_skills[:3])} could slow "
            f"initial contribution and require dedicated onboarding resources or pairing."
        )
    else:
        risks.append(
            f"Skill coverage appears complete for stated requirements; however, "
            f"depth of expertise in each skill area must be confirmed via technical assessment."
        )

    # Risk 2: Stability / tenure risk
    if employment_timeline and len(employment_timeline) >= 3 and experience_years < 4.0:
        risks.append(
            f"Frequent role transitions detected ({len(employment_timeline)} positions in "
            f"{experience_years:.1f} years) — potential indicator of low tenure or retention risk."
        )
    elif required_exp > 0 and experience_years < required_exp * 0.6:
        risks.append(
            f"Significant experience shortfall ({experience_years:.1f} vs. {required_exp:.0f} required years) "
            f"introduces risk of slower productivity, higher mentoring cost, and longer time-to-impact."
        )
    else:
        risks.append(
            f"Standard onboarding risk applies — time-to-productivity will depend on familiarity "
            f"with company tools, processes, and team dynamics."
        )

    # Risk 3: Verification risk
    risks.append(
        f"Automated extraction risk: profile data is parsed programmatically and should be "
        f"cross-verified against the original resume and interview responses before final hiring decision."
    )

    # Risk 4 (bonus): Score-based risk
    if final_score < 60:
        risks.append(
            f"Overall match score of {round(final_score)}% is below the recommended threshold of 60% — "
            f"significant effort may be required to bring this candidate up to role readiness."
        )

    # ── OPPORTUNITIES ─────────────────────────────────────────────────────────
    opportunities = []
    if technical_fit >= 60:
        opportunities.append(
            f"Strong technical foundation offers potential to contribute rapidly to core product development "
            f"and take on more advanced responsibilities as they ramp up."
        )
    else:
        opportunities.append(
            f"Candidate shows growth potential; structured mentoring could accelerate skill development "
            f"and help bridge the gap to full role readiness."
        )
    if experience_years >= 3:
        opportunities.append(
            f"With {experience_years:.1f} years of experience, the candidate may bring fresh perspectives "
            f"and cross-domain insights from previous environments."
        )
    else:
        opportunities.append(
            f"As an early-career professional, the candidate can be shaped to fit team culture "
            f"and technical norms with relatively low friction."
        )
    opportunities.append(
        f"Opportunity to assess leadership potential and career growth trajectory during the interview, "
        f"which could reveal strengths not captured in the resume."
    )

    # ── NARRATIVE ─────────────────────────────────────────────────────────────
    score_label = (
        "excellent" if final_score >= 75 else
        "strong" if final_score >= 60 else
        "moderate" if final_score >= 45 else
        "limited"
    )
    rec_verb = {
        "Strong Hire": "is a highly competitive candidate and is recommended for fast-track consideration",
        "Hire": "meets the core requirements and is recommended for the next interview stage",
        "Hold": "shows partial alignment and warrants further evaluation before a hiring decision",
        "Reject": "does not sufficiently meet the technical or experience requirements for this role",
    }.get(recommendation, "requires further evaluation")

    narrative = (
        f"{name} demonstrates {score_label} alignment with the {job_title} role, "
        f"achieving a composite match score of {final_score:.0f}%. "
        f"Technical fit is rated at {round(technical_fit)}%, with experience relevance at {round(experience_relevance)}%. "
        f"Based on the evidence in this resume, {name} {rec_verb}."
    )

    return {
        "narrative": narrative,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:4],
        "risks": risks[:4],
        "opportunities": opportunities[:3],
        "recommendation": recommendation,
        "confidence": confidence,
        "recommendation_confidence": confidence,
        "interview_focus_areas": [
            f"Assess proficiency depth in {s}" for s in missing_skills[:3]
        ] + (
            ["Evaluate problem-solving approach on relevant domain scenarios"] if len(missing_skills) < 3 else []
        ),
        "hiring_red_flags": [rf for rf in risk_flags[:3]] if risk_flags else [],
        "hiring_green_flags": [f"Matched skill: {s}" for s in matched_skills[:3]] if matched_skills else ["Adequate profile for initial screening"],
        "salary_range_fit": "Senior" if experience_years >= 8 else "Mid" if experience_years >= 3 else "Junior",
        "onboarding_complexity": "Easy" if final_score >= 75 else "Medium" if final_score >= 50 else "Complex",
        "time_to_productivity": "Immediate" if final_score >= 80 else "1-2 weeks" if final_score >= 65 else "1 month" if final_score >= 48 else "2-3 months",
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
    on the candidate document. Guarantees ≥3 points per strengths/weaknesses/risks.
    """
    if candidate.get("hiring_summary") and candidate["hiring_summary"].get("recommendation"):
        existing = candidate["hiring_summary"]
        # Only reuse if it already has 3+ points per section (upgrade older 1-liners)
        if (
            len(existing.get("strengths", [])) >= 3 and
            len(existing.get("weaknesses", [])) >= 3 and
            len(existing.get("risks", [])) >= 3
        ):
            return existing

    name = candidate.get("name", "Candidate")
    job_title = job.get("title", "this role")
    final_score = float(candidate.get("score", 0))
    experience_years = float(candidate.get("experience_years", candidate.get("total_experience_years", 0)))

    score_breakdown = match_explanation.get("score_breakdown", {})
    tech_fit = float(score_breakdown.get("technical_fit", candidate.get("skill_score", 0)) or 0)
    exp_rel = float(score_breakdown.get("experience_relevance") or score_breakdown.get("exp_score", candidate.get("experience_score", 0)) or 0)
    res_quality = float(score_breakdown.get("resume_quality", candidate.get("resume_quality", 0)) or 0)
    semantic_score = float(candidate.get("semantic_score", 0) or 0)

    matched_skills = (
        match_explanation.get("exact_matches", []) +
        match_explanation.get("semantic_matches", [])
    )
    missing_skills = match_explanation.get("missing_skills", candidate.get("missing_skills", []))
    risk_flags = match_explanation.get("risk_flags", candidate.get("risk_flags", []))

    certifications = candidate.get("certifications", [])
    projects = candidate.get("projects_structured") or candidate.get("projects", [])
    employment_timeline = candidate.get("employment_timeline", [])
    soft_skills = candidate.get("soft_skills", [])

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
        certifications=certifications,
        projects=projects,
        employment_timeline=employment_timeline,
        soft_skills=soft_skills,
        semantic_score=semantic_score,
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
    summary["recommendation_confidence"] = confidence
    summary["generated_at"] = __import__("datetime").datetime.utcnow().isoformat()

    return summary
