"""
utils/emailer.py
Sends fatigue alert emails via Gmail SMTP.

Requires in .env:
    EMAIL_ADDRESS=your_gmail@gmail.com
    EMAIL_APP_PASSWORD=your_16_char_app_password   (NOT your normal Gmail password)
    ALERT_RECIPIENT=shahanakarthikeyan0@gmail.com   (defaults to this if unset)

Gmail App Passwords require 2-Step Verification to be enabled on the
sending account. See: https://myaccount.google.com/apppasswords
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD, ALERT_RECIPIENT
from utils.logger import get_logger

log = get_logger("emailer")


def send_fatigue_alert(alerts: list, brand_name: str = None) -> dict:
    """
    Sends an email alert when creative fatigue is detected.
    Returns {"sent": bool, "reason": str} — never raises, so a failed
    email never crashes the fatigue check itself.
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        log.warning("Email not configured (EMAIL_ADDRESS / EMAIL_APP_PASSWORD missing in .env) — skipping alert.")
        return {"sent": False, "reason": "Email credentials not configured in .env"}

    if not alerts:
        return {"sent": False, "reason": "No fatigue alerts to send"}

    brand_label = brand_name or "Your brand"
    subject = f"⚠️ Creative Fatigue Alert — {brand_label}"

    body_lines = [
        f"Fatigue Monitor detected {len(alerts)} issue(s) with {brand_label}'s ad performance:\n",
    ]
    for a in alerts:
        body_lines.append(f"  • {a['message']}")
    body_lines.append("\nThis is an automated alert from your Competitive Creative Intelligence Engine.")
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ALERT_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, ALERT_RECIPIENT, msg.as_string())
        log.info("Fatigue alert email sent to %s", ALERT_RECIPIENT)
        return {"sent": True, "reason": f"Alert sent to {ALERT_RECIPIENT}"}
    except smtplib.SMTPAuthenticationError:
        log.error("Gmail authentication failed — check EMAIL_ADDRESS/EMAIL_APP_PASSWORD.")
        return {"sent": False, "reason": "Gmail authentication failed — check your App Password"}
    except Exception as e:
        log.error("Failed to send fatigue alert email: %s", e)
        return {"sent": False, "reason": f"Email send failed: {e}"}
