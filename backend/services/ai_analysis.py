import os
import re
import numpy as np
from bson import ObjectId
from datetime import datetime
from database import candidates_col

class MultimodalAnalyzer:
    """
    Enterprise-grade AI Interview Analysis Engine.
    Prioritizes actual detected behavior over generative guesses.
    """

    def __init__(self, face_stats, transcripts, resume_score):
        self.face_stats = face_stats
        self.transcripts = transcripts
        self.resume_score = float(resume_score or 0.0)
        self.total_seconds = len(face_stats) * 5 if face_stats else 0
        
    def analyze(self):
        # 1. Behavioral Analysis (Video/Gaze/Posture)
        video_metrics = self._analyze_behavioral()
        
        # 2. Communication Analysis (Audio/Speech/Clarity)
        speech_metrics = self._analyze_communication()
        
        # 3. Security & Proctoring (Cheating Detection)
        security_metrics = self._analyze_proctoring()
        
        # 4. Data Quality & Analysis Confidence
        quality_metrics = self._assess_data_quality(video_metrics, speech_metrics)
        
        # 5. Final Aggregation & Expert Recommendation
        return self._aggregate_intelligence(video_metrics, speech_metrics, security_metrics, quality_metrics)

    def _analyze_behavioral(self):
        """Analyzes gaze, head pose, and presence."""
        if not self.face_stats:
            return {"eye_contact": 0, "stability": 0, "attention": 0, "level": "Insufficient Data", "timeline": []}
            
        timeline = []
        eye_contact_vals = []
        no_face_events = 0
        
        for i, chunk in enumerate(self.face_stats):
            looking_away = chunk.get("looking_away_count", 0)
            no_face = chunk.get("no_face_count", 0)
            if no_face > 5: no_face_events += 1
            
            # Stricter focus calculation
            focus = max(0, 100 - (looking_away * 10) - (no_face * 25))
            
            # Mark event if focus drops below 30
            event = None
            if focus < 30:
                event = "Distracted" if no_face < 5 else "Left Frame"
                
            timeline.append({"time": i * 5, "focus": focus, "event": event})
            eye_contact_vals.append(focus)

        avg_eye_contact = np.mean(eye_contact_vals) if eye_contact_vals else 0
        stability = 100 - (no_face_events * 10)
        stability = max(0, min(100, stability))
        
        # Conservative Levels
        if avg_eye_contact > 85: level = "High"
        elif avg_eye_contact > 70: level = "Focused"
        elif avg_eye_contact > 45: level = "Variable"
        else: level = "Weak"
        
        return {
            "eye_contact": round(avg_eye_contact, 1),
            "stability": round(stability, 1),
            "attention": round(avg_eye_contact * 0.8 + stability * 0.2, 1),
            "level": level,
            "timeline": timeline,
            "no_face_count": no_face_events
        }

    def _analyze_communication(self):
        """Analyzes speech, silence, and confidence with stricter calibration."""
        full_text = " ".join(self.transcripts)
        words = full_text.split()
        word_count = len(words)
        
        # 1. Speaking Duration
        speaking_secs = word_count / 2.0 # Conservative estimate (2 words/sec)
        silence_secs = max(0, self.total_seconds - speaking_secs)
        speaking_ratio = (speaking_secs / max(1, self.total_seconds)) * 100
        
        # 2. Filler Detection
        fillers = ["um", "uh", "ah", "like", "basically", "actually", "sort of", "kind of"]
        filler_count = sum(1 for w in words if w.lower() in fillers)
        filler_density = (filler_count / max(1, word_count)) * 100
        
        # 3. Stricter Communication Score
        # Start low, earn points.
        comm_score = 20 # Base for presence
        if word_count > 50:
            # Earn up to 50 pts for ratio (ideal 30-60%)
            if 30 <= speaking_ratio <= 65: comm_score += 50
            else: comm_score += min(30, speaking_ratio)
            
            # Earn up to 30 pts for low fillers
            filler_penalty = filler_density * 4
            comm_score += max(0, 30 - filler_penalty)
        
        # Final Leveling
        if word_count < 30: level = "Very Limited"
        elif comm_score > 85: level = "Professional"
        elif comm_score > 70: level = "Articulate"
        elif comm_score > 50: level = "Conversational"
        else: level = "Needs Improvement"
        
        if speaking_ratio < 15:
            level = "Mostly Silent"
            comm_score = min(20, comm_score)

        return {
            "score": round(comm_score, 1),
            "level": level,
            "speaking_ratio": round(speaking_ratio, 1),
            "filler_count": filler_count,
            "word_count": word_count,
            "silence_secs": round(silence_secs, 1)
        }

    def _analyze_proctoring(self):
        """High-sensitivity security and proctoring detection with categorization."""
        if not self.face_stats:
            return {"risk_score": 0, "level": "Unknown", "evidence": []}
            
        multiple_faces = sum(s.get("multiple_faces_count", 0) for s in self.face_stats)
        tab_switches = sum(s.get("tab_switches", 0) for s in self.face_stats)
        copy_paste = sum(s.get("copy_paste_count", 0) for s in self.face_stats)
        
        # Sharp risk escalation
        risk = (multiple_faces * 60) + (tab_switches * 35) + (copy_paste * 20)
        risk = min(100, risk)
        
        evidence = []
        event_log = []
        
        # Categorized Events
        if multiple_faces > 0:
            msg = f"Multiple individuals detected in frame ({multiple_faces} instances)."
            evidence.append(msg)
            event_log.append({"category": "Integrity", "severity": "Critical", "message": msg, "time": "Multiple"})
            
        if tab_switches > 0:
            msg = f"Browser focus lost/Tab switched ({tab_switches} times)."
            evidence.append(msg)
            event_log.append({"category": "Attention", "severity": "Moderate", "message": msg, "time": "Variable"})
            
        if copy_paste > 0:
            msg = "Suspicious clipboard (copy/paste) usage detected."
            evidence.append(msg)
            event_log.append({"category": "Integrity", "severity": "High", "message": msg, "time": "Instant"})

        # Add generic events from raw stats
        for stat in self.face_stats:
            for e in stat.get("suspicious_events", []):
                cat = "Attention" if "face" in e.lower() or "look" in e.lower() else "Security"
                event_log.append({
                    "category": cat,
                    "severity": "Low" if "look" in e.lower() else "Moderate",
                    "message": e,
                    "time": "T-Event"
                })

        if risk > 80: level = "Critical"
        elif risk > 50: level = "High Risk"
        elif risk > 20: level = "Suspicious"
        else: level = "Clean"
        
        return {
            "risk_score": round(risk, 1),
            "level": level,
            "evidence": evidence,
            "event_log": event_log
        }

    def _assess_data_quality(self, video, comms):
        """Determines if the analysis is reliable."""
        total_time = self.total_seconds
        total_words = comms["word_count"]
        
        # Stricter production thresholds
        if total_time < 90 or total_words < 40:
            return {"confidence": "Low", "reason": "Insufficient interview duration or limited verbal data (minimum 90s required)"}
        if video["eye_contact"] < 35:
            return {"confidence": "Medium", "reason": "Weak visual signal (candidate frequently out of frame or obscured)"}
        return {"confidence": "High", "reason": "Sufficient multimodal data collected"}

    def _aggregate_intelligence(self, video, comms, security, quality):
        """Final conservative synthesis with extreme calibration."""
        # 1. Base Confidence (harder to earn)
        base_score = (video["eye_contact"] * 0.35) + (comms["score"] * 0.45)
        if quality["confidence"] == "High": base_score += 20
        elif quality["confidence"] == "Medium": base_score += 10
        
        # 2. Penalty Application (Doubled for enterprise)
        penalty = security["risk_score"] * 1.2
        final_confidence = max(0, base_score - penalty)
        
        # 3. Decision Logic (Elite thresholds)
        perf_index = (video["attention"] * 0.4 + comms["score"] * 0.6)
        hiring_index = (self.resume_score * 0.3) + (perf_index * 0.7)
        
        if security["level"] in ["Critical", "High Risk"]:
            recommendation = "Reject"
            verdict = "Security/Integrity Failure"
        elif hiring_index > 92 and comms["level"] == "Professional" and video["level"] == "High" and security["level"] == "Clean":
            recommendation = "Strong Hire"
            verdict = "Exceptional Fit & Peerless Integrity"
        elif hiring_index > 72 and comms["score"] > 65:
            recommendation = "Hire"
            verdict = "Competent Professional Performance"
        elif hiring_index > 50:
            recommendation = "Hold"
            verdict = "Marginal Behavioral/Technical Fit"
        else:
            recommendation = "Reject"
            verdict = "Below Target Performance Thresholds"

        if quality["confidence"] == "Low":
            verdict = f"Inconclusive: {quality['reason']}"
            recommendation = "Hold"

        return {
            "communication": comms["level"],
            "confidence": quality["confidence"],
            "attention": video["level"],
            "cheating_risk": security["level"],
            "recommendation": recommendation,
            "verdict": verdict,
            "reasoning": f"Analysis grounded in {quality['confidence'].lower()} quality behavioral data. {quality.get('reason', '')}",
            "metrics": {
                "comm_score": comms["score"],
                "conf_score": round(final_confidence, 1),
                "risk_score": security["risk_score"],
                "attention_score": video["attention"],
                "speaking_ratio": comms["speaking_ratio"],
                "word_count": comms["word_count"]
            },
            "timeline": video["timeline"],
            "security_evidence": security["evidence"],
            "event_log": security["event_log"],
            "analysis_confidence": quality["confidence"]
        }


