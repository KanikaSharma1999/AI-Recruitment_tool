from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from database import settings_col
from models import EmailSettings
from services.email_service import (
    encrypt_password,
    decrypt_password,
    test_smtp_connection,
    send_email,
    get_db_email_settings,
    get_fallback_settings,
)
from pydantic import BaseModel, Field
import smtplib
import traceback as tb
import os
from datetime import datetime

router = APIRouter(prefix="/settings", tags=["settings"])


class TestEmailRequest(BaseModel):
    settings: EmailSettings
    target_email: str


def update_env_file(updates: dict):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    new_lines = []
    keys_updated = set()
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        
        if "=" in line:
            parts = line.split("=", 1)
            key = parts[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_updated.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    for key, val in updates.items():
        if key not in keys_updated:
            new_lines.append(f"{key}={val}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


@router.get("/email")
async def get_email_settings(current_user=Depends(get_current_user)):
    """Retrieve email settings from DB, masking the password."""
    email = current_user["email"]
    
    doc = await settings_col.find_one({"type": "email_config", "email": email})
    if not doc:
        return {
            "provider": "gmail",
            "smtp_host": "",
            "smtp_port": "",
            "smtp_user": "",
            "smtp_password": "",
            "from_email": "",
            "app_name": "HireIQ",
            "use_tls": True
        }
        
    smtp_password = doc.get("smtp_password", "")
    masked_password = ""
    if smtp_password:
        masked_password = "********"
        
    return {
        "provider": "gmail",
        "smtp_host": doc.get("smtp_host", ""),
        "smtp_port": doc.get("smtp_port", ""),
        "smtp_user": doc.get("smtp_user", ""),
        "smtp_password": masked_password,
        "from_email": doc.get("from_email", ""),
        "app_name": doc.get("app_name", "HireIQ"),
        "use_tls": doc.get("use_tls", True)
    }


@router.post("/email")
async def save_email_settings(settings: EmailSettings, current_user=Depends(get_current_user)):
    """Save/Update email settings securely in MongoDB per recruiter."""
    user_id = str(current_user["_id"])
    email = current_user["email"]
    config_dict = settings.model_dump()
    
    smtp_password = config_dict.get("smtp_password", "")
    if smtp_password == "********":
        existing = await settings_col.find_one({"type": "email_config", "email": email})
        if existing:
            smtp_password = existing.get("smtp_password", "")
        else:
            smtp_password = ""
    else:
        from services.email_service import encrypt_password
        smtp_password = encrypt_password(smtp_password)
        
    doc = {
        "type": "email_config",
        "user_id": user_id,
        "email": email,
        "smtp_host": config_dict.get("smtp_host", ""),
        "smtp_port": config_dict.get("smtp_port"),
        "smtp_user": config_dict.get("smtp_user", ""),
        "smtp_password": smtp_password,
        "from_email": config_dict.get("from_email", ""),
        "app_name": config_dict.get("app_name", "HireIQ"),
        "use_tls": config_dict.get("use_tls", True),
        "updated_at": datetime.utcnow()
    }
    
    await settings_col.update_one(
        {"type": "email_config", "email": email},
        {"$set": doc},
        upsert=True
    )
    return {"message": "Email settings saved successfully"}


@router.post("/test-email")
async def send_test_email(req: TestEmailRequest, current_user=Depends(get_current_user)):
    """Test SMTP configuration by sending a real email."""
    email = current_user["email"]
    test_settings = req.settings.model_dump()
    
    if test_settings["smtp_password"] == "********":
        existing = await settings_col.find_one({"type": "email_config", "email": email})
        if existing:
            from services.email_service import decrypt_password
            test_settings["smtp_password"] = decrypt_password(existing.get("smtp_password", ""))
        else:
            test_settings["smtp_password"] = ""
            
    success, message = await test_smtp_connection(test_settings)
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #4f46e5;">Test Email Successful!</h2>
        <p>This email confirms that your SMTP settings are configured correctly for <b>{test_settings['app_name']}</b>.</p>
        <p><b>Provider:</b> {test_settings.get('provider','')}</p>
        <p><b>User:</b> {test_settings['smtp_user']}</p>
    </div>
    """
    sent = await send_email(
        to_email=req.target_email,
        subject=f"Test Email: {test_settings['app_name']}",
        body_html=html,
        settings_override=test_settings,
    )
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send test email despite successful connection.")
    return {"message": "Test email sent successfully to " + req.target_email}



# ─────────────────────────────────────────────────────────────────────────────
# POST /settings/debug-email
# Full SMTP diagnostic — accessible to ANY logged-in HR user (no admin needed).
# Tests .env vars, DB config, SMTP connection, login, and actually sends a mail.
# Returns detailed JSON so HR can see exactly what is failing.
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/debug-email")
async def debug_email_route(current_user=Depends(get_current_user)):
    """
    Full SMTP debug test. Sends a real test email to the logged-in HR user.
    Exposes every step with exact error messages — no silent failures.
    """
    hr_email = current_user.get("email")

    result = {
        "target_recipient": hr_email,
        "env_vars": {},
        "db_settings_found": False,
        "smtp_host": None,
        "smtp_port": None,
        "smtp_user": None,
        "from_email": None,
        "smtp_password_set": False,
        "smtp_connected": False,
        "login_success": False,
        "mail_sent": False,
        "error": None,
        "traceback": None,
        "recommendation": None,
    }

    # Step 1 — Show .env variable values
    result["env_vars"] = {
        "SMTP_SERVER":  os.getenv("SMTP_SERVER", "NOT SET"),
        "SMTP_PORT":    os.getenv("SMTP_PORT", "NOT SET"),
        "SMTP_USER":    os.getenv("SMTP_USER", "NOT SET"),
        "EMAIL_FROM":   os.getenv("EMAIL_FROM", "NOT SET"),
        "SMTP_PASSWORD": "SET ✓" if os.getenv("SMTP_PASSWORD") else "NOT SET ✗",
    }

    # Step 2 — Load settings (DB → .env fallback)
    try:
        db_cfg = await get_db_email_settings()
        result["db_settings_found"] = bool(db_cfg)
        settings = db_cfg or get_fallback_settings()
    except Exception as e:
        result["error"] = f"Failed to load email settings: {e}"
        result["traceback"] = tb.format_exc()
        return result

    smtp_host  = settings.get("smtp_host")
    smtp_port  = int(settings.get("smtp_port", 587))
    smtp_user  = settings.get("smtp_user")
    smtp_pass  = settings.get("smtp_password")
    from_email = settings.get("from_email")
    use_tls    = settings.get("use_tls", True)

    result.update({
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "from_email": from_email,
        "smtp_password_set": bool(smtp_pass),
    })

    # Step 3 — Validate all required fields are present
    missing = [k for k, v in {
        "smtp_host": smtp_host, "smtp_user": smtp_user,
        "smtp_password": smtp_pass, "from_email": from_email,
    }.items() if not v]

    if missing:
        result["error"] = f"Missing SMTP credentials: {missing}"
        result["recommendation"] = (
            "Open Settings → Email Configuration and complete all fields. "
            "For Gmail: Host=smtp.gmail.com, Port=587, TLS=ON. "
            "IMPORTANT: Use a Gmail App Password — NOT your regular Gmail password. "
            "Generate one at: https://myaccount.google.com/apppasswords"
        )
        return result

    # Step 4 — Test SMTP connection and login
    try:
        print(f"[DEBUG-EMAIL] Connecting to {smtp_host}:{smtp_port} (TLS={use_tls})")
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            if use_tls:
                server.starttls()
        result["smtp_connected"] = True
        print(f"[DEBUG-EMAIL] Connected. Attempting login as {smtp_user}...")

        server.login(smtp_user, smtp_pass)
        result["login_success"] = True
        print(f"[DEBUG-EMAIL] Login SUCCESS for {smtp_user}")
        server.quit()

    except smtplib.SMTPAuthenticationError as e:
        result["error"] = f"Authentication failed: {e}"
        result["traceback"] = tb.format_exc()
        result["recommendation"] = (
            "LOGIN FAILED. This is the most common issue. "
            "For Gmail you MUST use a 16-character App Password — not your normal Gmail password. "
            "Steps: Google Account → Security → 2-Step Verification → App Passwords → "
            "Select app: Mail → Generate → paste the 16-char code as your SMTP password."
        )
        print(f"[DEBUG-EMAIL] AUTH FAILED: {e}")
        return result

    except Exception as e:
        result["error"] = f"SMTP connection error: {e}"
        result["traceback"] = tb.format_exc()
        result["recommendation"] = f"Cannot reach {smtp_host}:{smtp_port}. Check firewall/host settings."
        print(f"[DEBUG-EMAIL] CONNECTION ERROR: {e}")
        return result

    # Step 5 — Send real test mail to HR
    try:
        html_body = f"""
        <div style="font-family:sans-serif;padding:24px;border:1px solid #e2e8f0;border-radius:12px;max-width:560px">
            <h2 style="color:#4f46e5;margin-top:0">✅ ATS Email Test — Success</h2>
            <p>This confirms your SMTP configuration is working correctly.</p>
            <table style="font-size:13px;margin:16px 0;border-collapse:collapse">
                <tr><td style="color:#64748b;padding:4px 12px 4px 0"><b>SMTP Host</b></td><td>{smtp_host}:{smtp_port}</td></tr>
                <tr><td style="color:#64748b;padding:4px 12px 4px 0"><b>SMTP User</b></td><td>{smtp_user}</td></tr>
                <tr><td style="color:#64748b;padding:4px 12px 4px 0"><b>Delivered to</b></td><td>{hr_email}</td></tr>
            </table>
            <p style="color:#10b981;font-weight:700">HR interview scheduling emails will now work correctly.</p>
        </div>
        """
        print(f"[DEBUG-EMAIL] Sending test mail to {hr_email}...")
        sent = await send_email(hr_email, "ATS Email Test — SMTP Working ✅", html_body)
        result["mail_sent"] = sent
        if not sent:
            result["error"] = "send_email() returned False after successful login — check server console for traceback."
        else:
            print(f"[DEBUG-EMAIL] Test mail DELIVERED to {hr_email}")
    except Exception as e:
        result["error"] = f"send_email raised exception: {e}"
        result["traceback"] = tb.format_exc()
        print(f"[DEBUG-EMAIL] SEND ERROR: {e}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Recruiter Ranking Configuration Settings
# ─────────────────────────────────────────────────────────────────────────────

class RankingWeights(BaseModel):
    skills: int = Field(..., ge=0, le=100)
    experience: int = Field(..., ge=0, le=100)
    semantic: int = Field(..., ge=0, le=100)
    projects: int = Field(..., ge=0, le=100)
    certifications: int = Field(..., ge=0, le=100)
    quality: int = Field(..., ge=0, le=100)

class RankingConfigUpdate(BaseModel):
    preset: str
    weights: RankingWeights

@router.get("/ranking")
async def get_ranking_config(current_user=Depends(get_current_user)):
    """Retrieve the recruiter's ranking configuration."""
    user_id = str(current_user["_id"])
    email = current_user["email"]
    
    config = await settings_col.find_one({
        "type": "ranking_config",
        "$or": [{"user_id": user_id}, {"email": email}]
    })
    
    if not config:
        return {
            "preset": "Software Engineer",
            "weights": {
                "skills": 40,
                "experience": 25,
                "semantic": 15,
                "projects": 10,
                "certifications": 5,
                "quality": 5
            }
        }
        
    return {
        "preset": config.get("preset", "Custom"),
        "weights": config.get("weights", {
            "skills": 40,
            "experience": 25,
            "semantic": 15,
            "projects": 10,
            "certifications": 5,
            "quality": 5
        })
    }

@router.post("/ranking")
async def save_ranking_config(config: RankingConfigUpdate, current_user=Depends(get_current_user)):
    """Save the recruiter's ranking configuration."""
    weights = config.weights
    total = (
        weights.skills +
        weights.experience +
        weights.semantic +
        weights.projects +
        weights.certifications +
        weights.quality
    )
    
    if total != 100:
        raise HTTPException(
            status_code=400,
            detail=f"The total sum of weights must be exactly 100%. Current total is {total}%."
        )
        
    user_id = str(current_user["_id"])
    email = current_user["email"]
    
    await settings_col.update_one(
        {"type": "ranking_config", "$or": [{"user_id": user_id}, {"email": email}]},
        {
            "$set": {
                "type": "ranking_config",
                "user_id": user_id,
                "email": email,
                "preset": config.preset,
                "weights": config.weights.model_dump(),
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {"message": "Ranking configuration saved successfully"}

async def get_recruiter_weights(current_user) -> dict:
    """Helper function to load dynamic recruiter weights, falling back to default software engineer weights."""
    if not current_user:
        return {
            "skills": 0.40,
            "experience": 0.25,
            "semantic": 0.15,
            "projects": 0.10,
            "certifications": 0.05,
            "quality": 0.05
        }
    user_id = str(current_user.get("_id", ""))
    email = current_user.get("email", "")
    
    config = await settings_col.find_one({
        "type": "ranking_config",
        "$or": [{"user_id": user_id}, {"email": email}]
    })
    
    if not config or "weights" not in config:
        return {
            "skills": 0.40,
            "experience": 0.25,
            "semantic": 0.15,
            "projects": 0.10,
            "certifications": 0.05,
            "quality": 0.05
        }
        
    w = config["weights"]
    return {
        "skills": float(w.get("skills", 40)) / 100.0,
        "experience": float(w.get("experience", 25)) / 100.0,
        "semantic": float(w.get("semantic", 15)) / 100.0,
        "projects": float(w.get("projects", 10)) / 100.0,
        "certifications": float(w.get("certifications", 5)) / 100.0,
        "quality": float(w.get("quality", 5)) / 100.0
    }
