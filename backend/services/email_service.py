import os
import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
# Force load/reload env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)

# --- Security ---
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

def get_fernet():
    if not ENCRYPTION_KEY:
        logger.error("[EmailService] ENCRYPTION_KEY missing in .env!")
        return None
    try:
        return Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.error(f"[EmailService] Invalid ENCRYPTION_KEY: {e}")
        return None

def encrypt_password(password: str) -> str:
    f = get_fernet()
    if not f: return password
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    f = get_fernet()
    if not f: return encrypted_password
    try:
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return encrypted_password # Fallback if not encrypted

# --- Dynamic Settings ---
async def get_db_email_settings():
    """Bypassed: We only read email settings from .env now."""
    return None

def get_fallback_settings():
    """Returns settings from .env as fallback.
    No hardcoded defaults or stale overrides.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    user = os.getenv("SMTP_USERNAME")
    return {
        "smtp_host":     os.getenv("SMTP_SERVER"),
        "smtp_port":     int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else None,
        "smtp_user":     user,
        "smtp_password": os.getenv("SMTP_PASSWORD"),
        "from_email":    os.getenv("EMAIL_FROM") or user,
        "app_name":      os.getenv("APP_NAME"),
        "use_tls":       True,
    }


def print_env_diagnostics():
    """Call on startup to confirm .env loaded correctly."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    user = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    server = os.getenv("SMTP_SERVER")
    
    print("\n[SMTP RESET]", flush=True)
    print(f"SMTP USER FOUND: {'YES' if user else 'NO'}", flush=True)
    print(f"SMTP PASSWORD FOUND: {'YES' if password else 'NO'}", flush=True)
    print(f"SMTP SERVER: {server if server else 'NOT SET'}\n", flush=True)

