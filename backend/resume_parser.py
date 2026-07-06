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
    "product management",

    # ── Blockchain ────────────────────────────────────────────────────────────
    "blockchain", "solidity", "ethereum", "web3", "smart contracts",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  SYNONYM / ALIAS NORMALISATION MAP
#  key = alias (what appears in resume/JD)
#  value = canonical skill name (must be in SKILLS_DB or close enough)
# ═══════════════════════════════════════════════════════════════════════════════
SKILL_SYNONYMS: dict[str, str] = {
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
    # Resume section headers
    "experience", "summary", "profile", "objective", "overview",
    "resume", "cv", "curriculum", "vitae", "contact", "details",
    "education", "skills", "projects", "achievements", "references",
    "professional", "personal", "technical", "work", "employment",
    "history", "background", "information", "about", "page",
    "address", "phone", "email", "mobile",
    # Job titles / role keywords (catch multi-word PDF artifacts)
    "manager", "engineer", "developer", "sales", "analyst",
    "consultant", "director", "executive", "officer", "lead", "leader",
    "specialist", "coordinator", "associate", "intern", "head", "chief",
    "architect", "scientist", "researcher", "advisor", "strategist",
    "recruiter", "trainer", "instructor", "mentor", "coach",
    "president", "chairman", "founder", "co-founder",
    "product", "program", "project", "senior", "junior", "principal",
    "staff", "team", "group", "business", "operations", "technology",
    # Industry / domain words
    "edtech", "fintech", "healthtech", "blockchain", "startup", "saas",
    "brand", "marketing", "design", "strategy", "growth", "digital",
    "data", "cloud", "ai", "ml", "bi", "it", "iot",
    # Social / platform labels
    "linkedin", "github", "twitter", "portfolio", "link", "edin",
    # Location words
    "india", "bengaluru", "bangalore", "pune", "mumbai", "chennai",
    "delhi", "hyderabad", "kolkata", "singapore", "remote",
    "hiring", "recruitment", "candidate",
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

# Regex to detect LinkedIn / social URL artefacts in extracted text
_LINKEDIN_LINE_RE = re.compile(r'(?:linkedin|github|twitter|link\s*edin|in/|github\.com)', re.IGNORECASE)
# Patterns that indicate a line is a job title / designation (not a name)
_JOB_TITLE_RE = re.compile(
    r'\b(manager|engineer|developer|analyst|consultant|director|executive|officer|lead|'
    r'leader|specialist|coordinator|associate|intern|head|chief|architect|scientist|'
    r'researcher|advisor|strategist|recruiter|trainer|instructor|mentor|coach|'
    r'president|chairman|founder|co-founder|product|program|project|senior|junior|'
    r'principal|staff|edtech|fintech|healthtech|startup|saas|candidate)\b',
    re.IGNORECASE
)

def is_valid_name(candidate: str) -> bool:
    candidate = candidate.strip()
    if not candidate:
        return False
    words = candidate.split()
    if not (2 <= len(words) <= 4):
        return False
    if len(candidate) > 50:
        return False
    if re.search(r'\d', candidate):
        return False
    if '@' in candidate:
        return False
    if '.' in candidate and len(candidate) > 12:  # email-like without @
        return False
    # Detect concatenated email-domain tokens like "Shividhamijagmailcom" (no @, >18 chars)
    if any(len(w) > 18 for w in words):
        return False
    if not all(re.match(r"^[a-zA-Z\-\']+$", w) for w in words):
        return False
    # Reject lines that look like LinkedIn artefacts or job titles
    if _LINKEDIN_LINE_RE.search(candidate):
        return False
    if _JOB_TITLE_RE.search(candidate):
        return False
    # Filter out common section headers and location words
    if any(w.lower() in BANNED_WORDS for w in words):
        return False
    return True


def clean_extracted_email(email: str) -> str:
    if email == "Not Found":
        return email
    # Match the email pattern where the TLD is co/in/com/org/net etc.
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|mil|co|in|info|biz|me|us|uk|ca|de|fr|jp)\b', email, re.IGNORECASE)
    if match:
        return match.group(0)
    # Fallback to any 2-4 letter TLD
    match2 = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}\b', email)
    if match2:
        return match2.group(0)
    # If no word boundary, match up to capitalized transition (e.g. gmail.comMANALI)
    match3 = re.match(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|co|in|info|biz|me|us))([A-Z].*)', email)
    if match3:
        return match3.group(1)
    # Generic fallback
    match4 = re.match(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4})', email)
    if match4:
        return match4.group(1)
    return email


