"""Email delivery module supporting Resend, SendGrid, and AWS SES."""
import logging
import os
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential
from ..storage.models import WeeklyDigest, DeliveryLog

logger = logging.getLogger(__name__)

PROVIDER = os.environ.get("EMAIL_PROVIDER", "resend")  # resend | sendgrid | ses
FROM_EMAIL = os.environ.get("FROM_EMAIL", "intel@yourdomain.com")
FROM_NAME = os.environ.get("FROM_NAME", "Weekly Intel")


def send_digest(
    db: Session,
    digest: WeeklyDigest,
    recipients: list[str],
) -> list[DeliveryLog]:
    """Send the weekly digest to all recipients."""
    logs = []
    for recipient in recipients:
        log = _send_to_recipient(db, digest, recipient)
        logs.append(log)
    return logs


def _send_to_recipient(db: Session, digest: WeeklyDigest, recipient: str) -> DeliveryLog:
    log = DeliveryLog(
        digest_id=digest.id,
        recipient_email=recipient,
        provider=PROVIDER,
        status="pending",
        attempts=0,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()

    week_str = digest.week_start.strftime("%B %d, %Y")
    subject = f"Weekly Intel — Week of {week_str}"

    try:
        message_id = _send_with_retry(
            recipient=recipient,
            subject=subject,
            html=digest.html_content,
            plain_text=_html_to_plain(digest.markdown_content),
        )
        log.status = "sent"
        log.message_id = message_id
        log.sent_at = datetime.utcnow()
    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        logger.error(f"Failed to send to {recipient}: {e}")

    log.attempts += 1
    db.add(log)
    db.commit()
    return log


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _send_with_retry(recipient: str, subject: str, html: str, plain_text: str) -> str:
    """Send email with exponential backoff retry. Returns message_id."""
    if PROVIDER == "resend":
        return _send_resend(recipient, subject, html, plain_text)
    elif PROVIDER == "sendgrid":
        return _send_sendgrid(recipient, subject, html, plain_text)
    elif PROVIDER == "ses":
        return _send_ses(recipient, subject, html, plain_text)
    raise ValueError(f"Unknown provider: {PROVIDER}")


def _send_resend(recipient: str, subject: str, html: str, plain_text: str) -> str:
    import resend
    resend.api_key = os.environ["RESEND_API_KEY"]

    response = resend.Emails.send({
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [recipient],
        "subject": subject,
        "html": html,
        "text": plain_text,
        "headers": {
            "List-Unsubscribe": f"<mailto:{FROM_EMAIL}?subject=unsubscribe>",
        },
    })
    return response.get("id", "")


def _send_sendgrid(recipient: str, subject: str, html: str, plain_text: str) -> str:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Content, MimeType

    sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])
    message = Mail(
        from_email=f"{FROM_NAME} <{FROM_EMAIL}>",
        to_emails=recipient,
        subject=subject,
    )
    message.add_content(Content(MimeType.text, plain_text))
    message.add_content(Content(MimeType.html, html))

    response = sg.send(message)
    return response.headers.get("X-Message-Id", "")


def _send_ses(recipient: str, subject: str, html: str, plain_text: str) -> str:
    import boto3

    client = boto3.client(
        "ses",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    response = client.send_email(
        Source=f"{FROM_NAME} <{FROM_EMAIL}>",
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": plain_text, "Charset": "UTF-8"},
                "Html": {"Data": html, "Charset": "UTF-8"},
            },
        },
    )
    return response.get("MessageId", "")


def _html_to_plain(markdown_text: str) -> str:
    """Use markdown content as plain text fallback."""
    import re
    text = re.sub(r"#{1,6}\s", "", markdown_text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"\|.+\|", "", text)
    return text