# --- Core Sending Logic ---
async def send_email(to_email: str, subject: str, body_html: str, body_text: str = "", settings_override=None):
    """Sends an HTML email. Full step-by-step logging — no silent failures."""
    import traceback as _tb

    print(f"\n{'='*60}")
    print(f"[send_email] CALLED")
    print(f"  To      : {to_email}")
    print(f"  Subject : {subject}")

    # --- Load settings ---
    print("  [1] Loading SMTP settings...")
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    
    settings = settings_override or get_fallback_settings()

    smtp_host  = settings.get("smtp_host")
    smtp_port  = int(settings.get("smtp_port")) if settings.get("smtp_port") else None
    smtp_user  = settings.get("smtp_user")
    smtp_pass  = settings.get("smtp_password")
    from_email = settings.get("from_email")
    app_name   = settings.get("app_name") or "AI Hiring Platform"
    use_tls    = settings.get("use_tls", True)

    print(f"  [2] SMTP Config: host={smtp_host} port={smtp_port} user={smtp_user} from={from_email} pass={'SET' if smtp_pass else 'MISSING'}")

    # --- Validate credentials ---
    if not all([smtp_host, smtp_user, smtp_pass, from_email]):
        missing = [k for k, v in {"smtp_host": smtp_host, "smtp_user": smtp_user, "smtp_pass": smtp_pass, "from_email": from_email}.items() if not v]
        print(f"  [FATAL] Missing credentials: {missing}")
        print(f"  Hint: .env must use SMTP_USERNAME, SMTP_SERVER, SMTP_PORT, EMAIL_FROM, SMTP_PASSWORD")
        return False

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            print(f"  [3] Attempt {attempt + 1}: Building message...")
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{app_name} <{from_email}>"
            msg["To"]      = to_email
            if body_text:
                msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))
            print(f"  [3] Message built OK")

            print(f"  [4] Connecting to {smtp_host}:{smtp_port}...")
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                if use_tls:
                    print(f"  [4] Starting TLS...")
                    server.starttls()
            print(f"  [4] Connected OK")

            print(f"  [5] Logging in as {smtp_user}...")
            server.login(smtp_user, smtp_pass)
            print(f"  [5] Login SUCCESS")

            print(f"  [6] Sending message...")
            server.send_message(msg)
            server.quit()
            print(f"  [6] SENT SUCCESSFULLY to {to_email}")
            print(f"{'='*60}\n")
            return True

        except Exception as e:
            print(f"  [ERROR] Attempt {attempt + 1} FAILED: {e}")
            _tb.print_exc()
            if attempt < max_retries:
                print(f"  Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"  [FATAL] All attempts failed for {to_email}")
                print(f"{'='*60}\n")
                return False

async def test_smtp_connection(settings):
    """Verifies SMTP settings without sending a full email."""
    try:
        smtp_host = settings.get("smtp_host")
        smtp_port = int(settings.get("smtp_port", 587))
        smtp_user = settings.get("smtp_user")
        smtp_pass = settings.get("smtp_password")
        use_tls = settings.get("use_tls", True)

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if use_tls:
                server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.quit()
        return True, "Connection successful"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your user/password (use App Password for Gmail)."
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

# --- HTML Templates ---

def get_interview_scheduled_template(candidate_name, job_role, date, time, mode, meeting_link, app_name):
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #4f46e5; margin: 0; font-size: 24px;">Interview Scheduled</h1>
                <p style="color: #64748b; margin-top: 5px;">{app_name} Recruitment Team</p>
            </div>
            
            <p>Hi <strong>{candidate_name}</strong>,</p>
            <p>We are pleased to invite you for an interview for the <strong>{job_role}</strong> position. Here are the details:</p>
            
            <div style="background: #f1f5f9; padding: 25px; border-radius: 10px; margin: 25px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 5px 0; color: #64748b; width: 100px;">📅 Date</td><td style="font-weight: 600;">{date}</td></tr>
                    <tr><td style="padding: 5px 0; color: #64748b;">⏰ Time</td><td style="font-weight: 600;">{time}</td></tr>
                    <tr><td style="padding: 5px 0; color: #64748b;">📍 Mode</td><td style="font-weight: 600; text-transform: capitalize;">{mode}</td></tr>
                </table>
                {f'<div style="margin-top: 20px; text-align: center;"><a href="{meeting_link}" style="background: #4f46e5; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Join Interview</a></div>' if meeting_link else ''}
            </div>
            
            <p style="font-size: 14px; color: #64748b;">Please ensure you have a stable internet connection and are in a quiet place for the interview.</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
            <p style="font-size: 12px; color: #94a3b8; text-align: center;">This is an automated message from {app_name}.</p>
        </div>
    </body>
    </html>
    """

def get_reminder_template(candidate_name, job_role, time, meeting_link, minutes_left, app_name):
    color = "#4f46e5" if minutes_left > 10 else "#e11d48"
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; background-color: #fff1f2 if {minutes_left} <= 5 else #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 35px; border-radius: 12px; border: 2px solid {color};">
            <h2 style="color: {color}; margin-top: 0;">🔔 Interview Starting in {minutes_left} Mins</h2>
            <p>Hi,</p>
            <p>This is a quick reminder that your interview for <strong>{job_role}</strong> with <strong>{candidate_name}</strong> starts at <strong>{time}</strong>.</p>
            
            <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0; text-align: center;">
                {f'<a href="{meeting_link}" style="background: {color}; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block;">JOIN NOW</a>' if meeting_link else '<p>Please prepare for the call.</p>'}
            </div>
            
            <p style="font-size: 13px; color: #64748b;">Good luck!</p>
        </div>
    </body>
    </html>
    """

def get_status_update_template(candidate_name, job_role, status, app_name):
    is_shortlisted = status == "shortlisted"
    color = "#10b981" if is_shortlisted else "#64748b"
    title = "Congratulations! You've been shortlisted" if is_shortlisted else "Update regarding your application"
    
    message = f"We are excited to inform you that you have been <strong>shortlisted</strong> for the next round of the <strong>{job_role}</strong> position." if is_shortlisted else \
              f"Thank you for your interest in the <strong>{job_role}</strong> position. After careful review, we have decided not to move forward with your application at this time."

    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; border-top: 4px solid {color}; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <h2 style="color: {color}; margin-top: 0;">{title}</h2>
            <p>Hi <strong>{candidate_name}</strong>,</p>
            <p>{message}</p>
            {f'<p>Our recruitment team will reach out to you shortly with more details about the next steps.</p>' if is_shortlisted else '<p>We appreciate your time and effort, and we wish you the very best in your job search.</p>'}
            <br>
            <p>Best regards,<br>The {app_name} Team</p>
        </div>
    </body>
    </html>
    """
