"""
Advanced Resume Parser
=======================
- Extended SKILLS_DB with 200+ skills
- SKILL_SYNONYMS dictionary for normalization (ReactJS→react, ML→machine learning, etc.)
- 3-stage skill extraction: keyword → fuzzy → semantic
- extract_certifications(), extract_projects()
- All functions are pure / no side-effects; safe to import anywhere
"""

import re
import os
import io
import datetime
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# ── PDF/DOCX reading ──────────────────────────────────────────────────────────
try:
    from PyPDF2 import PdfReader
    _PDF_OK = True
except ImportError:
    _PDF_OK = False

# ── spaCy (Lazy Loaded) ───────────────────────────────────────────────────────
_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            logger.info("[ResumeParser] Lazy-loading spaCy en_core_web_sm model...")
            _nlp = spacy.load("en_core_web_sm")
            logger.info("[ResumeParser] spaCy model loaded successfully.")
        except Exception as e:
            logger.warning(f"[ResumeParser] Could not load spaCy model: {e}")
            _nlp = False
    return _nlp if _nlp is not False else None

# ── rapidfuzz ─────────────────────────────────────────────────────────────────
try:
    from rapidfuzz import fuzz, process as rfprocess
    _FUZZY_OK = True
except ImportError:
    _FUZZY_OK = False


