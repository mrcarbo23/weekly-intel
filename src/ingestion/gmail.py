"""Gmail API ingestion for newsletters."""
import base64
import email
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Build authenticated Gmail service."""
    creds = None
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "gmail_token.json")
    creds_path = os.environ.get("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(creds_path):
            # Interactive OAuth is only possible in a local/dev environment with
            # a browser. It cannot run in a serverless deployment.
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise RuntimeError(
                "Gmail is not authenticated in this environment: no valid token "
                f"at GMAIL_TOKEN_PATH ({token_path}) and no client secrets at "
                f"GMAIL_CREDENTIALS_PATH ({creds_path}). Authenticate locally to "
                "generate a token, or remove/deactivate the gmail source."
            )
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_newsletters(
    senders: list[str] = None,
    label: str = "Newsletters",
    days_back: int = 7,
) -> list[dict]:
    """
    Fetch newsletters from Gmail.
    senders: list of sender email addresses to filter
    label: Gmail label to read from (alternative to sender filter)
    days_back: how many days back to look
    """
    service = get_gmail_service()

    query_parts = []
    after_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query_parts.append(f"after:{after_date}")

    if senders:
        sender_query = " OR ".join(f"from:{s}" for s in senders)
        query_parts.append(f"({sender_query})")
    elif label:
        query_parts.append(f"label:{label}")

    query = " ".join(query_parts)

    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])

    newsletters = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        parsed = _parse_message(msg)
        if parsed:
            newsletters.append(parsed)

    return newsletters


def _parse_message(msg: dict) -> Optional[dict]:
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

    subject = headers.get("Subject", "")
    sender = headers.get("From", "")
    date_str = headers.get("Date", "")

    body = _extract_body(msg["payload"])
    if not body:
        return None

    return {
        "title": subject,
        "author": sender,
        "url": f"gmail://message/{msg['id']}",
        "publish_date": _parse_email_date(date_str),
        "raw_content": body,
        "message_id": msg["id"],
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract text body from MIME payload."""
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator=" ", strip=True)

    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


def _parse_email_date(date_str: str) -> datetime:
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()
