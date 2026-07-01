"""Vercel serverless function: generate weekly digest."""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the most recent digest's rendered HTML."""
        from src.storage.database import init_db, get_db
        from src.storage.models import WeeklyDigest

        init_db()
        with get_db() as db:
            digest = (
                db.query(WeeklyDigest)
                .order_by(WeeklyDigest.generated_at.desc())
                .first()
            )
            html = digest.html_content if digest else None

        if not html:
            html = (
                "<!DOCTYPE html><html><body style=\"font-family:system-ui;"
                "max-width:640px;margin:80px auto;text-align:center;color:#555\">"
                "<h2>No digest yet</h2><p>Run the pipeline "
                "(Ingest → Process → Generate Digest) to create one.</p>"
                "</body></html>"
            )

        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        from src.storage.database import init_db, get_db
        from src.processing.clustering import cluster_week_items
        from src.digest.generator import generate_weekly_digest
        from datetime import timedelta
        import traceback

        try:
            init_db()

            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)

            with get_db() as db:
                cluster_week_items(db, week_start, week_end)
                digest = generate_weekly_digest(db, week_start)
                result = {
                    "digest_id": digest.id,
                    "week": week_start.strftime("%Y-W%W"),
                    "items_count": digest.items_count,
                    "markdown_path": digest.markdown_path,
                }
            status = 200
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"[:500],
                      "trace": traceback.format_exc()[-800:]}
            status = 500

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
