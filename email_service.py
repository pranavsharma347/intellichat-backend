# email_service.py  (backend folder mein, main.py ke saath rakho)
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM") or SMTP_USER
APP_ENV = os.getenv("APP_ENV", "dev")


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Email bhejta hai. True = gayi, False = nahi gayi (settings missing ya error)."""
    if not (SMTP_USER and SMTP_PASSWORD):
        print("EMAIL NOT CONFIGURED: SMTP_USER or SMTP_PASSWORD is empty in the running server")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"IntelliChat <{MAIL_FROM}>"
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print("EMAIL SENT:", subject)          # subject only, never the link or password
        return True
    except Exception as e:
        print("EMAIL FAILED:", type(e).__name__)   
        return False


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


#for sending email to user when they sign up
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
 



