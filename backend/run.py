"""
Production entry point for the FastAPI backend.

Binds Uvicorn to 0.0.0.0 and the host-provided PORT (Render, Railway,
Fly.io, Heroku, etc.). Falls back to port 8000 for local use.

Run with:
    python run.py
"""

import os

import uvicorn

DEFAULT_PORT = 8000


def get_port() -> int:
    """Return the configured port, falling back to DEFAULT_PORT."""
    raw = os.environ.get("PORT", "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        return DEFAULT_PORT
    if not 1 <= port <= 65535:
        return DEFAULT_PORT
    return port


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=get_port(),
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
