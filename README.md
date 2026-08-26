# AI Startup Idea Validator

Submit a startup idea and get real market and competitor evidence from the web.

Built for Orbit ISB 7.0 — Milestone 1.

## Structure

```
backend/    FastAPI service and the web search agent
frontend/   HTML, CSS and JavaScript interface
```

## Running it locally

**Backend**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Runs at http://127.0.0.1:8000 — API docs at http://127.0.0.1:8000/docs

You need a Tavily API key in `backend/.env`:

```
TAVILY_API_KEY=tvly-your-key-here
```

**Frontend**

Open `frontend/index.html` in your browser.

## Deployment

Backend on Render (root directory `backend`), frontend on Vercel
(root directory `frontend`).

## Branches

`staging` for development, `main` for production.
