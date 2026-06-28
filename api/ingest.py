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
        with get_db() as db:
            sources = db.query(Source).filter(Source.active == True).all()
            for source in sources:
                total_new += ingest_source(db, source)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"new_items": total_new}).encode())
