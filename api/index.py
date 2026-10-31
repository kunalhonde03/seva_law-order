"""Vercel Serverless Function entrypoint for SurakshaVani FastAPI application."""

import os
import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Signal to settings that we are in a serverless environment
os.environ["VERCEL"] = "1"

# Import ASGI application
from backend.app.main import app

