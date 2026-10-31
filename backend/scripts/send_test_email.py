"""
Sends one email using the settings in .env, to prove delivery works.
Run: python scripts/send_test_email.py you@example.com
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.utils.email import send_email


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/send_test_email.py you@example.com")
    print(f"Sending through {settings.SMTP_HOST}:{settings.SMTP_PORT} as {settings.SMTP_FROM}")
    sent = send_email(sys.argv[1], "Brightloop test email", "Email from Brightloop is working.")
    print("Sent. Check the inbox and the spam folder." if sent else "Not sent. The reason is printed above.")
    sys.exit(0 if sent else 1)


if __name__ == "__main__":
    main()
