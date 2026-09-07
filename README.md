# Litmus

Submit a startup idea and get a real market and competitor analysis, built from
evidence gathered off the live web.

Built for **Orbit ISB 7.0** — Milestones 1 and 2.

| | |
|---|---|
| Live app | https://orbit-isb-7-0.vercel.app |
| API | https://orbit-isb-7-0-staging.onrender.com |
| API docs | https://orbit-isb-7-0-staging.onrender.com/docs |
| Architecture | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Licence | [LICENSE.txt](./LICENSE.txt) — MIT |

---

## Milestone 1 deliverables

| # | What was required | Where it is |
|---|---|---|
| 1 | System architecture — agents, data flow, structure | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| 2 | Idea submission interface — a founder submits an idea and sees results on the same page | [`frontend/`](./frontend) — `index.html`, `script.js`, `style.css` |
| 3 | Web Search Agent — Python, Tavily API, results returned to the frontend | [`backend/agents/web_search_agent.py`](./backend/agents/web_search_agent.py), exposed by [`backend/main.py`](./backend/main.py) |

## Milestone 2 deliverables

| # | What was required | Where it is |
|---|---|---|
| 1 | Market Opportunity & Customer Segmentation Agent | [`backend/agents/market_agent.py`](./backend/agents/market_agent.py) |
| 2 | Competitor Discovery & Comparison Agent | [`backend/agents/competitor_agent.py`](./backend/agents/competitor_agent.py) |
| 3 | Agent orchestration — all three agents, one request | [`backend/agents/pipeline.py`](./backend/agents/pipeline.py) |
| 4 | Tested on ideas from different industries | [`backend/test_runs/`](./backend/test_runs) |
| — | Performance and model measurements | [`backend/experiments/`](./backend/experiments) |

---

## What it does

A founder types their startup idea into a web page. Three agents run.

The **Web Search Agent** expands that one idea into three targeted search
queries, runs all three against the Tavily API at the same time, then merges,
ranks and de-duplicates the results.

The **Market Opportunity Agent** and the **Competitor Discovery Agent** then
read those results — at the same time as each other — and return structured
JSON: market size and growth, customer segments labelled buyer or supply,
a competitor comparison split into direct and indirect, and the gaps nobody is
serving.

Anything the sources did not support is labelled `Estimate (not from sources):`
and highlighted on the page, so a founder can tell evidence from inference at a
glance. If one agent fails the others still return, with a note saying which
part is missing.

A full run takes about six seconds.

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
| Analysis | Google Gemini (`gemini-3.7-flash`, free tier) |
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |

## Structure

```
backend/
  main.py                       FastAPI app, CORS, routes
  agents/
    web_search_agent.py         Milestone 1 - Tavily search
    market_agent.py             Milestone 2 - market and segments
    competitor_agent.py         Milestone 2 - competitors and gaps
    pipeline.py                 Milestone 2 - LangGraph orchestration
  test_runs/                    saved analyses, used as testing evidence
  experiments/                  the timing and model comparison scripts
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
`stats`, plus `market`, `competitors`, `errors` and `elapsed_seconds` — full
shape in
[ARCHITECTURE.md](./ARCHITECTURE.md#5-the-api-contract).

## Deployment

| | Setting |
|---|---|
| Render — Root Directory | `backend` |
| Render — Build Command | `pip install -r requirements.txt` |
| Render — Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Render — Environment | `TAVILY_API_KEY`, `GOOGLE_API_KEY` |
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
- [x] **Milestone 2** — market and competitor agents, connected pipeline, run concurrently
- [ ] Milestone 3 — synthesis agent and an overall validation score
