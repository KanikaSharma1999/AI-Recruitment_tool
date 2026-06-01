"""
Jitsi JWT Token Service
Generates secure moderator (recruiter) and attendee (candidate) tokens.
Uses PyJWT to sign tokens accepted by Jitsi's token_authentication plugin.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId
import uuid, os, time

from auth import get_current_user
from database import candidates_col

router = APIRouter(prefix="/interviews/tokens", tags=["interview-tokens"])

# Jitsi JWT config - uses the app secret from env
JITSI_APP_ID   = os.getenv("JITSI_APP_ID", "hireiq")
JITSI_SECRET   = os.getenv("JITSI_SECRET", os.getenv("JWT_SECRET", "hireiq_secret_key_2026"))
JITSI_DOMAIN   = os.getenv("JITSI_DOMAIN", "meet.jit.si")

class TokenRequest(BaseModel):
    candidate_id: str
    role: Optional[str] = "moderator"   # "moderator" | "attendee"

def _build_jitsi_jwt(room: str, display_name: str, email: str, is_moderator: bool, avatar: str = "") -> str:
    """Build a Jitsi-compatible JWT token."""
    try:
        import jwt as pyjwt
    except ImportError:
        # Fallback: return empty string (Jitsi will use open mode)
        return ""

    now = int(time.time())
    exp = now + (4 * 3600)  # 4 hour expiry

    payload = {
        "iss": JITSI_APP_ID,
        "aud": "jitsi",
        "sub": JITSI_DOMAIN,
        "room": room,
        "iat": now,
        "exp": exp,
        "nbf": now - 10,
        "context": {
            "user": {
                "name": display_name,
                "email": email,
                "avatar": avatar,
                "moderator": str(is_moderator).lower(),
            },
            "features": {
                "livestreaming": is_moderator,
                "outbound-call": False,
                "sip-outbound-call": False,
                "transcription": is_moderator,
                "recording": is_moderator,
            }
        },
        "moderator": is_moderator,
    }
    token = pyjwt.encode(payload, JITSI_SECRET, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


@router.post("/recruiter")
async def get_recruiter_token(
    req: TokenRequest,
    current_user=Depends(get_current_user),
):
    """
    Returns a MODERATOR Jitsi JWT token for the recruiter.
    Recruiter gets full host controls.
    """
    candidate = await candidates_col.find_one({"_id": ObjectId(req.candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview = candidate.get("interview", {})
    current_status = interview.get("status") or "scheduled"
    
    # State check: block recruiter rejoin if completed
    if current_status in ["completed", "analyzing", "analyzed", "missed", "cancelled", "archived"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate recruiter token. The interview is already {current_status}."
        )

    meeting_link = interview.get("meeting_link", "")
    
    # Extract room name from the Jitsi URL
    room = meeting_link.split("/")[-1] if meeting_link else f"hireiq-{req.candidate_id[:8]}"

    recruiter_name = current_user.get("name") or current_user.get("email", "Recruiter")
    recruiter_email = current_user.get("email", "recruiter@hireiq.com")

    token = _build_jitsi_jwt(
        room=room,
        display_name=recruiter_name,
        email=recruiter_email,
        is_moderator=True,
    )

    # Mark recruiter as joined in candidate and session DB
    await candidates_col.update_one(
        {"_id": ObjectId(req.candidate_id)},
        {"$set": {
            "interview.recruiter_joined": True
        }}
    )

    return {
        "token": token,
        "room": room,
        "domain": JITSI_DOMAIN,
        "role": "moderator",
        "meeting_url": f"https://{JITSI_DOMAIN}/{room}",
        "display_name": recruiter_name,
    }


@router.post("/candidate")
async def get_candidate_token(req: TokenRequest):
    """
    Returns a restricted ATTENDEE Jitsi JWT token for the candidate.
    Candidate cannot record, share screen, or become moderator.
    This endpoint is PUBLIC so the candidate link works without login.
    """
    candidate = await candidates_col.find_one({"_id": ObjectId(req.candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview = candidate.get("interview", {})
    if not interview:
        raise HTTPException(status_code=400, detail="No interview scheduled for this candidate")

    current_status = interview.get("status") or "scheduled"
    
    # State check: candidate cannot join if completed, analyzing, analyzed, missed, etc.
    if current_status in ["completed", "analyzing", "analyzed", "missed", "cancelled", "archived"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot join interview because it has been {current_status}."
        )

    # Enforce start window
    if interview.get("date") and interview.get("time"):
        try:
            sched_date = interview["date"]
            sched_time = interview["time"]
            scheduled_dt = datetime.fromisoformat(f"{sched_date}T{sched_time}:00")
            now_local = datetime.now()
            
            # Candidate early block (more than 5 mins early)
            if now_local < scheduled_dt - timedelta(minutes=5):
                raise HTTPException(
                    status_code=400,
                    detail="Interview room is not open yet. Please join closer to the scheduled time."
                )
            
            # Candidate late block (more than 15 mins past)
            if now_local > scheduled_dt + timedelta(minutes=15):
                raise HTTPException(
                    status_code=400,
                    detail="This interview session has expired. The entry grace period has ended."
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"[Candidate Token] Error checking window: {e}")

    meeting_link = interview.get("meeting_link", "")
    room = meeting_link.split("/")[-1] if meeting_link else f"hireiq-{req.candidate_id[:8]}"

    candidate_name = candidate.get("name", "Candidate")
    candidate_email = candidate.get("email", "candidate@interview.com")

    token = _build_jitsi_jwt(
        room=room,
        display_name=candidate_name,
        email=candidate_email,
        is_moderator=False,
    )

    # Update candidate state to candidate_joined or keep current status (e.g. live)
    new_status = "candidate_joined" if current_status == "scheduled" else current_status

    # Mark candidate as joined in DB
    await candidates_col.update_one(
        {"_id": ObjectId(req.candidate_id)},
        {"$set": {
            "interview.status": new_status,
            "interview.candidate_joined_session": True,
            "interview.candidate_joined": True,
            "interview.join_time": datetime.utcnow()
        }}
    )

    return {
        "token": token,
        "room": room,
        "domain": JITSI_DOMAIN,
        "role": "attendee",
        "meeting_url": f"https://{JITSI_DOMAIN}/{room}",
        "display_name": candidate_name,
        "candidate_name": candidate_name,
    }


@router.get("/room-info/{candidate_id}")
async def get_room_info(candidate_id: str, current_user=Depends(get_current_user)):
    """Returns room metadata for the recruiter dashboard."""
    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview = candidate.get("interview", {})
    return {
        "candidate_name": candidate.get("name"),
        "room": interview.get("meeting_link", "").split("/")[-1],
        "status": interview.get("status"),
        "scheduled_date": interview.get("date"),
        "scheduled_time": interview.get("time"),
        "duration_minutes": interview.get("duration", 30),
    }
