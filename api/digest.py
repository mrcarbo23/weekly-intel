"""Vercel serverless function: generate weekly digest."""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        from src.storage.database import init_db, get_db
        from src.processing.clustering import cluster_week_items
        from src.digest.generator import generate_weekly_digest
        from datetime import timedelta
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

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
