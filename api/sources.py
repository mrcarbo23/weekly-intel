"""Vercel serverless function: manage sources."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import init_db, get_db
from src.storage.models import Source


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        init_db()
        with get_db() as db:
            sources = db.query(Source).all()
            data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "source_type": s.source_type,
                    "url": s.url,
                    "active": s.active,
                    "last_fetched_at": s.last_fetched_at.isoformat() if s.last_fetched_at else None,
                }
                for s in sources
            ]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        init_db()
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        with get_db() as db:
            source = Source(
                name=body["name"],
                source_type=body["source_type"],
                url=body.get("url"),
                config=body.get("config"),
                active=body.get("active", True),
            )
            db.add(source)
            db.commit()
            result = {"id": source.id, "name": source.name}

        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_DELETE(self):
        init_db()

        # Accept the id from ?id=<n> or a JSON body {"id": <n>}.
        source_id = None
        params = parse_qs(urlparse(self.path).query)
        if params.get("id"):
            source_id = params["id"][0]
        else:
            length = int(self.headers.get("Content-Length", 0))
            if length:
                source_id = json.loads(self.rfile.read(length)).get("id")

        try:
            source_id = int(source_id)
        except (TypeError, ValueError):
            return self._respond(400, {"error": "missing or invalid source id"})

        with get_db() as db:
            source = db.get(Source, source_id)
            if source is None:
                return self._respond(404, {"error": f"source {source_id} not found"})
            db.delete(source)
            db.commit()

        self._respond(200, {"deleted": source_id})

    def _respond(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())
