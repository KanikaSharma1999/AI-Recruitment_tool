"""
Validation: 5 synthetic resumes → must produce realistic distribution
Expected:
  Excellent  → 80-100
  Good       → 65-82
  Average    → 45-67
  Weak       → 20-48
  Irrelevant → 0-22
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

# Compact JD with a focused set of required skills
JD_TEXT = """
Senior Python Backend Engineer (5+ years)

Required Skills:
- Python (mandatory)
- FastAPI (mandatory)
- MongoDB (mandatory)
- Docker (required)
- Kubernetes (required)
- PostgreSQL or any SQL database
- REST API design
- pytest / unit testing
- CI/CD pipelines

Nice to have: AWS, Redis, Microservices architecture
"""

# ── Synthetic resumes ────────────────────────────────────────────────────────

EXCELLENT = {
    "label": "Excellent",
    "skills": ["python","fastapi","mongodb","docker","kubernetes","postgresql",
               "redis","aws","rest api","pytest","ci/cd","microservices","linux"],
    "experience_years": 7.0,
    "raw_text": "Arjun Mehta arjun@email.com Bangalore\n"
                "7 years of professional Python backend experience.\n"
                "Skills: Python, FastAPI, MongoDB, Docker, Kubernetes, PostgreSQL, Redis, AWS, "
                "REST API, pytest, CI/CD, Microservices, Linux\n"
                "Senior Backend Engineer @ TechCorp 2020-Present: FastAPI microservices, Kubernetes.\n"
                "Designed and implemented high-throughput REST APIs and microservice endpoints.\n"
                "Backend Engineer @ Startup XYZ 2018-2020: Python/Django, Docker containerization.\n"
                "Junior Dev @ Infosys 2016-2018: Python, PostgreSQL database optimization.\n"
                "Project 1: Distributed Job Scheduler (FastAPI+MongoDB+Kubernetes)\n"
                "Project 2: Real-time Analytics Pipeline (Python, Redis, PostgreSQL)\n"
                "Certifications: AWS Certified Developer, Kubernetes CKA\n"
                "B.Tech Computer Science IIT Bombay 2016",
    "timeline": [
        {"company":"TechCorp","title":"Senior Backend Engineer","start_date":"2020","end_date":"Present","is_internship":False,"is_freelance":False},
        {"company":"Startup XYZ","title":"Backend Engineer","start_date":"2018","end_date":"2020","is_internship":False,"is_freelance":False},
        {"company":"Infosys","title":"Junior Developer","start_date":"2016","end_date":"2018","is_internship":False,"is_freelance":False},
    ],
}

GOOD = {
    "label": "Good",
    "skills": ["python","fastapi","mysql","docker","rest api","git","linux","pytest","postgresql"],
    "experience_years": 4.0,
    "raw_text": "Priya Sharma priya@email.com Pune\n"
                "4 years backend development experience working in agile environments.\n"
                "Skills: Python, FastAPI, MySQL, PostgreSQL, Docker, REST API, Git, Linux, pytest\n"
                "Backend Developer @ Wipro 2021-Present: FastAPI services, Docker deployments.\n"
                "Built multiple REST APIs using FastAPI, deployed using Docker containers on dev clusters.\n"
                "Software Engineer @ TCS 2020-2021: Python scripting, REST APIs, MySQL.\n"
                "Participated in agile planning, sprint reviews, and codebase maintenance.\n"
                "Project 1: E-commerce API (FastAPI+MySQL)\n"
                "Project 2: Inventory Management (Python, REST API)\n"
                "B.E. Computer Engineering Pune University 2019",
    "timeline": [
        {"company":"Wipro","title":"Backend Developer","start_date":"2021","end_date":"Present","is_internship":False,"is_freelance":False},
        {"company":"TCS","title":"Software Engineer","start_date":"2020","end_date":"2021","is_internship":False,"is_freelance":False},
    ],
}

AVERAGE = {
    "label": "Average",
    "skills": ["python","flask","sqlite","git","html","css","rest api"],
    "experience_years": 2.0,
    "raw_text": "Rahul Gupta rahul@email.com Hyderabad\n"
                "2 years software development experience. Focus on frontend and backend web applications.\n"
                "Skills: Python, Flask, SQLite, Git, HTML, CSS, REST API\n"
                "Software Developer @ Mediocre Tech 2022-Present: Flask REST APIs, SQLite database queries.\n"
                "Maintained simple endpoints, created clean HTML template pages, and fixed css bugs.\n"
                "Worked on user dashboards, database migrations, and simple security integrations.\n"
                "Project 1: Todo App (Flask)\n"
                "Project 2: Blog platform (Python, HTML)\n"
                "B.Sc Computer Science 2021",
    "timeline": [
        {"company":"Mediocre Tech","title":"Software Developer","start_date":"2022","end_date":"Present","is_internship":False,"is_freelance":False},
    ],
}

WEAK = {
    "label": "Weak",
    "skills": ["html","css","javascript","bootstrap","figma"],
    "experience_years": 0.0,
    "raw_text": "Sneha Patel sneha@example.com Mumbai\n"
                "Junior designer and front-end developer looking for opportunities.\n"
                "Skills: HTML, CSS, JavaScript, Bootstrap, Figma, wireframing, styling.\n"
                "Keen to learn and develop responsive interfaces using modern design systems.\n"
                "Collaborated on small student design briefs and mock-ups.\n"
                "Project 1: Portfolio website (HTML/CSS)\n"
                "Project 2: Mock design system for local store\n"
                "BCA 2023",
    "timeline": [],
}

IRRELEVANT = {
    "label": "Irrelevant",
    "skills": ["excel","communication","powerpoint","salesforce"],
    "experience_years": 6.0,
    "raw_text": "Kiran Nair kiran@email.com Delhi\n"
                "6 years in sales and marketing with record of exceeding targets.\n"
                "Skills: MS Excel, PowerPoint, Salesforce CRM, Negotiation, B2B Communication\n"
                "Senior Sales Executive @ FMCG 2018-Present: Managed client accounts, tracked sales targets.\n"
                "Led team of junior representatives, optimized CRM sales pipelines, boosted customer retention.\n"
                "Sales Rep @ Insurance Co 2017-2018: Cold calling, lead qualification, and territory sales.\n"
                "Project 1: Customer Relationship Pipeline optimization\n"
                "Project 2: Sales Campaign expansion plan\n"
                "MBA Marketing 2017",
    "timeline": [
        {"company":"FMCG","title":"Senior Sales Executive","start_date":"2018","end_date":"Present","is_internship":False,"is_freelance":False},
    ],
}

RESUMES = [EXCELLENT, GOOD, AVERAGE, WEAK, IRRELEVANT]
EXPECTED_RANGES = {
    "Excellent":  (80, 100),
    "Good":       (60, 80),
    "Average":    (20, 45),
    "Weak":       (0, 20),
    "Irrelevant": (0, 25),
}


def run_test():
    from matching import (
        compute_skill_scores, compute_semantic_similarity,
        calculate_experience_breakdown, compute_quality_score,
        score_to_verdict, _clamp,
    )
    from services.llm_parser import parse_jd_local_fallback

    jd_profile = parse_jd_local_fallback(JD_TEXT)
    required_skills = jd_profile.get("required_skills", [])
    minimum_exp = float(jd_profile.get("minimum_experience", 0.0) or 0.0)

    print(f"\nJD Required Skills ({len(required_skills)}): {required_skills}")
    print(f"JD Minimum Experience: {minimum_exp} yrs\n")
    print("=" * 70)

    results = []
    for r in RESUMES:
        label = r["label"]
        raw   = r["raw_text"]
        skills = r["skills"]
        exp_yrs = r["experience_years"]
        timeline = r["timeline"]

        skill_score, exact, sem_m, partial, missing = compute_skill_scores(required_skills, skills)
        sem_score = compute_semantic_similarity(JD_TEXT, raw)

        exp_bd = calculate_experience_breakdown(timeline, exp_yrs, required_skills)
        relevant_exp = exp_bd["relevant_experience"]
        total_exp = exp_bd["total_experience"]
        effective_exp = max(relevant_exp, total_exp)

        if minimum_exp <= 0:
            exp_score = _clamp(min(100.0, 20.0 + effective_exp * 16.0))
        else:
            if effective_exp >= minimum_exp:
                exp_score = 100.0
            else:
                ratio = effective_exp / minimum_exp
                exp_score = _clamp(ratio * 100.0)

        proj_count = sum(1 for l in raw.split('\n') if 'project' in l.lower() and len(l) > 10)
        proj_score = 70.0 if proj_count >= 2 else (50.0 if proj_count == 1 else 20.0)
        cert_score = 65.0

        fake_profile = {
            "email": "test@x.com",
            "employment_timeline": timeline,
            "total_experience_years": exp_yrs,
            "confidence_score": 75.0,
            "extraction_reliability": "Medium",
        }
        quality_score, qpen = compute_quality_score(fake_profile, raw)

        raw_final = (
            skill_score * 0.40
            + exp_score  * 0.25
            + sem_score  * 0.15
            + proj_score * 0.10
            + cert_score * 0.05
            + quality_score * 0.05
        )

        penalties = []
        if required_skills:
            n = len(required_skills)
            mr = len(missing) / n
            if mr >= 0.7:
                raw_final -= 20; penalties.append(f">70% req skills missing -20")
            elif mr >= 0.5:
                raw_final -= 12; penalties.append(f">50% req skills missing -12")
            elif mr >= 0.3 and skill_score < 50:
                raw_final -= 6;  penalties.append(f">30% req skills missing -6")

        if minimum_exp > 0 and effective_exp < minimum_exp * 0.5:
            raw_final -= 10; penalties.append("exp severely below req -10")
        if len(raw) < 500:
            raw_final -= 10; penalties.append("short resume -10")

        conf = fake_profile.get("confidence_score", 75)
        if conf < 50:
            raw_final -= 8; penalties.append("low confidence -8")

        final = _clamp(raw_final)
        verdict = score_to_verdict(final)

        results.append((label, final, verdict))
        print(f"[{label:10s}] final={final:5.1f}  skill={skill_score:5.1f}  "
              f"exp={exp_score:5.1f}  sem={sem_score:4.1f}  "
              f"proj={proj_score:4.1f}  verdict={verdict}")
        if missing:
            print(f"             missing({len(missing)}): {missing[:5]}")
        if penalties:
            print(f"             penalties: {penalties}")

    print("\n" + "=" * 70)
    print("DISTRIBUTION CHECK:")
    all_pass = True
    for label, score, verdict in results:
        lo, hi = EXPECTED_RANGES[label]
        passed = lo <= score <= hi
        if not passed:
            all_pass = False
        status = "PASS" if passed else f"FAIL (expected {lo}-{hi})"
        print(f"  {label:10s}: {score:5.1f}  {verdict:22s}  {status}")

    print()
    print("ALL DISTRIBUTION CHECKS PASSED" if all_pass else
          "Some checks failed -- review scoring weights above.")
    return all_pass


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)
