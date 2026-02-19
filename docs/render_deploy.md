# Render Deployment Notes

This project is a Python Flask web app (frontend + API in one service).

Use these Render settings for a Web Service:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn Main:app --bind 0.0.0.0:$PORT`

Required environment variables:

- `SECRET_KEY`: random strong string
- `DATABASE_URL`: PostgreSQL connection URL

Quick checks in Render logs:

- Confirm build installs `gunicorn` from `requirements.txt`.
- Confirm start command runs `gunicorn Main:app --bind 0.0.0.0:$PORT`.
- Confirm no import error like `No module named Main`.
- If app starts but routes fail, check `DATABASE_URL` value (missing/invalid DB URL causes DB access errors).
