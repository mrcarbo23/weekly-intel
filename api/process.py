"""Vercel serverless function: run LLM processing."""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        from src.storage.database import init_db, get_db
        from scripts.run_pipeline import process_items
        init_db()

        with get_db() as db:
            count = process_items(db)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"processed": count}).encode())
