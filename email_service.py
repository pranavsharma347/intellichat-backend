import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM") or SMTP_USER
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "IntelliChat")
APP_ENV = os.getenv("APP_ENV", "dev")


def _send_via_brevo(to: str, subject: str, text: str, html: str | None) -> bool:
    """Send email via Brevo API. Returns True if successful, False otherwise.`"""
    payload = {
        "sender": {"name": MAIL_FROM_NAME, "email": MAIL_FROM},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
    }
    if html:
        payload["htmlContent"] = html

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        return False
    except Exception as e:
        return False


def _send_via_smtp(to: str, subject: str, text: str, html: str | None) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("EMAIL FAILED (SMTP):", type(e).__name__)   
        return False


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Email bhejta hai. True = gayi, False = nahi gayi (settings missing ya error)."""
    if BREVO_API_KEY and MAIL_FROM:
        ok = _send_via_brevo(to, subject, text, html)
    elif SMTP_USER and SMTP_PASSWORD:
        ok = _send_via_smtp(to, subject, text, html)
    else:
        return False

    if ok:
        print("EMAIL SENT:", subject)          # subject only, never the link or password
    return ok


def _button_email(heading: str, intro: str, button_text: str, link: str, footer: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;color:#111">
      <h2 style="color:#FF7B00;margin:0 0 16px">IntelliChat</h2>
      <h3 style="margin:0 0 8px">{heading}</h3>
      <p style="color:#444;line-height:1.5">{intro}</p>
      <p style="margin:24px 0">
        <a href="{link}" style="background:#FF7B00;color:#fff;text-decoration:none;
           padding:12px 24px;border-radius:999px;font-weight:bold;display:inline-block">{button_text}</a>
      </p>
      <p style="color:#666;font-size:13px;line-height:1.5">{footer}</p>
      <p style="color:#888;font-size:12px;word-break:break-all">Button kaam na kare to ye link browser mein kholo:<br>{link}</p>
    </div>
    """


def send_reset_email(to: str, link: str) -> None:
    ok = send_email(
        to,
        "Reset your IntelliChat password",
        f"Reset your IntelliChat password using this link (valid for 15 minutes):\n{link}\n\n"
        "If you did not ask for this, you can ignore this email.",
        _button_email(
            "Reset your password",
            "We got a request to reset your password. This link works for 15 minutes.",
            "Reset password",
            link,
            "If you did not ask for this, you can safely ignore this email.",
        ),
    )
    if not ok and APP_ENV == "dev":
        print("RESET LINK (dev only):", link)


def send_verification_email(to: str, link: str) -> None:
    ok = send_email(
        to,
        "Verify your IntelliChat email",
        f"Welcome to IntelliChat! Verify your email using this link (valid for 24 hours):\n{link}\n\n"
        "If you did not create an account, you can ignore this email.",
        _button_email(
            "Verify your email",
            "Thanks for signing up. Please confirm this email address to activate your account. "
            "This link works for 24 hours.",
            "Verify email",
            link,
            "If you did not create an account, you can safely ignore this email.",
        ),
    )
    if not ok and APP_ENV == "dev":
        print("VERIFY LINK (dev only):", link)