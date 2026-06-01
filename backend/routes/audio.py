from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from bson import ObjectId
from datetime import datetime
import os
import tempfile
import numpy as np
from database import candidates_col, interview_sessions_col
from auth import get_current_user

router = APIRouter(prefix="/audio", tags=["audio"])

def diarize_segment(text: str) -> str:
    """
    Perform semantic dialogue-turn rule classification to label the speaker.
    Distinguishes candidate responses from interviewer queries/introductions.
    """
    text_lower = text.lower().strip()
    
    # Recruiter/Interviewer common question patterns and introductory remarks
    interviewer_patterns = [
        "tell me about",
        "why do you",
        "what is your",
        "how do you",
        "can you explain",
        "could you describe",
        "walk me through",
        "welcome to",
        "nice to meet you",
        "my name is",
        "next question",
        "let's talk about",
        "how would you handle",
        "do you have any questions",
        "thank you for coming",
        "your resume shows"
    ]
    
    # Check if any interviewer pattern is in the text, or if the segment is a question ending in '?'
    is_question = text_lower.endswith("?")
    has_interviewer_phrase = any(phrase in text_lower for phrase in interviewer_patterns)
    
    if has_interviewer_phrase or (is_question and any(q_word in text_lower for q_word in ["what", "why", "how", "who", "where", "when", "which", "can", "could", "would", "do", "does", "is", "are"])):
        return "Interviewer"
    
    return "Candidate"

@router.post("/upload")
async def upload_audio_chunk(
    candidate_id: str = Form(...),
    audio: UploadFile = File(...),
):
    """
    Candidate audio chunk upload endpoint.
    Performs real cloud Whisper transcription, extracts segments,
    applies speaker diarization, calculates absolute timeline timestamps,
    and stores structured results in the database.
    """
    content = await audio.read()
    if not content:
        return {"message": "Empty audio chunk, skipped."}

    # Fetch active interview session to calculate timeline offsets
    session = await interview_sessions_col.find_one({
        "candidate_id": candidate_id,
        "meeting_status": "LIVE"
    })
    
    if session:
        start_time = session.get("start_time")
        if isinstance(start_time, str):
            if start_time.endswith("Z"):
                start_time = start_time[:-1]
            start_time = datetime.fromisoformat(start_time)
        
        elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
        # The chunk covers the last 10 seconds of recording
        offset_seconds = max(0.0, elapsed_seconds - 10.0)
    else:
        offset_seconds = 0.0

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(
            status_code=500,
            detail="Cloud transcription service is offline: GROQ_API_KEY is not configured."
        )

    # Write audio chunk to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    new_chunks = []
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=groq_api_key)
        
        with open(temp_file_path, "rb") as f:
            translation = await client.audio.transcriptions.create(
                file=(temp_file_path, f.read()),
                model="whisper-large-v3",
                response_format="verbose_json"
            )

        # Parse verbosely to extract segments, timestamps, and confidence levels
        segments = getattr(translation, "segments", []) or translation.get("segments", [])
        
        for segment in segments:
            if not isinstance(segment, dict):
                segment = segment.__dict__ if hasattr(segment, "__dict__") else {}
                
            text = segment.get("text", "").strip()
            if not text:
                continue

            # Calculate start and end offsets relative to the interview timeline
            seg_start = float(segment.get("start", 0.0))
            absolute_start = offset_seconds + seg_start
            
            # Format timeline timestamp (e.g. "02:15")
            minutes = int(absolute_start // 60)
            seconds = int(absolute_start % 60)
            timestamp_str = f"{minutes:02d}:{seconds:02d}"

            # Run speaker diarization heuristic
            speaker = diarize_segment(text)

            # Extract or compute confidence level from log probability
            confidence = segment.get("confidence", None)
            if confidence is None:
                avg_logprob = segment.get("avg_logprob", None)
                if avg_logprob is not None:
                    confidence = float(np.exp(avg_logprob))
                else:
                    confidence = 0.95
            
            confidence = round(min(1.0, max(0.0, float(confidence))), 2)

            new_chunks.append({
                "text": text,
                "timestamp": timestamp_str,
                "speaker": speaker,
                "confidence": confidence
            })

        # Upload audio chunk to Cloud Storage (AWS S3 / Supabase / Local Fallback)
        try:
            from services.storage_service import storage_service
            audio_url = await storage_service.upload_file(temp_file_path, f"chunk_{candidate_id}_{int(datetime.utcnow().timestamp())}.webm")
            await candidates_col.update_one(
                {"_id": ObjectId(candidate_id)},
                {"$push": {"audio_recordings": {"url": audio_url, "timestamp": datetime.utcnow()}}}
            )
            print(f"[StorageService] Uploaded audio chunk: {audio_url}")
        except Exception as storage_err:
            print(f"[Storage Error] Failed to upload chunk: {storage_err}")

    except Exception as e:
        print(f"[Cloud Whisper Error] Failed to transcribe audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass

    if new_chunks:
        # Save structured segments in candidate profile
        await candidates_col.update_one(
            {"_id": ObjectId(candidate_id)},
            {"$push": {"transcript": {"$each": new_chunks}}}
        )
        # Save structured segments in live Jitsi session
        await interview_sessions_col.update_one(
            {"candidate_id": candidate_id, "meeting_status": "LIVE"},
            {"$push": {"transcript": {"$each": new_chunks}}}
        )

    return {
        "message": "Audio chunk transcribed successfully.",
        "segments_added": len(new_chunks),
        "transcripts": new_chunks
    }
