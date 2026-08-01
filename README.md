# Brisk Hack AI — Full Stack MVP

## Run locally (Windows)

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs

## Render deployment
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

SQLite is used for the MVP. For production, replace it with PostgreSQL and move `SECRET_KEY` into an environment variable.
