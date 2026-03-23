"""Layer 1: Gmail SMTP delivery with retry logic."""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries


def _build_message(html_content: str, subject: str, sender: str, recipient: str) -> MIMEMultipart:
    """Construct a MIME email with HTML body."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    return msg


def send_newsletter(
    html_content: str,
    subject: str,
    recipient: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Send the newsletter via Gmail SMTP with up to MAX_RETRIES attempts.

    Args:
        html_content: Rendered HTML string from newsletter.build_newsletter().
        subject:      Email subject line.
        recipient:    Destination address. Defaults to settings.NEWSLETTER_RECIPIENT.
        dry_run:      If True, print the email details but do not send.

    Returns:
        True on success, False if all retries fail.
    """
    recipient = recipient or settings.NEWSLETTER_RECIPIENT

    if dry_run:
        print(f"[dry-run] Would send email:")
        print(f"  To:      {recipient}")
        print(f"  Subject: {subject}")
        print(f"  Size:    {len(html_content):,} chars")
        return True

    settings.validate(["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "NEWSLETTER_RECIPIENT"])

    sender = settings.GMAIL_ADDRESS
    msg = _build_message(html_content, subject, sender, recipient)

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(sender, settings.GMAIL_APP_PASSWORD)
                smtp.sendmail(sender, [recipient], msg.as_string())

            print(f"Email sent → {recipient} (attempt {attempt})")
            return True

        except smtplib.SMTPAuthenticationError as e:
            # Wrong credentials — no point retrying
            print(f"SMTP authentication failed: {e}")
            raise

        except Exception as e:
            last_error = e
            print(f"Send attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print(f"All {MAX_RETRIES} send attempts failed. Last error: {last_error}")
    return False
