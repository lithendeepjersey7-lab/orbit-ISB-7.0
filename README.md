# AI Startup Idea Validator

Submit a startup idea and get real market and competitor evidence gathered from
the live web.

Built for **Orbit ISB 7.0** — Milestone 1.

| | |
|---|---|
| Live app | https://orbit-isb-7-0.vercel.app |
| API | https://orbit-isb-7-0-staging.onrender.com |
| API docs | https://orbit-isb-7-0-staging.onrender.com/docs |
| Architecture | [ARCHITECTURE.md](./ARCHITECTURE.md) |

---

## What it does

A founder types their startup idea into a web page. The Web Search Agent
expands that one idea into three targeted search queries, runs each against the
Tavily API, then merges, ranks and de-duplicates the results.

They get back a summary of what the web says, the queries the agent generated,
and a list of real sources they can click through to.

Searching the founder's raw sentence returns general blog posts. Searching
these three angles returns evidence:

| Angle | Finds |
|---|---|
| `{idea} competitors and similar startups` | Who is already in this space |
| `{idea} market size and industry growth trends` | Whether the opportunity is real |
| `existing solutions and customer complaints about {idea}` | Where the gap is |

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | HTML, CSS, JavaScript — deployed on Vercel |
| Backend | Python, FastAPI, Uvicorn — deployed on Render |
| Web search | [Tavily](https://tavily.com) Search API |

## Structure

```
backend/
  main.py                       FastAPI app, CORS, routes
  agents/
    web_search_agent.py         the Web Search Agent
  requirements.txt
  .env.example                  template - real .env is git-ignored

frontend/
  index.html                    the idea submission form
  script.js                     calls the API, renders results
  style.css

ARCHITECTURE.md                 agents, data flow, API contract
render.yaml                     Render deployment settings
```

## Running it locally

You need Python 3.11 or newer and a Tavily API key
([free tier](https://app.tavily.com), no card required).

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env             # then add your real key to .env
uvicorn main:app --reload
```

Runs at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs

**Frontend**

Change `API_URL` at the top of `frontend/script.js` to
`http://127.0.0.1:8000`, then open `frontend/index.html` in a browser.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Service info — used to check the API is up |
| `POST` | `/validate` | Takes `{"idea": "..."}`, returns ranked web evidence |

Example:

```bash
curl -X POST https://orbit-isb-7-0-staging.onrender.com/validate \
  -H "Content-Type: application/json" \
  -d '{"idea":"an app that helps students split rent with roommates"}'
```

Returns `idea`, `queries`, `summary` and `results` — full shape in
[ARCHITECTURE.md](./ARCHITECTURE.md#5-the-api-contract).

## Deployment

| | Setting |
|---|---|
| Render — Root Directory | `backend` |
| Render — Build Command | `pip install -r requirements.txt` |
| Render — Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Render — Environment | `TAVILY_API_KEY` |
| Vercel — Root Directory | `frontend` |
| Vercel — Framework Preset | Other (static files, no build step) |

These are also recorded in [`render.yaml`](./render.yaml).

> The backend runs on Render's free tier, which sleeps after 15 minutes of
> inactivity. The first request after a sleep takes around 50 seconds.

## Branches

`staging` for development, `main` for production. Both hosts deploy
automatically on push.

## Milestone status

- [x] **Milestone 1** — system architecture, idea submission interface, Web Search Agent
- [ ] Milestone 2 — Competitor and Market Sizing agents, running concurrently
- [ ] Milestone 3 — synthesis agent and an overall validation score
