#!/usr/bin/env python3
"""Send the latest weekly digest via email."""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db, get_db
from src.storage.models import WeeklyDigest
from src.delivery.email import send_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Send the latest weekly digest")
    parser.add_argument(
        "--recipients",
        required=True,
        help="Comma-separated list of recipient email addresses",
    )
    parser.add_argument(
        "--digest-id",
        type=int,
        help="Specific digest ID to send (defaults to latest)",
    )
    args = parser.parse_args()

    recipients = [r.strip() for r in args.recipients.split(",") if r.strip()]
    if not recipients:
        logger.error("No recipients specified.")
        sys.exit(1)

    init_db()

    with get_db() as db:
        if args.digest_id:
            digest = db.query(WeeklyDigest).filter(WeeklyDigest.id == args.digest_id).first()
        else:
            digest = (
                db.query(WeeklyDigest)
                .order_by(WeeklyDigest.generated_at.desc())
                .first()
            )

        if not digest:
            logger.error("No digest found. Run the pipeline first.")
            sys.exit(1)

        logger.info(f"Sending digest (ID={digest.id}, week={digest.week_start.date()}) to {recipients}")
        logs = send_digest(db, digest, recipients)

        for log in logs:
            if log.status == "sent":
                logger.info(f"  ✓ Sent to {log.recipient_email} (message_id={log.message_id})")
            else:
                logger.error(f"  ✗ Failed to send to {log.recipient_email}: {log.error_message}")


if __name__ == "__main__":
    main()
