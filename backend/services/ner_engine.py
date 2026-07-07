"""
services/ner_engine.py
=======================
Stage 2 of the Hybrid Parsing Pipeline — Named Entity Recognition.

Uses GLiNER as the primary NER engine to extract:
  - Candidate Name
  - Email
  - Phone Number
  - City / State / Country / Address
  - Organizations / Companies / Universities

GLiNER is fast, zero-shot, and runs entirely locally.

Cascade for low-confidence extractions:
  GLiNER → Groq Validation → Final Value

Falls back to the existing regex-based extractor if GLiNER is not installed.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── GLiNER ────────────────────────────────────────────────────────────────────
_gliner_model = None
_GLINER_LABELS = [
    "person name",
    "email address",
    "phone number",
    "city",
    "state",
    "country",
    "address",
    "organization",
    "company",
    "university",
]

_HAS_GLINER = False
try:
    from gliner import GLiNER as _GLiNER
    _HAS_GLINER = True
    logger.info("[NEREngine] GLiNER library found. Will load model on first use.")
except ImportError:
    logger.info("[NEREngine] GLiNER not installed — will use regex fallback for NER.")


def _get_gliner():
    """Lazy-load the GLiNER model (loaded once per process)."""
    global _gliner_model
    if _gliner_model is None and _HAS_GLINER:
        try:
            logger.info("[NEREngine] Loading GLiNER model 'urchade/gliner_medium-v2.1' ...")
            _gliner_model = _GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
            logger.info("[NEREngine] GLiNER model loaded successfully.")
        except Exception as exc:
            logger.error("[NEREngine] GLiNER model load failed: %s. Using regex fallback.", exc)
            _gliner_model = False
    return _gliner_model if _gliner_model is not False else None


# ═══════════════════════════════════════════════════════════════════════════════
#  GLiNER extraction
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_with_gliner(text: str, threshold: float = 0.45) -> dict:
    """
    Run GLiNER on the first 2000 characters of resume text.
    Returns a raw dict of label → list of (text, score) tuples.
    """
    model = _get_gliner()
    if not model:
        return {}

    # GLiNER works best on shorter windows; use only the header portion
    window = text[:2000]
    try:
        entities = model.predict_entities(window, _GLINER_LABELS, threshold=threshold)
    except Exception as exc:
        logger.warning("[NEREngine] GLiNER prediction failed: %s", exc)
        return {}

    result: dict[str, list] = {}
    for ent in entities:
        label = ent.get("label", "")
        value = ent.get("text", "").strip()
        score = float(ent.get("score", 0.0))
        if value:
            result.setdefault(label, []).append((value, score))

    return result


def _best(ents: dict, label: str) -> Optional[tuple]:
    """Return the highest-confidence entity for a label, or None."""
    items = ents.get(label, [])
    if not items:
        return None
    return max(items, key=lambda x: x[1])


# ═══════════════════════════════════════════════════════════════════════════════
#  Regex fallbacks (used when GLiNER skips / is unavailable)
# ═══════════════════════════════════════════════════════════════════════════════

def _regex_email(text: str) -> Optional[str]:
    m = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    return m.group(0) if m else None


def _regex_phone(text: str) -> Optional[str]:
    # Priority 1: labeled field
    lbl = re.search(
        r"(?:phone|mobile|contact|cell|ph|mob|tel|whatsapp)[.\s:\-]*"
        r"(\+?(?:[\d\s\-\(\)\.]{9,20}))",
        text, re.IGNORECASE,
    )
    if lbl:
        raw = re.sub(r"[\s\-\(\)\.]", "", lbl.group(1))
        if 9 <= len(raw) <= 15:
            return lbl.group(1).strip()

    # Priority 2: +91 prefixed
    m = re.search(r"\+91[\s\-]?([6-9]\d{9})", text)
    if m:
        return f"+91 {m.group(1)}"

    # Priority 3: standalone 10-digit Indian mobile
    for m in re.finditer(r"\b([6-9]\d{9})\b", text):
        return m.group(1)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Groq validation for low-confidence GLiNER results
# ═══════════════════════════════════════════════════════════════════════════════

_LOW_CONFIDENCE_THRESHOLD = 0.55  # below this → send to Groq for validation


def _groq_validate_name(candidate_name: str, raw_text: str) -> Optional[str]:
    """
    Ask Groq to confirm/correct a low-confidence name extraction.
    Returns the validated name or the original candidate if Groq is unavailable.
    """
    try:
        from services.llm_service import is_groq_available, llm_generate_json, sanitize_prompt_input
        if not is_groq_available():
            return candidate_name

        snippet = sanitize_prompt_input(raw_text, max_chars=800)
        prompt = (
            f"Given this resume header snippet:\n\n{snippet}\n\n"
            f"The parser extracted this as the candidate name: \"{candidate_name}\"\n"
            "Is this correct? If yes, return it. If not, extract the correct full name.\n"
            'Respond ONLY with JSON: {"name": "Correct Full Name"}'
        )
        result = llm_generate_json(prompt, temperature=0.0, max_tokens=50)
        validated = result.get("name", "").strip()
        if validated and len(validated.split()) >= 2:
            logger.info(
                "[NEREngine] Groq corrected name: '%s' → '%s'",
                candidate_name, validated,
            )
            return validated
    except Exception as exc:
        logger.warning("[NEREngine] Groq name validation failed: %s", exc)
    return candidate_name


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def extract_entities(raw_text: str, filename: str = "resume.pdf") -> dict:
    """
    Primary NER extraction entry point.

    Returns:
    {
        "name":          str,
        "email":         str,
        "phone":         str,
        "location":      str,   # city/state/country combined
        "city":          str,
        "state":         str,
        "country":       str,
        "organizations": list[str],
        "companies":     list[str],
        "universities":  list[str],
        "ner_source":    "gliner" | "regex"
    }

    Cascade: GLiNER (primary) → Groq validation (low confidence) → regex fallback
    """
    result = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "city": "",
        "state": "",
        "country": "",
        "organizations": [],
        "companies": [],
        "universities": [],
        "ner_source": "regex",
    }

    # ── Try GLiNER first ──────────────────────────────────────────────────────
    gliner_ents = _extract_with_gliner(raw_text) if _HAS_GLINER else {}
    used_gliner = bool(gliner_ents)

    if used_gliner:
        result["ner_source"] = "gliner"

        # Name
        name_match = _best(gliner_ents, "person name")
        if name_match:
            name_text, name_score = name_match
            if name_score < _LOW_CONFIDENCE_THRESHOLD:
                # Send to Groq for validation
                result["name"] = _groq_validate_name(name_text, raw_text)
            else:
                result["name"] = name_text

        # Email (regex is more reliable than GLiNER for structured patterns)
        email_match = _best(gliner_ents, "email address")
        if email_match:
            result["email"] = email_match[0]
        else:
            result["email"] = _regex_email(raw_text) or ""

        # Phone
        phone_match = _best(gliner_ents, "phone number")
        if phone_match:
            result["phone"] = phone_match[0]
        else:
            result["phone"] = _regex_phone(raw_text) or ""

        # Location fields
        for label, key in [
            ("city", "city"), ("state", "state"), ("country", "country"), ("address", "location")
        ]:
            best = _best(gliner_ents, label)
            if best:
                result[key] = best[0]

        # Build combined location string
        loc_parts = [result["city"], result["state"], result["country"]]
        result["location"] = result["location"] or ", ".join(p for p in loc_parts if p)

        # Organizations
        for ent, _score in gliner_ents.get("organization", []):
            result["organizations"].append(ent)
        for ent, _score in gliner_ents.get("company", []):
            result["companies"].append(ent)
        for ent, _score in gliner_ents.get("university", []):
            result["universities"].append(ent)

    # ── Regex fallback for any still-empty critical fields ────────────────────
    if not result["email"]:
        result["email"] = _regex_email(raw_text) or ""
    if not result["phone"]:
        result["phone"] = _regex_phone(raw_text) or ""

    # ── Name fallback: use existing regex-based extractor ────────────────────
    if not result["name"]:
        try:
            from resume_parser import extract_candidate_details
            details = extract_candidate_details(raw_text, filename)
            result["name"]  = details.get("name", "")
            result["email"] = result["email"] or details.get("email", "")
            result["phone"] = result["phone"] or details.get("phone", "")
            result["ner_source"] = "regex"
        except Exception:
            pass

    # Final name fallback: derive from filename
    if not result["name"]:
        stem = filename.rsplit(".", 1)[0]
        parts = [p.capitalize() for p in re.split(r"[\s_\-]+", stem) if len(p) >= 2]
        result["name"] = " ".join(parts[:3]) or "Candidate Profile"

    # Deduplicate lists
    result["organizations"] = list(dict.fromkeys(result["organizations"]))
    result["companies"]     = list(dict.fromkeys(result["companies"]))
    result["universities"]  = list(dict.fromkeys(result["universities"]))

    return result
