# Render Deployment Notes

This project is a Python Flask web app (frontend + API in one service).

Use these Render settings for a Web Service:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn Main:app -c gunicorn.conf.py`
- Health Check Path: `/healthz`

Required environment variables:

- `SECRET_KEY`: random strong string
- `DATABASE_URL`: PostgreSQL connection URL

Quick checks in Render logs:

- Confirm build installs `gunicorn` from `requirements.txt`.
- Confirm start command runs `gunicorn Main:app -c gunicorn.conf.py`.
- Confirm no import error like `No module named Main`.
- If app starts but routes fail, check `DATABASE_URL` value (missing/invalid DB URL causes DB access errors).

If Render shows `No open HTTP ports detected`:

- Verify the service type is `Web Service` (not `Background Worker`).
- Recheck Start Command exactly matches `gunicorn Main:app -c gunicorn.conf.py`.
- Ensure `/healthz` returns `200`.
