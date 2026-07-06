"""
LLM Service — services/llm_service.py
=======================================
Cloud LLM client for HireIQ.

Provider : Groq Cloud  (llama-3.3-70b-versatile)
Whisper  : Groq Whisper (whisper-large-v3-turbo) — see transcription_service.py

Design principles:
  • Single Responsibility — only LLM I/O lives here.
  • Scoring is NEVER done here — the heuristic engine owns all scores.
  • Every public function raises RuntimeError when the API key is absent so
    callers can distinguish "key missing" from a true API error.
  • Rule-based fallbacks live in the individual service modules (feedback.py,
    hiring_summary.py, etc.) — NOT here.
"""

import os
import json
import re
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL:   str = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")

# ── Prompt-injection guard ─────────────────────────────────────────────────────
_INJECTION_MARKERS = [
    "ignore previous instructions", "ignore all instructions",
    "disregard the above", "system prompt", "you are now",
    "act as", "forget your", "new persona", "jailbreak",
]

def sanitize_prompt_input(text: str, max_chars: int = 12_000) -> str:
    """Truncate and scrub obvious prompt-injection patterns from user-supplied text."""
    if not text:
        return ""
    cleaned = text[:max_chars]
    for marker in _INJECTION_MARKERS:
        cleaned = re.sub(re.escape(marker), "[REDACTED]", cleaned, flags=re.IGNORECASE)
    return cleaned


# ── Client factories ───────────────────────────────────────────────────────────
def _groq_sync():
    """Return a synchronous Groq client, or raise if the key is absent."""
    if not GROQ_API_KEY or "your_groq" in GROQ_API_KEY:
        raise RuntimeError(
            "[LLMService] GROQ_API_KEY is not set. "
            "Add it to backend/.env  →  GROQ_API_KEY=gsk_..."
        )
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except ImportError:
        raise RuntimeError("[LLMService] groq package missing. Run: pip install groq")


def _groq_async():
    """Return an async Groq client, or raise if the key is absent."""
    if not GROQ_API_KEY or "your_groq" in GROQ_API_KEY:
        raise RuntimeError(
            "[LLMService] GROQ_API_KEY is not set. "
            "Add it to backend/.env  →  GROQ_API_KEY=gsk_..."
        )
    try:
        from groq import AsyncGroq
        return AsyncGroq(api_key=GROQ_API_KEY)
    except ImportError:
        raise RuntimeError("[LLMService] groq package missing. Run: pip install groq")


# ── Availability check ─────────────────────────────────────────────────────────
def is_groq_available() -> bool:
    """True when GROQ_API_KEY is configured (does NOT test network connectivity)."""
    return bool(GROQ_API_KEY and "your_groq" not in GROQ_API_KEY)


# ── Synchronous generation ─────────────────────────────────────────────────────
def llm_generate(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Synchronous single-turn completion. Raises RuntimeError on failure."""
    client = _groq_sync()
    resp = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def llm_generate_json(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> dict:
    """Synchronous generation with automatic JSON extraction and one retry."""
    response = llm_generate(prompt, model, temperature, max_tokens)
    try:
        return _parse_json(response)
    except ValueError:
        retry = (
            prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
            "No markdown, no prose, no code fences. Start with { and end with }."
        )
        response2 = llm_generate(retry, model, temperature, max_tokens)
        return _parse_json(response2)


# ── Asynchronous generation ────────────────────────────────────────────────────
async def llm_generate_async(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Async single-turn completion."""
    client = _groq_async()
    resp = await client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


async def llm_generate_json_async(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> dict:
    """Async generation with automatic JSON extraction and one retry."""
    response = await llm_generate_async(prompt, model, temperature, max_tokens)
    try:
        return _parse_json(response)
    except ValueError:
        retry = (
            prompt
            + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
            "No markdown, no prose, no code fences. Start with { and end with }."
        )
        response2 = await llm_generate_async(retry, model, temperature, max_tokens)
        return _parse_json(response2)


# ── Streaming ──────────────────────────────────────────────────────────────────
async def llm_stream(
    prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.4,
    messages: Optional[list] = None,
) -> AsyncGenerator[str, None]:
    """Async token-by-token streaming. Yields a single error string on failure."""
    if not is_groq_available():
        yield "[GROQ_API_KEY not configured — add it to backend/.env]"
        return

    client = _groq_async()
    if messages is None:
        messages = [{"role": "user", "content": prompt or ""}]

    try:
        stream = await client.chat.completions.create(
            model=model or GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            stream=True,
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token
    except Exception as exc:
        logger.error("[LLMService] Stream error: %s", exc)
        yield f"\n\n⚠️ AI stream error: {exc}"


# ── Multi-turn chat helpers ────────────────────────────────────────────────────
def llm_chat(
    messages: list,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> str:
    """Synchronous multi-turn chat completion."""
    client = _groq_sync()
    resp = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


async def llm_chat_async(
    messages: list,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> str:
    """Async multi-turn chat completion."""
    client = _groq_async()
    resp = await client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


# ── JSON parsing helper ────────────────────────────────────────────────────────
def _parse_json(text: str) -> dict:
    """
    Extract a JSON object from LLM output that may contain markdown fences,
    prose before/after the JSON, or other noise.
    Raises ValueError if no valid JSON object is found.
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find outermost { … } by tracking brace depth
    try:
        first = text.find("{")
        if first != -1:
            depth, in_str, esc = 0, False, False
            for i in range(first, len(text)):
                ch = text[i]
                if ch == "\\" and in_str:
                    esc = not esc
                    continue
                if ch == '"' and not esc:
                    in_str = not in_str
                esc = False
                if not in_str:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[first : i + 1])
    except Exception:
        pass

    # Greedy regex fallback
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise ValueError(f"Cannot extract JSON from LLM output: {text[:300]}")
