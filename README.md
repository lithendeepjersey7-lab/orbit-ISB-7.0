# Litmus

Submit a startup idea and get a structured startup validation built from live
web evidence, followed by SWOT, MVP, and go-to-market recommendations. The
result can be downloaded as an HTML report.

Built for **Orbit ISB 7.0** — Milestones 1 through 4.

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

## Milestone 3 deliverables

| Deliverable | Implementation |
|---|---|
| SWOT and execution-risk analysis | [`backend/agents/swot_agent.py`](./backend/agents/swot_agent.py) |
| MVP feature recommendations | [`backend/agents/mvp_agent.py`](./backend/agents/mvp_agent.py) |
| Go-to-market strategy | [`backend/agents/gtm_agent.py`](./backend/agents/gtm_agent.py) |
| Context-grounded follow-up advisor | [`backend/agents/advisor_agent.py`](./backend/agents/advisor_agent.py), exposed at `POST /advisor` |
| Pipeline integration | [`backend/agents/pipeline.py`](./backend/agents/pipeline.py) |

## Milestone 4 deliverables

| Deliverable | Implementation |
|---|---|
| Downloadable validation report | [`backend/report_generator.py`](./backend/report_generator.py), exposed at `POST /report` |
| Five-domain offline end-to-end runner | [`backend/e2e_test_runner.py`](./backend/e2e_test_runner.py) |
| Agent response schema checks | [`backend/agents/response_validation.py`](./backend/agents/response_validation.py) |
| Final demonstration steps | [`FINAL_DEMO.md`](./FINAL_DEMO.md) |

---

## What it does

A founder submits a startup idea through the web page. The pipeline gathers web
evidence, runs market and competitor analysis concurrently, then runs SWOT,
MVP, and go-to-market analysis in sequence.

The **Web Search Agent** expands that one idea into three targeted search
queries, runs all three against the Tavily API at the same time, then merges,
ranks and de-duplicates the results.

The **Market Opportunity Agent** and the **Competitor Discovery Agent** then
read those results — at the same time as each other — and return structured
JSON: market size and growth, customer segments labelled buyer or supply,
a competitor comparison split into direct and indirect, and the gaps nobody is
serving.

After both analyses complete, the pipeline runs SWOT and execution-risk
analysis, recommends an MVP audience and feature set, then creates a GTM
strategy. Each stage's output is returned in its own field. The **Advisor** can
answer a follow-up using a supplied validation result, but currently is
available through the API only, not a frontend question form.

Anything the sources did not support is labelled `Estimate (not from sources):`
and highlighted on the page, so a founder can tell evidence from inference at a
glance. If one agent fails the others still return, with a note saying which
part is missing.

The frontend currently displays the market and competitor sections directly.
SWOT, MVP, and GTM are included in the API response and downloadable report.
The Advisor endpoint is API-only; the current frontend has no follow-up
question form.

The HTML report contains the startup idea/executive summary, market analysis,
competitor analysis, SWOT and risks, MVP recommendations, and GTM strategy.
Unavailable analysis sections are labelled instead of being filled with
invented content. End-to-end fixture runtimes are not representative of live
API latency.

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
| Report | Python-generated, self-contained HTML |

## Structure

```
backend/
  main.py                       FastAPI app, CORS, routes
  report_generator.py           HTML validation report builder
  e2e_test_runner.py             offline five-domain integration runner
  agents/
    web_search_agent.py         Milestone 1 - Tavily search
    market_agent.py             Milestone 2 - market and segments
    competitor_agent.py         Milestone 2 - competitors and gaps
    swot_agent.py               Milestone 3 - SWOT and execution risks
    mvp_agent.py                Milestone 3 - MVP recommendations
    gtm_agent.py                Milestone 3 - go-to-market strategy
    advisor_agent.py            Milestone 3 - follow-up answers
    response_validation.py      required JSON shape/type validation
    pipeline.py                 LangGraph validation orchestration
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

cp .env.example .env             # add TAVILY_API_KEY and GOOGLE_API_KEY
uvicorn main:app --reload
```

