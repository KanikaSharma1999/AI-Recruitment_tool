from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from bson import ObjectId
from datetime import datetime
import uuid

from database import candidates_col
from auth import get_current_user
from pydantic import BaseModel

class InterviewSchedule(BaseModel):
    candidate_id: str
    job_id: str
    date: str          # ISO date string
    time: str          # e.g. "10:30"
    mode: str          # "online" | "offline"
    location: Optional[str] = ""
    notes: Optional[str] = ""

class InterviewFeedbackCreate(BaseModel):
    candidate_id: str
    hr_notes: str

router = APIRouter(prefix="/interviews", tags=["interviews"])

@router.post("/schedule")
async def schedule_interview(
    interview: InterviewSchedule,
    current_user=Depends(get_current_user),
):
    candidate_id = interview.candidate_id
    
    room_name = f"interview-{candidate_id}-{uuid.uuid4().hex[:8]}"
    meeting_link = f"https://meet.jit.si/{room_name}"
    
    from services.email_service import send_email, get_interview_scheduled_template
    from database import jobs_col
    import os
    
    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    job = await jobs_col.find_one({"_id": ObjectId(interview.job_id)})
    
    from services.notification_service import notification_service
    
    interview_data = interview.model_dump()
    interview_data["meeting_link"] = meeting_link
    interview_data["status"] = "scheduled"
    interview_data["scheduled_at"] = datetime.utcnow()
    interview_data["scheduled_by"] = current_user.get("email")
    interview_data["recruiter_email"] = current_user.get("email")  # Stored for scheduler reminders

    result = await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {
            "status": "interview_scheduled",
            "interview": interview_data,
            "scheduled_by_email": current_user.get("email"),  # top-level for easy querying
            "updated_at": datetime.utcnow(),
        }},
    )

    if result.matched_count > 0:
        # 1. Schedule Background Reminder for Recruiter
        # Extract ISO date/time for scheduling
        # interview.date is usually 'YYYY-MM-DD' and interview.time is 'HH:MM'
        try:
            scheduled_iso = f"{interview.date}T{interview.time}:00"
            await notification_service.schedule_interview_reminders(
                candidate_id=candidate_id,
                scheduled_time_str=scheduled_iso,
                recruiter_email=current_user.get("email")
            )
        except Exception as e:
            print(f"[Interview] Failed to schedule reminder: {e}")

        # 2. Send HR-ONLY Email Notification
        print(f"\n{'#'*55}")
        print(f"[SCHEDULE_INTERVIEW] ENTERED email sending block")
        print(f"[SCHEDULE_INTERVIEW] HR email: {current_user.get('email')}")
        print(f"[SCHEDULE_INTERVIEW] Candidate: {candidate.get('name')}")
        print(f"{'#'*55}")

        from services.email_service import send_email, get_db_email_settings, get_fallback_settings
        settings = await get_db_email_settings() or get_fallback_settings()
        
        c_score = round(candidate.get('score', 0))
        c_email = candidate.get('email', 'N/A')
        job_role = job.get('title', 'Job Role') if job else 'Job Role'
        
        hs = candidate.get("hiring_summary", {})
        ai = candidate.get("ai_analysis", {})
        c_summary = hs.get("summary", ai.get("executive_summary", "Candidate demonstrates strong technical and operational alignment with the role requirements."))
        if not c_summary or c_summary == "N/A" or "No summary available" in c_summary:
            c_summary = "Candidate demonstrates strong technical and operational alignment with the role requirements."
            
        matched_skills = candidate.get("matched_skills", [])
        if not matched_skills:
            matched_skills = candidate.get("skills", [])
        c_skills = ", ".join(matched_skills[:5]) if matched_skills else "General competency"
        
        hr_html = f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #4f46e5;">Interview Scheduled Successfully</h2>
            <p>You have scheduled an interview with <b>{candidate['name']}</b>.</p>
            
            <div style="background: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <p style="margin:5px 0;"><b>Candidate:</b> {candidate['name']}</p>
                <p style="margin:5px 0;"><b>Candidate Email:</b> {c_email}</p>
                <p style="margin:5px 0;"><b>Role:</b> {job_role}</p>
                <p style="margin:5px 0;"><b>Interview Date:</b> {interview.date}</p>
                <p style="margin:5px 0;"><b>Interview Time:</b> {interview.time}</p>
                <p style="margin:5px 0;"><b>Meeting Link:</b> <a href="{meeting_link}">{meeting_link}</a></p>
                <p style="margin:5px 0;"><b>AI Match Score:</b> {c_score}%</p>
                <p style="margin:5px 0;"><b>Top Skills:</b> {c_skills}</p>
            </div>
            
            <p><b>AI Summary:</b><br/>{c_summary}</p>
            
            <hr style="margin-top:20px; border:none; border-top: 1px solid #e2e8f0;">
            <p style="font-size: 12px; color: #64748b;">A reminder will be sent to you 15 minutes before the start time.</p>
        </div>
        """
        
        # Send confirmation to HR ONLY (no email to candidate)
        hr_email = current_user.get("email")
        subject = f"Interview Scheduled — {candidate['name']} | {job_role}"
        
        print(f"[SCHEDULE_INTERVIEW] Calling send_email() → {hr_email}")
        try:
            success = await send_email(hr_email, subject, hr_html)
            print(f"[SCHEDULE_INTERVIEW] send_email() result: {success}")
        except Exception as e:
            import traceback
            print(f"[SCHEDULE_INTERVIEW] send_email() RAISED EXCEPTION: {e}")
            traceback.print_exc()

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    return {"message": "Interview scheduled successfully", "meeting_link": meeting_link}

@router.post("/feedback")
async def create_interview_feedback(
    feedback: InterviewFeedbackCreate,
    current_user=Depends(get_current_user),
):
    candidate = await candidates_col.find_one({"_id": ObjectId(feedback.candidate_id)})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    resume_score = candidate.get("score", 0.0)
    
    # Generate Feedback using Cohere or Rule-based
    import os
    import cohere
    client = None
    api_key = os.getenv("COHERE_API_KEY")
    if api_key:
        try:
            client = cohere.Client(api_key)
        except Exception:
            pass

    structured_feedback = {
        "communication": "Average",
        "confidence": "Average",
        "recommendation": "Pending review",
        "raw_response": ""
    }
    
    if client:
        try:
            prompt = (
                f"You are an HR Interview Evaluator.\n"
                f"The candidate's AI Resume Match Score is {int(resume_score * 100)}%.\n"
                f"Here are the HR interviewer's notes: {feedback.hr_notes}\n\n"
                "Based on this, evaluate the candidate in exactly 3 lines formatted strictly as:\n"
                "Communication: [Excellent/Good/Average/Poor]\n"
                "Confidence: [Excellent/Good/Average/Poor]\n"
                "Recommendation: [Hire / Strong Hire / Reject / Hold]"
            )
            response = client.chat(
                model="command-r-plus-08-2024",
                message=prompt,
                temperature=0.3,
            )
            text = response.text.strip()
            structured_feedback["raw_response"] = text
            # Parse lines
            for line in text.split('\n'):
                line = line.strip()
                if line.lower().startswith("communication:"):
                    structured_feedback["communication"] = line.split(":", 1)[1].strip()
                elif line.lower().startswith("confidence:"):
                    structured_feedback["confidence"] = line.split(":", 1)[1].strip()
                elif line.lower().startswith("recommendation:"):
                    structured_feedback["recommendation"] = line.split(":", 1)[1].strip()
        except Exception as e:
            client = None # Fallback
            
    if not client:
        # Rule-based fallback
        notes_lower = feedback.hr_notes.lower()
        if "good" in notes_lower or "great" in notes_lower or "excellent" in notes_lower:
            structured_feedback["communication"] = "Good"
            structured_feedback["confidence"] = "Good"
            structured_feedback["recommendation"] = "Hire" if resume_score > 0.6 else "Hold"
        elif "poor" in notes_lower or "bad" in notes_lower or "weak" in notes_lower:
            structured_feedback["communication"] = "Poor"
            structured_feedback["confidence"] = "Poor"
            structured_feedback["recommendation"] = "Reject"
        else:
            structured_feedback["communication"] = "Average"
            structured_feedback["confidence"] = "Average"
            structured_feedback["recommendation"] = "Hold"
            
    # Save to candidate doc
    await candidates_col.update_one(
        {"_id": ObjectId(feedback.candidate_id)},
        {"$set": {"interview_feedback": structured_feedback}}
    )
    
    return {"message": "Feedback generated and saved", "feedback": structured_feedback}

class FaceStatsCreate(BaseModel):
    candidate_id: str
    looking_away_count: int
    no_face_count: int
    multiple_faces_count: int
    tab_switches: Optional[int] = 0
    copy_paste_count: Optional[int] = 0
    posture_shift: Optional[int] = 0
    presence: Optional[bool] = True
    suspicious_events: Optional[list] = []

@router.post("/face-stats")
async def add_face_stats(stats: FaceStatsCreate):
    # Appends new face stats reading to the candidate doc
    await candidates_col.update_one(
        {"_id": ObjectId(stats.candidate_id)},
        {"$push": {
            "face_stats": {
                "looking_away_count": stats.looking_away_count,
                "no_face_count": stats.no_face_count,
                "multiple_faces_count": stats.multiple_faces_count,
                "tab_switches": stats.tab_switches,
                "copy_paste_count": stats.copy_paste_count,
                "posture_shift": stats.posture_shift,
                "presence": stats.presence,
                "suspicious_events": stats.suspicious_events,
                "timestamp": datetime.utcnow()
            }
        }}
    )
    return {"message": "Stats recorded"}

class AnalyzeRequest(BaseModel):
    candidate_id: str

@router.post("/analyze")
async def analyze_interview(req: AnalyzeRequest):
    import sys
    import os
    # Add services folder to path if needed
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from services.ai_analysis import generate_interview_feedback
    
    try:
        feedback = await generate_interview_feedback(req.candidate_id)
        return {"message": "Analysis generated", "feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Interview Question Generator ─────────────────────────────────────────────

class QuestionGenRequest(BaseModel):
    job_id: str
    candidate_id: Optional[str] = None   # If provided, personalise questions

BEHAVIORAL_TEMPLATES = [
    "Tell me about a time you faced a significant technical challenge and how you resolved it.",
    "Describe a situation where you had to learn a new technology quickly to meet a deadline.",
    "Give an example of when you disagreed with a team member or manager and how you handled it.",
    "Tell me about a project where you had to collaborate cross-functionally. What was your role?",
    "Describe a time when you identified a critical bug or issue before it reached production.",
]

def _skills_based_questions(job_title: str, skills: list, exp_years: float = 0) -> list:
    """Generate template-based interview questions from job skills."""
    questions = []

    # Technical questions per skill
    for skill in skills[:5]:
        questions.append({
            "type": "Technical",
            "question": f"Can you walk me through your experience with {skill}? What's the most complex thing you've built using it?",
        })

    # Behavioral questions (role-specific)
    level = "senior" if exp_years >= 5 else "mid-level" if exp_years >= 2 else "junior"
    questions.append({
        "type": "Behavioral",
        "question": f"For a {level} {job_title} role, what do you consider your strongest technical contribution in the past year?",
    })
    for bt in BEHAVIORAL_TEMPLATES[:3]:
        questions.append({"type": "Behavioral", "question": bt})

    # Architecture / system design (if senior)
    if exp_years >= 4:
        questions.append({
            "type": "System Design",
            "question": f"Design a scalable {job_title.lower()} system that needs to handle 1M requests per day. Walk me through your approach.",
        })

    # Closing
    questions.append({
        "type": "Culture Fit",
        "question": "What does your ideal engineering team and working culture look like?",
    })
    questions.append({
        "type": "Motivation",
        "question": f"Why are you interested in this {job_title} position specifically, and what do you hope to achieve in your first 90 days?",
    })

    return questions[:10]


async def _cohere_questions(job_title: str, skills: list, description: str) -> Optional[list]:
    """Try to generate questions via Cohere. Returns None on failure."""
    import os
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key or api_key == "your_cohere_key":
        return None
    try:
        import cohere
        client = cohere.Client(api_key)
        skills_str = ", ".join(skills[:8]) if skills else "general software skills"
        prompt = (
            f"You are a senior technical recruiter preparing for a {job_title} interview.\n"
            f"Required skills: {skills_str}\n"
            f"Job context: {description[:500]}\n\n"
            "Generate exactly 8 interview questions. Mix of:\n"
            "- 3 technical questions (directly testing the required skills)\n"
            "- 3 behavioral questions (STAR-format)\n"
            "- 1 system design question\n"
            "- 1 motivation question\n\n"
            "Format each question as:\n"
            "TYPE: [Technical/Behavioral/System Design/Motivation]\n"
            "Q: [The question]\n\n"
            "Be specific, not generic. Reference the actual skills and role context."
        )
        response = client.chat(
            model="command-r-plus-08-2024",
            message=prompt,
            temperature=0.5,
            max_tokens=800,
        )
        text = response.text.strip()
        # Parse response
        questions = []
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        for block in blocks:
            lines = block.split("\n")
            q_type = "Technical"
            q_text = ""
            for line in lines:
                if line.upper().startswith("TYPE:"):
                    q_type = line.split(":", 1)[1].strip()
                elif line.upper().startswith("Q:"):
                    q_text = line.split(":", 1)[1].strip()
            if q_text:
                questions.append({"type": q_type, "question": q_text})
        return questions if len(questions) >= 4 else None
    except Exception:
        return None


@router.post("/generate-questions")
async def generate_interview_questions(
    req: QuestionGenRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate 8-10 role-specific interview questions for a job.
    Uses Cohere if available; falls back to skills-based templates.
    """
    from database import jobs_col, candidates_col

    job = await jobs_col.find_one({"_id": ObjectId(req.job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_title = job.get("title", "Software Engineer")
    skills = job.get("required_skills", [])
    description = job.get("description", "")
    exp_years = 0.0

    # If candidate given, personalise
    candidate = None
    if req.candidate_id:
        try:
            candidate = await candidates_col.find_one({"_id": ObjectId(req.candidate_id)})
        except Exception:
            pass
    if candidate:
        exp_years = float(candidate.get("experience_years", 0))
        # Merge candidate skills with missing skills for targeted questions
        missing = candidate.get("missing_skills", [])
        if missing:
            skills = missing[:3] + [s for s in skills if s not in missing][:5]

    # Try Cohere first
    questions = await _cohere_questions(job_title, skills, description)

    # Template fallback
    if not questions:
        questions = _skills_based_questions(job_title, skills, exp_years)

    return {
        "job_title": job_title,
        "total": len(questions),
        "questions": questions,
        "generated_by": "cohere" if questions and len(questions) >= 8 else "template",
    }
