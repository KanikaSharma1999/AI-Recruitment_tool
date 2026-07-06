"""
Transcription Service — services/transcription_service.py
===========================================================
Isolated speech-to-text interface for HireIQ.

Decision: Groq Whisper is retained as the cloud ASR backend because no
equivalent free local STT model runs reliably on CPU only (without GPU).
This service isolates the dependency so it can be swapped later:

  Future swap: Replace `_transcribe_groq` with `_transcribe_faster_whisper`
               (requires `pip install faster-whisper` and NVIDIA GPU).

Usage:
    from services.transcription_service import transcribe_audio_file

If GROQ_API_KEY is not set, the function returns an empty list with a
warning — audio data is stored but transcription is skipped gracefully.
"""

import os
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def is_transcription_available() -> bool:
    """Return True if the ASR backend is configured."""
    return bool(GROQ_API_KEY and "your_groq" not in GROQ_API_KEY)


async def transcribe_audio_file(
    audio_bytes: bytes,
    file_ext: str = ".webm",
    offset_seconds: float = 0.0,
) -> list[dict]:
    """
    Transcribe raw audio bytes.
    Returns a list of segment dicts with keys: text, timestamp, speaker, confidence.
    Returns an empty list if transcription is unavailable.

    Parameters
    ----------
    audio_bytes   : Raw audio content from the upload.
    file_ext      : File extension hint for the temp file (e.g. '.webm', '.mp4').
    offset_seconds: Interview timeline offset to calculate absolute timestamps.
    """
    if not audio_bytes:
        return []

    if not is_transcription_available():
        logger.warning(
            "[Transcription] GROQ_API_KEY not set — transcription skipped. "
            "Set GROQ_API_KEY in .env to enable live speech-to-text."
        )
        return []

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        return await _transcribe_groq(tmp_path, offset_seconds)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def _transcribe_groq(file_path: str, offset_seconds: float = 0.0) -> list[dict]:
    """
    Groq Whisper backend (cloud ASR).
    Isolated here so it can be swapped for faster-whisper when GPU is available.
    """
    import numpy as np

    try:
        from groq import AsyncGroq
    except ImportError:
        logger.error("[Transcription] groq package not installed. Run: pip install groq")
        return []

    client = AsyncGroq(api_key=GROQ_API_KEY)

    with open(file_path, "rb") as f:
        translation = await client.audio.transcriptions.create(
            file=(file_path, f.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )

    segments = getattr(translation, "segments", []) or []
    if isinstance(translation, dict):
        segments = translation.get("segments", [])

    results = []
    for segment in segments:
        if not isinstance(segment, dict):
            segment = segment.__dict__ if hasattr(segment, "__dict__") else {}

        text = segment.get("text", "").strip()
        if not text:
            continue

        seg_start = float(segment.get("start", 0.0))
        absolute_start = offset_seconds + seg_start
        minutes, seconds = int(absolute_start // 60), int(absolute_start % 60)
        timestamp_str = f"{minutes:02d}:{seconds:02d}"

        speaker = _diarize_segment(text)

        confidence = segment.get("confidence")
        if confidence is None:
            avg_logprob = segment.get("avg_logprob")
            confidence = float(np.exp(avg_logprob)) if avg_logprob is not None else 0.95
        confidence = round(min(1.0, max(0.0, float(confidence))), 2)

        results.append({
            "text": text,
            "timestamp": timestamp_str,
            "speaker": speaker,
            "confidence": confidence,
        })

    return results


# ---------------------------------------------------------------------------
# Future: faster-whisper local backend (requires GPU)
# ---------------------------------------------------------------------------
# async def _transcribe_faster_whisper(file_path: str, offset_seconds: float = 0.0) -> list[dict]:
#     from faster_whisper import WhisperModel
#     model = WhisperModel("base", device="cuda", compute_type="float16")
#     segments, _ = model.transcribe(file_path)
#     results = []
#     for segment in segments:
#         minutes, seconds = int(segment.start // 60), int(segment.start % 60)
#         results.append({
#             "text": segment.text.strip(),
#             "timestamp": f"{minutes:02d}:{seconds:02d}",
#             "speaker": _diarize_segment(segment.text),
#             "confidence": round(segment.no_speech_prob, 2),
#         })
#     return results


def _diarize_segment(text: str) -> str:
    """
    Rule-based speaker diarization.
    Classifies each voice segment as Interviewer or Candidate.
    """
    text_lower = text.lower().strip()
    interviewer_patterns = [
        "tell me about", "why do you", "what is your", "how do you",
        "can you explain", "could you describe", "walk me through",
        "welcome to", "nice to meet you", "my name is", "next question",
        "let's talk about", "how would you handle", "do you have any questions",
        "thank you for coming", "your resume shows",
    ]
    is_question = text_lower.endswith("?")
    has_interviewer_phrase = any(p in text_lower for p in interviewer_patterns)
    question_words = {"what", "why", "how", "who", "where", "when", "which", "can", "could", "would", "do", "does", "is", "are"}

    if has_interviewer_phrase or (is_question and any(w in text_lower for w in question_words)):
        return "Interviewer"
    return "Candidate"
