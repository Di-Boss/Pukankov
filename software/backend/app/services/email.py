import smtplib
from email.message import EmailMessage
from ..core.config import settings


def send_email(to, subject, text):
    if not settings.smtp_host or not settings.smtp_from:
        return False
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = settings.smtp_from
    msg["Subject"] = subject
    msg.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return True