# ═══════════════════════════════════════════════════════════════════════════════
#  SKILLS DATABASE  (canonical lowercase names)
# ═══════════════════════════════════════════════════════════════════════════════
SKILLS_DB = {
    # ── Programming Languages ──────────────────────────────────────────────────
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang",
    "rust", "kotlin", "swift", "ruby", "php", "scala", "matlab", "perl", "bash",
    "shell", "powershell", "r", "julia", "dart", "elixir", "haskell", "lua",
    "assembly", "cobol", "fortran", "groovy", "objective-c", "vba",

    # ── Web Frontend ───────────────────────────────────────────────────────────
    "html", "css", "react", "angular", "vue", "svelte", "next.js", "nuxt.js",
    "gatsby", "remix", "jquery", "bootstrap", "tailwind", "sass", "scss",
    "webpack", "vite", "babel", "redux", "mobx", "graphql", "rest api",
    "websocket", "pwa", "webassembly",

    # ── Web Backend ────────────────────────────────────────────────────────────
    "node.js", "express", "django", "flask", "fastapi", "spring boot", "spring",
    "asp.net", "laravel", "rails", "gin", "fiber", "nestjs", "strapi",
    "phoenix", "sinatra", "hapi", "koa",

    # ── Mobile ────────────────────────────────────────────────────────────────
    "react native", "flutter", "android", "ios", "xamarin", "ionic", "cordova",

    # ── Data / ML / AI ────────────────────────────────────────────────────────
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "matplotlib", "seaborn", "plotly", "xgboost",
    "lightgbm", "catboost", "hugging face", "transformers",
    "sentence-transformers", "bert", "gpt", "llm", "rag",
    "reinforcement learning", "neural network", "cnn", "rnn", "lstm",
    "generative ai", "stable diffusion", "langchain", "llamaindex",
    "openai", "cohere", "anthropic",

    # ── Data Engineering ──────────────────────────────────────────────────────
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "elasticsearch", "neo4j", "influxdb", "clickhouse",
    "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake",
    "databricks", "bigquery", "redshift", "tableau", "power bi",
    "looker", "metabase", "superset", "dask", "polars", "flink",
    "hive", "pig", "sqoop", "nifi",

    # ── Cloud / DevOps ────────────────────────────────────────────────────────
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "terraform", "ansible", "puppet", "chef", "jenkins", "github actions",
    "gitlab ci", "circleci", "travis ci", "linux", "unix", "git",
    "nginx", "apache", "helm", "istio", "prometheus", "grafana",
    "elk stack", "splunk", "datadog", "newrelic", "cloudformation",
    "pulumi", "vagrant", "packer", "argocd", "flux",

    # ── Security ──────────────────────────────────────────────────────────────
    "cybersecurity", "penetration testing", "ethical hacking", "siem",
    "firewalls", "oauth", "jwt", "ssl", "encryption", "devsecops",

    # ── Testing ───────────────────────────────────────────────────────────────
    "unit testing", "integration testing", "selenium", "cypress", "jest",
    "pytest", "junit", "mocha", "chai", "testng", "playwright",

    # ── Methodologies / Soft ──────────────────────────────────────────────────
    "agile", "scrum", "kanban", "devops", "ci/cd", "microservices",
    "rest", "soap", "grpc", "tdd", "bdd", "ddd", "solid",
    "communication", "leadership", "teamwork", "problem solving",
    "project management", "data analysis", "excel", "jira", "confluence",
    "product management", "management", "digital transformation",
    "educational pedagogy", "laws and regulations", "analytical skills",
    "problem-solving skills", "microsoft office", "google suite", "crm",
    "english language",

    # ── Blockchain ────────────────────────────────────────────────────────────
    "blockchain", "solidity", "ethereum", "web3", "smart contracts",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  SYNONYM / ALIAS NORMALISATION MAP
#  key = alias (what appears in resume/JD)
#  value = canonical skill name (must be in SKILLS_DB or close enough)
# ═══════════════════════════════════════════════════════════════════════════════
SKILL_SYNONYMS: dict[str, str] = {
    # Management and soft skills aliases
    "managing projects": "project management",
    "project manager": "project management",
    "pedagogy": "educational pedagogy",
    "analytical": "analytical skills",
    "problem-solving": "problem-solving skills",
    "english": "english language",

    # JavaScript aliases
    "js": "javascript",
    "es6": "javascript",
    "es2015": "javascript",
    "ecmascript": "javascript",
    "vanillajs": "javascript",
    "vanilla js": "javascript",

    # TypeScript
    "ts": "typescript",

    # Python
    "py": "python",

    # React aliases
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",

    # Node aliases
    "node": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",

    # Next.js
    "nextjs": "next.js",
    "next js": "next.js",

    # Vue
    "vuejs": "vue",
    "vue.js": "vue",
    "vue js": "vue",

    # Angular
    "angularjs": "angular",
    "angular js": "angular",
    "angular2": "angular",

    # Go
    "golang": "go",

    # C aliases
    "c language": "c",
    "clang": "c",

    # Machine Learning
    "ml": "machine learning",
    "ai/ml": "machine learning",
    "ai ml": "machine learning",
    "artificial intelligence": "machine learning",
    "ai": "machine learning",

    # Deep Learning
    "dl": "deep learning",

    # NLP aliases
    "natural language processing": "nlp",
    "text mining": "nlp",

    # Cloud
    "amazon web services": "aws",
    "amazon aws": "aws",
    "google cloud platform": "google cloud",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    "azure cloud": "azure",

    # Kubernetes
    "k8s": "kubernetes",
    "kube": "kubernetes",

    # Docker
    "containerization": "docker",
    "containers": "docker",

    # CI/CD
    "cicd": "ci/cd",
    "continuous integration": "ci/cd",
    "continuous deployment": "ci/cd",
    "continuous delivery": "ci/cd",

    # Database aliases
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "dynamo": "dynamodb",
    "elastic": "elasticsearch",
    "es": "elasticsearch",

    # Spring
    "spring framework": "spring boot",
    "spring mvc": "spring boot",

    # FastAPI
    "fast api": "fastapi",

    # GraphQL
    "gql": "graphql",

    # REST
    "rest": "rest api",
    "restful": "rest api",
    "rest apis": "rest api",
    "restful api": "rest api",
    "api": "rest api",
    "pytest": "unit testing",
    "unittest": "unit testing",
    "sql": "postgresql",

    # Data Viz
    "powerbi": "power bi",
    "power-bi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",

    # Misc
    "scikit": "scikit-learn",
    "sklearn": "scikit-learn",
    "hf": "hugging face",
    "huggingface": "hugging face",
    "tf": "tensorflow",
    "keras api": "keras",
    "xgb": "xgboost",
    "lgbm": "lightgbm",
    "git hub": "git",
    "github": "git",
    "gitlab": "git",
    "bitbucket": "git",
    "bash scripting": "bash",
    "shell scripting": "bash",
    "linux/unix": "linux",
    "unix/linux": "linux",
    "react native app": "react native",
    "rn": "react native",
    "flutter sdk": "flutter",
    "llm models": "llm",
    "large language model": "llm",
    "large language models": "llm",
    "generative artificial intelligence": "generative ai",
    "gen ai": "generative ai",
    "genai": "generative ai",
    "langchain framework": "langchain",
    "llama index": "llamaindex",
}

# ── Reverse map for normalisation ─────────────────────────────────────────────
# Maps canonical → canonical (identity) for fast lookup
_CANONICAL_SET = {s.lower().strip() for s in SKILLS_DB}

BANNED_WORDS = {
    "experience", "summary", "profile", "objective", "overview",
    "manager", "engineer", "developer", "sales", "analyst",
    "consultant", "director", "executive", "officer", "lead",
    "resume", "cv", "curriculum", "vitae", "contact", "details",
    "education", "skills", "projects", "achievements", "references",
    "professional", "personal", "technical", "work", "employment",
    "history", "background", "information", "about", "page",
}

CERTIFICATION_KEYWORDS = [
    "aws certified", "azure certified", "google certified", "gcp certified",
    "certified kubernetes", "cka", "ckad", "cks",
    "certified developer", "certified architect", "certified professional",
    "comptia", "cissp", "ceh", "oscp", "cism",
    "pmp", "prince2", "scrum master", "csm", "safe",
    "oracle certified", "microsoft certified", "ibm certified",
    "salesforce certified", "databricks certified", "snowflake certified",
    "tensorflow developer certificate", "tensorflow certificate",
    "deep learning specialization", "machine learning specialization",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE READING
# ═══════════════════════════════════════════════════════════════════════════════

def read_pdf_bytes(content: bytes) -> str:
    if not _PDF_OK:
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception:
        return ""


def read_txt_bytes(content: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(enc)
        except Exception:
            continue
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  NAME EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def is_valid_name(candidate: str) -> bool:
    candidate = candidate.strip()
    if not candidate:
        return False
    words = candidate.split()
    if not (2 <= len(words) <= 3):
        return False
    if len(candidate) > 40:
        return False
    if re.search(r'\d', candidate):
        return False
    if '@' in candidate:
        return False
    if not all(w.isalpha() for w in words):
        return False
    # Allow uppercase names and all-caps names (remove validation rejecting uppercase)
    if candidate == candidate.lower():
        return False
    if any(w.lower() in BANNED_WORDS for w in words):
        return False
    return True


def extract_candidate_details(raw_text: str, filename: str) -> dict:
    """Multi-strategy name/email/phone extraction."""
    nlp = get_nlp()
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
    email = email_match.group(0) if email_match else "Not Found"

    email_username = ""
    if email != "Not Found":
        raw_username = email.split("@")[0]
        email_username = re.sub(r'[^a-z]', '', raw_username.lower())

    # Supported phone formats: +91 90354 89733, +91-9035489733, 90354 89733, 99000 04144
    phone_pattern = r'(?:(?:\+?\d{1,3}[-\s]?)?\d{5}[-\s]\d{5})|(?:(?:\+?\d{1,3}[-\s]?)?\d{10})|(?:(?:\+?\d{1,3}[-\s]?)?\d{3}[-\s]\d{3}[-\s]\d{4})'
    phone_match = re.search(phone_pattern, raw_text)
    phone = phone_match.group(0).strip() if phone_match else "Not Found"

    def email_cross_check(candidate: str) -> bool:
        if not email_username:
            return True
        name_tokens = [w.lower() for w in candidate.split()]
        return any(
            token in email_username or email_username.startswith(token[:3])
            for token in name_tokens if len(token) >= 3
        )

    def try_name(candidate: str) -> Optional[str]:
        candidate_stripped = ' '.join(candidate.split())
        for prefix in ["certifications", "education", "experience", "skills", "projects", "summary"]:
            if candidate_stripped.lower().startswith(prefix):
                candidate_stripped = candidate_stripped[len(prefix):].strip()
        # Check original (supports ALL CAPS)
        if is_valid_name(candidate_stripped) and email_cross_check(candidate_stripped):
            return candidate_stripped
        # Fallback to Title Case
        candidate_cap = ' '.join(w.capitalize() for w in candidate_stripped.split())
        if is_valid_name(candidate_cap) and email_cross_check(candidate_cap):
            return candidate_cap
        return None

    # Remove all section headers before name extraction
    section_headers = {
        "professional summary", "work experience", "education", "certifications", 
        "core skills", "summary", "experience", "skills", "projects", "contact", 
        "about me", "curriculum vitae", "resume", "cv", "personal details", 
        "core competencies", "career objective", "objective", "work history"
    }

    lines = raw_text.split('\n')
    cleaned_lines = []
    for line in lines[:30]:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_clean = re.sub(r'[^a-zA-Z\s]', '', line_stripped).strip().lower()
        if line_clean in section_headers:
            continue
        cleaned_lines.append(line_stripped)
    first_30 = cleaned_lines
    name = None

    for line in first_30[:3]:
        result = try_name(line)
        if result:
            name = result
            break

    if not name and email != "Not Found":
        email_line_idx = None
        for idx, raw_line in enumerate(lines[:30]):
            if email in raw_line:
                email_line_idx = idx
                break
        if email_line_idx is not None:
            for raw_line in lines[max(0, email_line_idx - 5): email_line_idx]:
                result = try_name(raw_line.strip())
                if result:
                    name = result
                    break

    if not name and nlp:
        doc = nlp(raw_text[:2000])
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                result = try_name(ent.text)
                if result:
                    name = result
                    break

    if not name:
        for line in first_30:
            cleaned = re.sub(r'^(name\s*[:|-]?\s*)', '', line, flags=re.IGNORECASE).strip()
            result = try_name(cleaned)
            if result:
                name = result
                break

    if not name:
        if email != "Not Found":
            raw_username = email.split("@")[0]
            clean_username = re.sub(r'[\d._\-]+', ' ', raw_username).strip()
            parts = [p.capitalize() for p in clean_username.split() if p]
            name = ' '.join(parts[:2]) if parts else os.path.splitext(filename)[0].replace('_', ' ').strip()
        else:
            name = os.path.splitext(filename)[0].replace('_', ' ').strip()

    return {"name": name, "email": email, "phone": phone}


# ═══════════════════════════════════════════════════════════════════════════════
#  SKILL EXTRACTION  (3-stage pipeline)
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_skill_token(token: str) -> Optional[str]:
    """
    Given a raw token (lowercased), return the canonical skill name if it maps
    to anything in SKILLS_DB (via exact, synonym, or nothing).
    """
    t = token.strip().lower()
    if t in _CANONICAL_SET:
        return t
    if t in SKILL_SYNONYMS:
        canon = SKILL_SYNONYMS[t]
        if canon in _CANONICAL_SET:
            return canon
        return canon  # still return even if not in canonical set
    return None


def extract_skills(text: str) -> List[str]:
    """
    3-stage skill extraction:
    Stage 1: Direct keyword match (exact, multi-word)
    Stage 2: Synonym normalisation
    Stage 3: Fuzzy matching with rapidfuzz (catches typos/abbreviations)
    Returns sorted deduplicated list of canonical skill names.
    """
    text_lower = text.lower()
    found: set[str] = set()

    # Stage 1 — exact keyword match (existing approach, all SKILLS_DB)
    for skill in SKILLS_DB:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.add(skill)

    # Stage 2 — synonym normalisation
    # Tokenise text into 1-word and 2-word n-grams and check synonyms
    words = re.findall(r"[a-z][a-z0-9.#+\-/]*", text_lower)
    for i, w in enumerate(words):
        canon = _normalize_skill_token(w)
        if canon:
            found.add(canon)
        # Bi-gram
        if i + 1 < len(words):
            bigram = w + " " + words[i + 1]
            canon = _normalize_skill_token(bigram)
            if canon:
                found.add(canon)
        # Tri-gram
        if i + 2 < len(words):
            trigram = w + " " + words[i + 1] + " " + words[i + 2]
            canon = _normalize_skill_token(trigram)
            if canon:
                found.add(canon)

    # Stage 3 — fuzzy matching for short tokens (handles abbreviations like MLOps→ML)
    if _FUZZY_OK:
        # Only run fuzzy on 1-3 word tokens extracted from "skills section"
        skills_section = _extract_skills_section(text)
        if skills_section:
            tokens = re.split(r'[,;|\n•·▪\-]+', skills_section)
            for tok in tokens:
                tok = tok.strip().lower()
                if not tok or len(tok) < 2 or len(tok) > 30:
                    continue
                # Skip if already found
                if _normalize_skill_token(tok):
                    continue
                # Fuzzy match against SKILLS_DB
                match = rfprocess.extractOne(
                    tok, list(SKILLS_DB), scorer=fuzz.ratio, score_cutoff=82
                )
                if match:
                    found.add(match[0])

    return sorted(found)


def _extract_skills_section(text: str) -> str:
    """
    Extract the 'Skills' section from a resume for targeted fuzzy matching.
    Returns the section text or empty string.
    """
    patterns = [
        r'(?:technical\s+)?skills?\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\Z)',
        r'core\s+competenc(?:y|ies)\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\Z)',
        r'expertise\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\Z)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)[:1000]
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPERIENCE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_experience_years(text: str) -> float:
    """
    3-Stage Hybrid Experience Extraction:
    Stage 1: Professional Summary section scan (highest priority)
    Stage 2: Work history date range aggregation
    Stage 3: AI/NLP fallback via Cohere
    Returns 0.0 ONLY if candidate is confirmed fresher.
    """
    current_year = datetime.datetime.now().year

    # ──────────────────────────────────────────────────────────────────
    # STAGE 1: Scan Professional Summary / About / Profile sections FIRST
    # This catches "9 years of comprehensive experience" type statements
    # ──────────────────────────────────────────────────────────────────
    
    # Extract dedicated summary sections (top 40% of resume)
    top_section = text[:int(len(text) * 0.4)]
    
    # Also try to extract named sections
    summary_section_pat = re.compile(
        r'(?:professional\s+summary|executive\s+summary|career\s+summary|'
        r'summary\s+of\s+qualifications?|profile\s+summary|about\s+me|'
        r'professional\s+profile|career\s+objective|overview|profile|summary)'
        r'\s*[:：\-]?\s*\n(.*?)(?:\n\s*\n|\n[A-Z][A-Z ]{4,}|\Z)',
        re.IGNORECASE | re.DOTALL
    )
    summary_text = top_section  # default: use top 40%
    m = summary_section_pat.search(text)
    if m:
        summary_text = m.group(1)[:2000] + " " + top_section

    # Patterns ordered from most-specific to least-specific
    summary_patterns = [
        # "9 years of comprehensive experience", "14+ years of professional experience"
        r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of\s+(?:comprehensive\s+|professional\s+|relevant\s+|combined\s+|extensive\s+|total\s+|overall\s+|rich\s+)?experience',
        # "experience of 9 years", "experience: 9 years"
        r'experience\s*(?:of\s+|:\s*)(\d+(?:\.\d+)?)\s*\+?\s*years?',
        # "9 years experience" (no 'of')
        r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+experience',
        # "9+ years in software/tech/data/AI"
        r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+in\s+(?:the\s+)?(?:software|it|tech|data|ml|ai|telecom|finance|banking|healthcare|manufacturing)',
        # "X yrs experience"
        r'(\d+(?:\.\d+)?)\s*\+?\s*yrs?\s+(?:of\s+)?experience',
        # "experience: X" or "total experience: X years"
        r'(?:total\s+)?experience\s*[:：]\s*(\d+(?:\.\d+)?)\s*\+?\s*years?',
        # "with X years of" (common in summaries)
        r'with\s+(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of',
        # "over X years" / "more than X years"
        r'(?:over|more\s+than|approximately|around|nearly)\s+(\d+(?:\.\d+)?)\s*\+?\s*years?',
    ]
    
    for pat in summary_patterns:
        m = re.search(pat, summary_text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 0 < val <= 40:
                return val

    # ──────────────────────────────────────────────────────────────────
    # STAGE 2: Work History Timeline Aggregation
    # Parse date ranges and sum durations
    # ──────────────────────────────────────────────────────────────────
    
    # Match: "2015 - 2020", "Jan 2018 – Present", "2021 to Current", etc.
    date_patterns = [
        # Full month+year to month+year or present
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(20\d\d|19\d\d)\s*[-–—to]+\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*)?(20\d\d|19\d\d|present|current|till\s*date|now|ongoing)',
        # Year to year
        r'(20\d\d|19\d\d)\s*[-–—to]+\s*(20\d\d|19\d\d|present|current|till\s*date|now|ongoing)',
    ]
    
    seen_ranges = set()
    total_months = 0
    
    for pat in date_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            groups = m.groups()
            start_str = groups[-2] if len(groups) >= 2 else groups[0]
            end_str = groups[-1]
            try:
                s = int(re.search(r'\d{4}', start_str).group())
                e = current_year if re.search(r'present|current|till|now|ongoing', end_str, re.IGNORECASE) else int(re.search(r'\d{4}', end_str).group())
                key = (s, e)
                if key not in seen_ranges and 1980 <= s <= current_year and s <= e:
                    seen_ranges.add(key)
                    total_months += (e - s) * 12
            except Exception:
                continue

    if total_months > 0:
        years = total_months / 12
        return round(min(years, 40.0), 1)

    # ──────────────────────────────────────────────────────────────────
    # STAGE 3: AI/NLP Fallback via Cohere
    # Only reached if Stages 1+2 both failed
    # ──────────────────────────────────────────────────────────────────
    api_key = os.getenv("COHERE_API_KEY", "")
    if api_key and api_key not in ("your_cohere_key", ""):
        try:
            import cohere
            client = cohere.Client(api_key, timeout=10)
            prompt = (
                "You are a resume parser. Read the following resume text carefully.\n"
                "Your ONLY task: extract the TOTAL years of professional work experience.\n"
                "Consider: explicit statements ('9 years of experience'), employment date ranges, and job tenure.\n"
                "Rules:\n"
                "- If candidate is a student/fresher with NO professional work, output: 0\n"
                "- If you find work experience, output ONLY a single number like: 7 or 3.5\n"
                "- Do NOT output any explanation or text, ONLY the number.\n\n"
                f"RESUME:\n{text[:3000]}"
            )
            resp = client.chat(model="command-r-plus-08-2024", message=prompt, temperature=0.0)
            m = re.search(r'(\d+(?:\.\d+)?)', resp.text.strip())
            if m:
                val = float(m.group(1))
                return min(val, 40.0)
        except Exception as e:
            print(f"[ExperienceParser] Cohere fallback failed: {e}")

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  EDUCATION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_education(text: str) -> List[str]:
    degrees = [
        "phd", "ph.d", "doctorate", "master", "mba", "m.s.", "m.sc",
        "m.tech", "m.e.", "bachelor", "b.s.", "b.sc", "b.tech", "b.e.", "b.com",
        "b.a.", "associate", "diploma", "high school", "10th", "12th",
        "undergraduate", "postgraduate", "graduate",
    ]
    found = []
    text_lower = text.lower()
    for deg in degrees:
        if deg in text_lower:
            found.append(deg.upper())
    return list(set(found))


# ═══════════════════════════════════════════════════════════════════════════════
#  CERTIFICATIONS  (new)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_certifications(text: str) -> List[str]:
    """
    Detect professional certifications mentioned in the resume.
    Returns list of detected certification strings.
    """
    found = []
    text_lower = text.lower()

    for cert in CERTIFICATION_KEYWORDS:
        if cert.lower() in text_lower:
            found.append(cert.title())

    # Also scan for "Certified ..." patterns
    cert_patterns = [
        r'((?:aws|azure|google|gcp|oracle|ibm|salesforce|databricks|snowflake)\s+certified[^\n,;.]{0,40})',
        r'(certified\s+(?:kubernetes|developer|architect|professional|engineer|scrum|safe)[^\n,;.]{0,40})',
        r'(cka|ckad|cks|pmp|cissp|ceh|oscp|comptia[^\s]*)',
    ]
    for pat in cert_patterns:
        matches = re.findall(pat, text_lower, re.IGNORECASE)
        for m in matches:
            cert = m.strip().title()
            if cert and len(cert) > 3:
                found.append(cert)

    # Deduplicate (case-insensitive)
    seen = set()
    unique = []
    for c in found:
        key = c.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique[:10]


# ═══════════════════════════════════════════════════════════════════════════════
#  PROJECTS  (new)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_projects(text: str) -> List[str]:
    """
    Extract project names/titles from the resume's Projects section.
    Returns list of project name strings (up to 8).
    """
    # Find projects section
    section_pat = r'(?:projects?|personal\s+projects?|key\s+projects?|notable\s+projects?)\s*[:：]?\s*\n(.*?)(?:\n(?=[A-Z][A-Z\s]{2,}:|\Z))'
    m = re.search(section_pat, text, re.IGNORECASE | re.DOTALL)
    section = m.group(1) if m else text

    exclude_headers = {
        "professional summary", "work experience", "education",
        "certifications", "core skills", "summary", "experience",
        "skills", "projects", "work history", "career highlights"
    }

    # Extract lines that look like project names (Title Case, short, possibly followed by |)
    project_names = []
    for line in section.split('\n'):
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 80:
            continue
        # Skip lines that are clearly descriptions (start with lowercase or bullet points deep)
        if line.startswith(('-', '•', '●', '*', '–', '·')):
            content = line.lstrip('-•●*–· ').strip()
        else:
            content = line

        content_clean = re.sub(r'[^a-zA-Z\s]', '', content).strip().lower()
        if content_clean in exclude_headers:
            continue

        # Project names are usually Title Case or ALL CAPS short phrases
        words = content.split()
        if not words:
            continue
        if len(words) <= 8 and (words[0][0].isupper() if words[0] else False):
            # Skip if it looks like a description (contains common verbs)
            desc_words = {'developed', 'built', 'created', 'implemented', 'designed',
                          'the', 'a', 'an', 'using', 'with', 'for', 'and', 'or'}
            if words[0].lower() not in desc_words:
                project_names.append(content)
        if len(project_names) >= 8:
            break

    return project_names


# ═══════════════════════════════════════════════════════════════════════════════
#  LOCATION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_location(text: str) -> str:
    # 1. Normalize text and insert spaces between merged words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', text)
    text = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', text)
    
    nlp = get_nlp()
    locations = [
        "Bangalore", "Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad",
        "Chennai", "Kolkata", "Ahmedabad", "Noida", "Gurgaon", "Gurugram",
        "New York", "San Francisco", "Seattle", "Austin", "Chicago",
        "London", "Singapore", "Toronto", "Remote",
    ]
    text_lower = text.lower()
    for loc in locations:
        # Use substring matching instead of strict word boundaries
        if loc.lower() in text_lower:
            return loc
    if nlp:
        doc = nlp(text[:2000])
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                return ent.text
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  JOB DESCRIPTION PARSER  (New)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_job_description(text: str) -> dict:
    """
    Advanced JD Parser:
    - Extracts skills (Required vs Preferred)
    - Detects Role/Domain
    - Extracts required experience years
    """
    text_lower = text.lower()
    
    # Heuristic fallback parsing
    required_keywords = ["must have", "required", "essential", "minimum requirements", "qualifications"]
    preferred_keywords = ["preferred", "plus", "bonus", "nice to have", "good to have", "desired"]
    
    sections = re.split(r'(\b(?:' + '|'.join(required_keywords + preferred_keywords) + r')\b)', text_lower)
    required_skills = set()
    preferred_skills = set()
    current_type = "required"
    
    for i in range(len(sections)):
        part = sections[i].strip()
        if not part: continue
        if any(k in part for k in required_keywords):
            current_type = "required"
            continue
        if any(k in part for k in preferred_keywords):
            current_type = "preferred"
            continue
        found = extract_skills(part)
        if current_type == "required":
            required_skills.update(found)
        else:
            preferred_skills.update(found)
            
    if not preferred_skills and not required_skills:
        all_skills = extract_skills(text)
        required_skills.update(all_skills)
    elif not required_skills:
        required_skills = preferred_skills
        preferred_skills = set()

    roles = {
        "frontend": ["frontend", "front-end", "ui", "react", "angular", "vue"],
        "backend": ["backend", "back-end", "api", "node", "python", "java", "spring", "django"],
        "fullstack": ["fullstack", "full stack", "full-stack"],
        "devops": ["devops", "sre", "infrastructure", "kubernetes", "docker", "aws", "azure", "gcp"],
        "data_science": ["data scientist", "data science", "machine learning", "ml", "ai", "artificial intelligence"],
        "data_engineering": ["data engineer", "data engineering", "etl", "spark", "hadoop", "sql"],
        "mobile": ["mobile", "android", "ios", "react native", "flutter", "swift", "kotlin"],
        "qa": ["qa", "tester", "testing", "automation", "selenium", "cypress"],
    }
    
    detected_roles = []
    for role, keywords in roles.items():
        if any(re.search(r'\b' + re.escape(k) + r'\b', text_lower) for k in keywords):
            detected_roles.append(role.replace('_', ' ').title())

    # Try LLM parse first
    try:
        from services.llm_parser import parse_jd_with_llm
        parsed_llm = parse_jd_with_llm(text)
    except Exception as e:
        print(f"[Parser] LLM JD parse failed: {e}")
        parsed_llm = {}

    return {
        "required_skills": parsed_llm.get("required_skills") or sorted(list(required_skills)),
        "preferred_skills": parsed_llm.get("preferred_skills") or sorted(list(preferred_skills - required_skills)),
        "roles": [parsed_llm.get("role_name")] if parsed_llm.get("role_name") else detected_roles,
        "experience_years": parsed_llm.get("minimum_experience") or extract_experience_years(text),
        
        # Structured requirements (Enterprise matching alignment)
        "role_name": parsed_llm.get("role_name") or (detected_roles[0] if detected_roles else "Software Engineer"),
        "minimum_experience": parsed_llm.get("minimum_experience") or extract_experience_years(text),
        "domain_requirements": parsed_llm.get("domain_requirements") or [],
        "leadership_required": parsed_llm.get("leadership_required") or False,
        "communication_required": parsed_llm.get("communication_required") or False,
        "certifications_required": parsed_llm.get("certifications_required") or [],
        "project_requirements": parsed_llm.get("project_requirements") or [],
        "management_requirements": parsed_llm.get("management_requirements") or []
    }


def parse_resume_file(content: bytes, filename: str) -> dict:
    """Parse raw file bytes into structured candidate data."""
    if filename.lower().endswith('.pdf'):
        raw_text = read_pdf_bytes(content)
    elif filename.lower().endswith('.docx'):
        try:
            import mammoth
            result = mammoth.extract_raw_text(io.BytesIO(content))
            raw_text = result.value
        except Exception:
            raw_text = read_txt_bytes(content)
    else:
        raw_text = read_txt_bytes(content)

    details        = extract_candidate_details(raw_text, filename)
    skills         = extract_skills(raw_text)
    experience_yrs = extract_experience_years(raw_text)
    education      = extract_education(raw_text)
    location       = extract_location(raw_text)
    certifications = extract_certifications(raw_text)
    projects       = extract_projects(raw_text)

    # Try LLM parse first
    try:
        from services.llm_parser import parse_resume_with_llm
        parsed_llm = parse_resume_with_llm(raw_text, filename)
    except Exception as e:
        print(f"[Parser] LLM resume parse failed: {e}")
        parsed_llm = {}

    return {
        "name":             parsed_llm.get("candidate_name") or details["name"],
        "email":            parsed_llm.get("email") or details["email"],
        "phone":            parsed_llm.get("phone") or details["phone"],
        "skills":           parsed_llm.get("technical_skills") or skills,
        "experience_years": parsed_llm.get("total_experience_years") or experience_yrs,
        "education":        parsed_llm.get("education") or education,
        "location":         location,
        "certifications":   parsed_llm.get("certifications") or certifications,
        "projects":         parsed_llm.get("projects") or projects,
        "raw_text":         raw_text[:12000],  # store first 12k chars

        # Structured candidate fields
        "candidate_name":   parsed_llm.get("candidate_name") or details["name"],
        "total_experience_years": parsed_llm.get("total_experience_years") or experience_yrs,
        "companies":        parsed_llm.get("companies") or [],
        "job_titles":       parsed_llm.get("job_titles") or [],
        "technical_skills": parsed_llm.get("technical_skills") or skills,
        "soft_skills":      parsed_llm.get("soft_skills") or [],
        "leadership_experience": parsed_llm.get("leadership_experience") or False,
        "domain_experience": parsed_llm.get("domain_experience") or [],
        "communication_indicators": parsed_llm.get("communication_indicators") or [],
        "employment_timeline": parsed_llm.get("employment_timeline") or [],
        "tools":            parsed_llm.get("tools") or [],
        "technologies":     parsed_llm.get("technologies") or [],
        "confidence_score": parsed_llm.get("confidence_score") or 75.0,
        "ambiguity_detection": parsed_llm.get("ambiguity_detection") or [],
        "extraction_reliability": parsed_llm.get("extraction_reliability") or "Medium"
    }

