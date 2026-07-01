"""Vercel serverless function: trigger ingestion."""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import init_db, get_db
from src.storage.models import Source


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        init_db()
        from scripts.run_pipeline import ingest_source

        total_new = 0
        report = []
        with get_db() as db:
            sources = db.query(Source).filter(Source.active == True).all()
            for source in sources:
                entry = {"name": source.name, "source_type": source.source_type}
                # Isolate each source: one misconfigured/failing source (e.g. a
                # gmail source without OAuth creds, or a substack source with no
                # URL) must not abort ingestion of the others.
                try:
                    new_items = ingest_source(db, source)
                    entry["new_items"] = new_items
                    entry["status"] = "ok"
                    total_new += new_items
                except Exception as exc:
                    db.rollback()
                    entry["new_items"] = 0
                    entry["status"] = "error"
                    entry["error"] = str(exc)[:300]
                report.append(entry)

        payload = {"new_items": total_new, "sources": report}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