Runs at http://127.0.0.1:8000 — interactive docs at http://127.0.0.1:8000/docs

**Frontend**

In a second terminal, serve the static frontend:

```bash
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500. The frontend selects the local API automatically
for localhost; no source edit is needed.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Service info — used to check the API is up |
| `POST` | `/validate` | Takes `{"idea": "..."}`, returns search evidence and available analyses |
| `POST` | `/advisor` | Takes a follow-up question and validation context; returns a structured answer |
| `POST` | `/report` | Takes a complete validation response and returns a downloadable HTML attachment |

Example:

```bash
curl -X POST https://orbit-isb-7-0-staging.onrender.com/validate \
  -H "Content-Type: application/json" \
  -d '{"idea":"an app that helps students split rent with roommates"}'
```

The `/validate` response includes `idea`, search fields (`queries`,
`categories`, `counts`, `summary`, `results`, and `stats`), `market`,
`competitors`, `swot`, `mvp`, `gtm`, `errors`, and `elapsed_seconds`. An
unavailable analysis may be `null`; `errors` records pipeline failures.

`POST /advisor` expects `question`, `idea`, and the `market`, `competitors`,
`swot`, `mvp`, and `gtm` values from a validation response. It returns
`answer`, `has_sufficient_context`, and `missing_context`. The endpoint is
stateless, so include the context in each request. The current frontend does
not provide an Advisor interaction.

`POST /report` accepts the full validation response as its JSON body. The
browser's **Download validation report** button sends it and downloads the
returned HTML file. Interactive request schemas are available at
http://127.0.0.1:8000/docs when the backend is running.

## Offline end-to-end test

From the repository root, run:

```bash
python backend/e2e_test_runner.py
```

The runner exercises the pipeline and report endpoint for SaaS, Consumer,
Hardware, Marketplace, and EdTech ideas. Search and the Gemini-backed agents
are replaced with explicitly marked fixtures, so no API credentials or
network access are needed. This verifies orchestration, expected response
shapes, and report generation only. It is **not a live AI-quality benchmark**
and does not validate the factual accuracy or usefulness of generated analysis.

The Gemini-backed agents check required JSON fields and nested data types.
Malformed, incomplete, or incorrectly typed responses are rejected as
unusable, allowing the pipeline to report partial failures instead of passing
malformed output to later stages. The agents do not currently retry or repair
rejected model output.

## Deployment

| | Setting |
|---|---|
| Render — Root Directory | `backend` |
| Render — Build Command | `pip install -r requirements.txt` |
| Render — Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Render — Required environment | `TAVILY_API_KEY`, `GOOGLE_API_KEY` (configure both in the Render environment settings) |
| Vercel — Root Directory | `frontend` |
| Vercel — Framework Preset | Other (static files, no build step) |

The Render service settings and Tavily secret declaration are in
[`render.yaml`](./render.yaml). Add `GOOGLE_API_KEY` separately in Render's
environment settings; it is not declared in the checked-in YAML. The local
[`backend/.env.example`](./backend/.env.example) is a template and also needs
the real Google key added to the copied `.env` file.

> The backend runs on Render's free tier, which sleeps after 15 minutes of
> inactivity. The first request after a sleep takes around 50 seconds.

## Branches

`staging` for development, `main` for production. Both hosts deploy
automatically on push.

## Milestone status

- [x] **Milestone 1** — system architecture, idea submission interface, Web Search Agent
- [x] **Milestone 2** — market and competitor agents, connected pipeline, run concurrently
- [x] **Milestone 3** — SWOT, MVP, GTM, and Advisor API capability
- [x] **Milestone 4** — downloadable report, five-idea offline E2E runner, response validation, documentation and demo guide

No overall numeric validation score is currently returned. The five-idea E2E
runner uses offline fixtures; live analysis quality has not been certified by
that test.