async def generate_interview_feedback(candidate_id: str) -> dict:
    candidate = await candidates_col.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise ValueError("Candidate not found")

    face_stats = candidate.get("face_stats", [])
    transcripts = candidate.get("transcript", [])
    resume_score = float(candidate.get("score", 0.0))

    analyzer = MultimodalAnalyzer(face_stats, transcripts, resume_score)
    result = analyzer.analyze()

    # Try to enhance with Cohere for a more human summary (Optional)
    api_key = os.getenv("COHERE_API_KEY")
    if api_key and transcripts:
        try:
            import cohere
            client = cohere.Client(api_key)
            prompt = (
                "You are an Elite Executive Recruiter writing internal notes about a candidate's behavior. "
                "Provide a concise, objective evaluation of this candidate's performance. \n\n"
                "DETECTED DATA:\n"
                f"- Confidence Level: {result['analysis_confidence']}\n"
                f"- Communication: {result['communication']} ({result['metrics']['word_count']} words used)\n"
                f"- Visual Presence: {result['attention']}\n"
                f"- Security Status: {result['cheating_risk']}\n"
                f"- Verdict: {result['verdict']}\n\n"
                "STRICT EVALUATION RULES:\n"
                "1. WRITE LIKE A HUMAN RECRUITER. (e.g., 'Candidate struggled with clarity' vs 'Communication is low').\n"
                "2. NO GENERIC AI PRAISE. Do not use words like 'excellent', 'fantastic', or 'great' unless data is perfect.\n"
                "3. BE CONSERVATIVE. If communication was variable, note the inconsistency.\n"
                "4. HIGHLIGHT CONCERNS. Mention if visual attention was lacking or if integrity events occurred.\n"
                "5. FORMAT: Two concise, professional bullet points."
            )
            resp = client.chat(model="command-r-plus-08-2024", message=prompt)
            result["reasoning"] = resp.text.strip()
        except Exception:
            pass

    # Save to candidate doc
    await candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"ai_analysis": result, "status": "interview_analyzed"}}
    )

    return result
