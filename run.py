"""
Development:  python run.py
Production:   gunicorn --bind 0.0.0.0:8000 --workers 2 run:app
"""
import uvicorn
from app.main import app  # noqa: F401 — needed for gunicorn import

if __name__ == "__main__":
    from config import PORT
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,       # auto-reload on file change in dev
        log_level="info",
    )
