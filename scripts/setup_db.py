#!/usr/bin/env python3
"""Initialize the database."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from src.storage.database import init_db
init_db()
print("Database initialized.")
