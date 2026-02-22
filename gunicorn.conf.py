import os


# Resolve the Render-provided port in Python to avoid shell expansion issues.
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Keep a single sync worker for the current free-tier footprint.
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
worker_class = "sync"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
