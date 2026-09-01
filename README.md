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

## Milestone 1 deliverables

| # | What was required | Where it is |
|---|---|---|
| 1 | System architecture — agents, data flow, structure | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| 2 | Idea submission interface — a founder submits an idea and sees results on the same page | [`frontend/`](./frontend) — `index.html`, `script.js`, `style.css` |
| 3 | Web Search Agent — Python, Tavily API, results returned to the frontend | [`backend/agents/web_search_agent.py`](./backend/agents/web_search_agent.py), exposed by [`backend/main.py`](./backend/main.py) |

---

## What it does

A founder types their startup idea into a web page. The Web Search Agent
expands that one idea into three targeted search queries, runs all three
against the Tavily API at the same time, then merges, ranks and de-duplicates
the results.

They get back a summary of what the web says, the queries the agent generated,
sources grouped by the search that found them, and a report of the run itself -
searches made, duplicates collapsed, and how many distinct sites the evidence
came from.

Searching the founder's raw sentence returns general blog posts. Searching
these three angles returns evidence:

| Angle | Shown as | Finds |
|---|---|---|
| `{idea} competitors and similar startups` | Competitors | Who is already in this space |
| `{idea} market size and industry growth trends` | Market size & trends | Whether the opportunity is real |
| `existing solutions and customer complaints about {idea}` | Customer demand | Where the gap is |

The three searches run concurrently, in a thread pool with one worker each.
Measured on the same idea: 2.3 seconds one after another, 1.2 seconds all at
once. It is 2x rather than 3x because the request finishes when the slowest
search returns, not when the sum of all three does.

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

Returns `idea`, `queries`, `categories`, `counts`, `summary`, `results`,
`elapsed_seconds` and a `stats` block describing the run — full shape in
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
- [ ] Milestone 2 — Competitor and Market Sizing agents, run concurrently alongside this one
- [ ] Milestone 3 — synthesis agent and an overall validation score
