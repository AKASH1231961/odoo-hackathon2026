import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from app.core.config import settings


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment: bytes = None,
    attachment_name: str = None,
):
    """
    Send a plain-text email via SMTP.
    Attaches a PDF if `attachment` bytes are provided.
    Failures are logged but never raise — billing tasks must not fail due to email.
    """
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment and attachment_name:
        part = MIMEApplication(attachment, Name=attachment_name)
        part["Content-Disposition"] = f'attachment; filename="{attachment_name}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to, msg.as_string())
    except Exception as exc:
        # Log but never re-raise — email failure must not abort billing
        print(f"[email] Failed to send to {to}: {exc}")

