"""
Ollama Local LLM Client
========================
Central client for all Mistral 7B Instruct inference via Ollama.
Replaces Groq API completely. Zero cost. Runs on local hardware.

Usage:
    from services.ollama_client import ollama_generate, ollama_available

    result = await ollama_generate(prompt="...", temperature=0.1)
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds


def _safe_json(text: str) -> Optional[dict]:
    """Extract and parse the first JSON object found in text."""
    import re
    text = text.strip()
    # Remove markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to extract JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


async def ollama_available() -> bool:
    """Check if Ollama server is reachable and Mistral model is loaded."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            if r.status_code != 200:
                return False
            models = [m.get("name", "") for m in r.json().get("models", [])]
            return any(OLLAMA_MODEL in m for m in models)
    except Exception as e:
        logger.warning(f"[Ollama] Not reachable: {e}")
        return False


async def ollama_generate(
    prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1000,
    expect_json: bool = True,
) -> Optional[dict | str]:
    """
    Send a prompt to local Ollama Mistral and return the response.

    Args:
        prompt: Full prompt string to send.
        temperature: Sampling temperature (0.0 = deterministic).
        max_tokens: Maximum tokens to generate.
        expect_json: If True, attempt to parse response as JSON dict.

    Returns:
        Parsed dict if expect_json=True, raw string otherwise.
        Returns None on failure.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if expect_json:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            r = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

        if expect_json:
            parsed = _safe_json(raw)
            if parsed is None:
                logger.error(f"[Ollama] JSON parse failed. Raw: {raw[:300]}")
            return parsed
        return raw

    except httpx.TimeoutException:
        logger.error(f"[Ollama] Request timed out after {OLLAMA_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"[Ollama] Generation failed: {e}")
        return None


def ollama_generate_sync(
    prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 1000,
    expect_json: bool = True,
) -> Optional[dict | str]:
    """
    Synchronous wrapper around ollama_generate.
    Used by synchronous code paths (e.g. llm_parser.py).
    """
    import httpx as _httpx
    import re

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if expect_json:
        payload["format"] = "json"

    try:
        with _httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            r = client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

        if expect_json:
            return _safe_json(raw)
        return raw

    except _httpx.TimeoutException:
        logger.error(f"[Ollama] Sync request timed out after {OLLAMA_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"[Ollama] Sync generation failed: {e}")
        return None