def extract_candidate_details(raw_text: str, filename: str) -> dict:
    """
    Multi-strategy name/email/phone extraction.
    6-strategy name cascade; labeled/regex/digit-scan for phone; space-robust email.
    """
    nlp = get_nlp()

    # 1. EMAIL: direct regex then space-collapsed fallback
    email = "Not Found"
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
    if email_match:
        email = clean_extracted_email(email_match.group(0))
    else:
        at_idx = raw_text.find("@")
        if at_idx != -1:
            chunk = raw_text[max(0, at_idx - 50):at_idx + 50]
            chunk_no_space = re.sub(r"\s+", "", chunk)
            m2 = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', chunk_no_space)
            if m2:
                email = clean_extracted_email(m2.group(0))

    email_username = ""
    if email != "Not Found":
        email_username = re.sub(r"[^a-z]", "", email.split("@")[0].lower())

    # 2. PHONE: labeled → +91 → 10-digit Indian → international → digit scan
    phone = "Not Found"

    # Priority 1: labeled field (Phone / Mobile / Contact / Tel / Whatsapp)
    labeled_m = re.search(
        r"(?:phone|mobile|contact|cell|ph|mob|tel|whatsapp)[.\s:\-]*"
        r"(\+?(?:[\d\s\-\(\)\.]{9,20}))",
        raw_text, re.IGNORECASE
    )
    if labeled_m:
        raw_ph = re.sub(r"[\s\-\(\)\.]", "", labeled_m.group(1))
        if 9 <= len(raw_ph) <= 15 and re.search(r"\d{7}", raw_ph):
            phone = labeled_m.group(1).strip()

    # Priority 2: +91 prefixed Indian mobile
    if phone == "Not Found":
        m = re.search(r"\+91[\s\-]?([6-9]\d{9})", raw_text)
        if m:
            phone = f"+91 {m.group(1)}"

    # Priority 3: standalone 10-digit Indian mobile (starts 6-9)
    if phone == "Not Found":
        for m in re.finditer(r"\b([6-9]\d{9})\b", raw_text):
            phone = m.group(1)
            break

    # Priority 4: international formatted numbers
    if phone == "Not Found":
        for pc in re.findall(
            r"(?:\+?[\d]{1,3}[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})",
            raw_text
        ):
            cleaned = re.sub(r"[\s\-\(\)\+\.]", "", pc)
            if 9 <= len(cleaned) <= 15:
                phone = pc.strip()
                break

    # Priority 5: dense-digit scan of first 1500 chars
    if phone == "Not Found":
        digits_only = re.sub(r"[^\d]", "", raw_text[:1500])
        m = re.search(r"[6-9]\d{9}", digits_only)
        if m:
            phone = m.group(0)
        else:
            m2 = re.search(r"\d{10}", digits_only)
            if m2:
                phone = m2.group(0)

    # 3. NAME: 6-strategy cascade
    def email_cross_check(candidate: str) -> bool:
        if not email_username or len(email_username) < 3:
            return True
        tokens = [w.lower() for w in candidate.split()]
        initials = "".join(w[0] for w in tokens if w)
        if initials in email_username or email_username in initials:
            return True
        return any(
            tok in email_username or email_username.startswith(tok[:3])
            for tok in tokens if len(tok) >= 3
        )

    def try_name(candidate: str, require_email: bool = False) -> Optional[str]:
        candidate = " ".join(candidate.split())
        candidate = re.sub(r"[^a-zA-Z\s\-]", "", candidate).strip()
        candidate = " ".join(w.capitalize() for w in candidate.split())
        if is_valid_name(candidate):
            if not require_email or email_cross_check(candidate):
                return candidate
        return None

    lines = raw_text.split("\n")
    first_30 = [ln.strip() for ln in lines[:40] if ln.strip()]

    # Merge adjacent short lines ONLY if both look like name tokens (no banned/role words)
    merged_lines = []
    i = 0
    while i < len(first_30):
        line = first_30[i]
        # Skip lines that are obviously not names before merging
        if _LINKEDIN_LINE_RE.search(line) or _JOB_TITLE_RE.search(line):
            merged_lines.append(line)
            i += 1
            continue
        words = line.split()
        if len(words) == 1 and i + 1 < len(first_30):
            nxt = first_30[i + 1].strip()
            nxt_words = nxt.split()
            combined = len(words) + len(nxt_words)
            # Only merge if the combined line is plausibly a name (2-4 words, no job title)
            combined_line = f"{line} {nxt}"
            if (2 <= combined <= 4
                    and not _LINKEDIN_LINE_RE.search(combined_line)
                    and not _JOB_TITLE_RE.search(combined_line)
                    and not any(w.lower() in BANNED_WORDS for w in combined_line.split())):
                merged_lines.append(combined_line)
                i += 2
                continue
        merged_lines.append(line)
        i += 1

    name = None

    # Strategy 1: first 4 merged lines, no email check
    for line in merged_lines[:4]:
        lo = line.lower()
        if any(w in BANNED_WORDS for w in lo.split()):
            continue
        if line.isupper() and len(line.split()) > 1:
            continue  # skip ALL-CAPS section headers
        result = try_name(line, require_email=False)
        if result:
            name = result
            break

    # Strategy 2: first 15 merged lines with email cross-check
    if not name:
        for line in merged_lines[:15]:
            lo = line.lower()
            if any(w in BANNED_WORDS for w in lo.split()):
                continue
            result = try_name(line, require_email=True)
            if result:
                name = result
                break

    # Strategy 3: lines immediately before the email line
    if not name and email != "Not Found":
        email_line_idx = None
        for idx, raw_line in enumerate(lines[:40]):
            if email.lower() in raw_line.lower() or (email_username and email_username in raw_line.lower()):
                email_line_idx = idx
                break
        if email_line_idx is not None:
            for raw_line in lines[max(0, email_line_idx - 6):email_line_idx]:
                result = try_name(raw_line.strip(), require_email=False)
                if result:
                    name = result
                    break

    # Strategy 4: explicit "Name:" label in first 2000 chars
    if not name:
        lbl_m = re.search(
            r"(?:^|\n)\s*(?:name|full\s+name|applicant)\s*[:\-]\s*([A-Z][a-z]+(?:[\s\-][A-Z][a-z]+){1,2})",
            raw_text[:2000], re.IGNORECASE | re.MULTILINE
        )
        if lbl_m:
            result = try_name(lbl_m.group(1).strip(), require_email=False)
            if result:
                name = result

    # Strategy 5: spaCy PERSON entity (NER)
    if not name and nlp:
        doc = nlp(raw_text[:3000])
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                result = try_name(ent.text, require_email=False)
                if result:
                    name = result
                    break

    # Strategy 6: derive from email username
    if not name and email != "Not Found":
        raw_username = email.split("@")[0]
        clean_username = re.sub(r"[\d._\-]+", " ", raw_username).strip()
        parts = [p.capitalize() for p in clean_username.split() if len(p) >= 2]
        if len(parts) >= 2:
            name = " ".join(parts[:3])

    # Fallback: filename stem
    if not name:
        stem = os.path.splitext(filename)[0]
        stem_clean = re.sub(r"[\d_\-]+", " ", stem).strip()
        parts = [p.capitalize() for p in stem_clean.split() if len(p) >= 2]
        name = " ".join(parts[:3]) if len(parts) >= 2 else "Candidate Profile"

    # Final guard: purely numeric => reset
    if re.match(r"^[\d\s]+$", name or ""):
        name = "Candidate Profile"

    return {"name": name, "email": email, "phone": phone}



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
    Handles: Skills, Key Skills, Technical Skills, Core Competencies, Areas of Expertise, etc.
    Returns the section text or empty string.
    """
    patterns = [
        # "Key Skills", "Technical Skills", "Skills"
        r'(?:key\s+)?(?:technical\s+)?skills?\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\n[A-Z][A-Z\s]{4,}\n|\Z)',
        # "Core Competencies" / "Core Competency"
        r'core\s+competenc(?:y|ies)\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\n[A-Z][A-Z\s]{4,}\n|\Z)',
        # "Areas of Expertise" / "Expertise"
        r'(?:areas?\s+of\s+)?expertise\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\n[A-Z][A-Z\s]{4,}\n|\Z)',
        # "Professional Skills" / "Functional Skills"
        r'(?:professional|functional|primary|secondary)\s+skills?\s*[:：]?\s*\n(.*?)(?:\n\s*\n|\n[A-Z][A-Z\s]{4,}\n|\Z)',
        # Inline: "Skills: Python, Java, SQL"
        r'(?:key\s+)?skills?\s*[:：]\s*(.+?)(?:\n\n|\n[A-Z]|\Z)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)[:1500]
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPERIENCE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_work_experience_section(text: str) -> str:
    """
    Extract the Work Experience / Professional Experience section text.
    This is specifically targeted for timeline date range extraction.
    """
    patterns = [
        r'(?:work\s+experience|professional\s+experience|employment\s+history|'
        r'career\s+history|work\s+history|experience\s+summary|career\s+progression)'
        r'\s*[:：]?\s*\n(.*?)(?:\n\s*(?:education|skills?|projects?|certifications?|achievements?|awards?|'
        r'publications?|references?|languages?|hobbies?)\s*[:：]?\s*\n|\Z)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)[:5000]
    return ""


def extract_experience_years(text: str) -> float:
    """
    4-Stage Hybrid Experience Extraction:
    Stage 0: Work Experience section date range aggregation (HIGHEST priority)
    Stage 1: Professional Summary section scan
    Stage 2: Full-text date range aggregation
    Stage 3: AI/NLP fallback via Cohere / local fallback
    Returns 0.0 ONLY if candidate is confirmed fresher.
    """
    current_year = datetime.datetime.now().year

    # Helper to clean/convert 2-digit or 4-digit year string
    def clean_year(yr_str: str) -> int:
        yr = int(re.search(r'\d+', yr_str).group())
        if yr < 100:
            if yr < 80:
                return 2000 + yr
            else:
                return 1900 + yr
        return yr

    def _aggregate_date_ranges(source_text: str) -> float:
        """Parse date ranges in text and sum durations."""
        date_patterns = [
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*[\'\'`]?\s*,?\s*(\d{2,4})\s*[-\u2013\u2014to]+\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*[\'\'`]?\s*,?\s*)?(\d{2,4}|present|current|till\s*date|now|ongoing)\b',
            r"\b((?:19|20)\d{2})\s*[-\u2013\u2014to]+\s*((?:19|20)\d{2}|present|current|till\s*date|now|ongoing)\b",
            # Short year like "Jul'24" or "Jul 2024"
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\'\u2018\u2019`]?(\d{2,4})\s*[-\u2013\u2014]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\'\u2018\u2019`]?)?(\d{2,4}|present|current|now|ongoing)\b",
        ]
        seen = set()
        months = 0
        for pat in date_patterns:
            for m in re.finditer(pat, source_text, re.IGNORECASE):
                g = m.groups()
                s_str, e_str = g[-2], g[-1]
                try:
                    s = clean_year(s_str)
                    e = current_year if re.search(r'present|current|till|now|ongoing', e_str, re.IGNORECASE) else clean_year(e_str)
                    key = (s, e)
                    if key not in seen and 1980 <= s <= current_year and s <= e:
                        seen.add(key)
                        months += (e - s) * 12
                except Exception:
                    continue
        return round(min(months / 12, 40.0), 1) if months > 0 else 0.0

    # ──────────────────────────────────────────────────────────────────
    # STAGE 0: Work Experience section — targeted date range aggregation
    # This is the HIGHEST priority because it reads actual job entries.
    # ──────────────────────────────────────────────────────────────────
    work_section = _extract_work_experience_section(text)
    if work_section:
        stage0_years = _aggregate_date_ranges(work_section)
        if stage0_years > 0:
            return stage0_years

    # ──────────────────────────────────────────────────────────────────
    # STAGE 1: Professional Summary / About / Profile section scan
    # ──────────────────────────────────────────────────────────────────
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
        # "9+ years in software/tech/data/AI/MarCom etc."
        r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+in\s+(?:the\s+)?(?:software|it|tech|data|ml|ai|telecom|finance|banking|healthcare|manufacturing|marcom|marketing|sales|branding|event)',
        # "X yrs experience"
        r'(\d+(?:\.\d+)?)\s*\+?\s*yrs?\s+(?:of\s+)?experience',
        # "experience: X" or "total experience: X years"
        r'(?:total\s+)?experience\s*[:：]\s*(\d+(?:\.\d+)?)\s*\+?\s*years?',
        # "with X years of / in" (common in summaries)
        r'with\s+(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of|in)',
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
    # STAGE 2: Full-text date range aggregation
    # ──────────────────────────────────────────────────────────────────
    stage2_years = _aggregate_date_ranges(text)
    if stage2_years > 0:
        return stage2_years

    # ──────────────────────────────────────────────────────────────────
    # STAGE 3: AI/NLP Fallback via Groq
    # ──────────────────────────────────────────────────────────────────
    try:
        from services.llm_service import is_groq_available, llm_generate
        if is_groq_available():
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
            resp = llm_generate(prompt, temperature=0.0, max_tokens=10)
            m = re.search(r'(\d+(?:\.\d+)?)', resp.strip())
            if m:
                val = float(m.group(1))
                return min(val, 40.0)
    except Exception as e:
        print(f"[ExperienceParser] Groq fallback failed: {e}")

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
    nlp = get_nlp()
    locations = [
        "Bangalore", "Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad",
        "Chennai", "Kolkata", "Ahmedabad", "Noida", "Gurgaon", "Gurugram",
        "New York", "San Francisco", "Seattle", "Austin", "Chicago",
        "London", "Singapore", "Toronto",
    ]
    for loc in locations:
        if re.search(r'\b' + re.escape(loc) + r'\b', text, re.IGNORECASE):
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

