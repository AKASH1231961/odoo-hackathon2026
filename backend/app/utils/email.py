import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate, make_msgid
from app.core.config import settings


def send_email(
    to: str,
    subject: str,
    body: str,
    attachment: bytes = None,
    attachment_name: str = None,
) -> bool:
    """
    Send a plain-text email via SMTP.
    Attaches a PDF if `attachment` bytes are provided.
    Returns False on failure instead of raising, so billing never aborts on email;
    callers that report to a person must check the result.
    """
    msg = MIMEMultipart()
    msg["From"] = formataddr(("Brightloop Software", settings.SMTP_FROM))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=settings.SMTP_FROM.rpartition("@")[2])
    msg.attach(MIMEText(body, "plain"))

    if attachment and attachment_name:
        part = MIMEApplication(attachment, Name=attachment_name)
        part["Content-Disposition"] = f'attachment; filename="{attachment_name}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            if server.has_extn("starttls"):
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            elif settings.SMTP_USER:
                raise smtplib.SMTPException("Server offers no encryption; refusing to send the password")
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to, msg.as_string())
        return True
    except Exception as exc:
        print(f"[email] Failed to send to {to}: {exc}")
        return False

