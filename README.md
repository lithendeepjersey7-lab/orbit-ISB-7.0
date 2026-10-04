# Litmus — AI Startup Idea Validator

Litmus is a multi-agent AI platform that helps founders validate startup
ideas using live web research and AI-powered business analysis.

A founder submits a startup idea, and Litmus runs a complete validation
pipeline covering market opportunity, competitors, SWOT and risks, MVP
recommendations, go-to-market strategy, and a downloadable validation report.

Built for **Orbit ISB 7.0 — Milestones 1 through 4.**

| | |
|---|---|
| Live app | https://orbit-isb-7-0.vercel.app |
| API | https://orbit-isb-7-0-staging.onrender.com |
| API docs | https://orbit-isb-7-0-staging.onrender.com/docs |
| Architecture | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Licence | [LICENSE.txt](./LICENSE.txt) — MIT |

---

## What Litmus does

A founder submits a startup idea through the web interface.

Litmus then processes the idea through a multi-agent validation pipeline:

```text
Startup Idea
     |
     v
Web Search Agent
     |
     +-------------------------+
     |                         |
     v                         v
Market Analysis        Competitor Analysis
     |                         |
     +------------+------------+
                  |
                  v
          SWOT & Risk Analysis
                  |
                  v
          MVP Recommendations
                  |
                  v
        Go-To-Market Strategy
                  |
                  v
       Validation Report
                  |
                  v
      Conversational Advisor

Each stage receives the relevant context from earlier stages. This allows
the system to move from web evidence to structured business analysis and
finally to actionable recommendations.

Features
Startup idea submission through a web interface
Live web research using the Tavily Search API
Market opportunity analysis
Customer segmentation
Competitor discovery and comparison
SWOT analysis and execution-risk identification
MVP feature recommendations
Go-to-market strategy generation
Downloadable HTML validation report
Context-grounded conversational startup advisor
Structured response validation for AI-generated outputs
Retry handling for transient Gemini service failures
End-to-end testing across five startup domains
Evidence and estimates are clearly distinguished in the interface
Validation pipeline
1. Web Search Agent

The Web Search Agent converts the submitted startup idea into targeted
research queries and retrieves evidence from the live web using Tavily.

The search covers three main areas:

Search angle	Purpose
{idea} competitors and similar startups	Identify existing players
{idea} market size and industry growth trends	Understand market opportunity
existing solutions and customer complaints about {idea}	Identify customer demand and potential gaps

The search results are merged, ranked, and de-duplicated before being passed
to the analysis agents.

2. Market Opportunity Agent

The Market Opportunity Agent analyses the retrieved evidence to identify:

Market opportunity
Market size information
Growth and demand
Relevant customer segments
Buyer and supply-side segments
3. Competitor Analysis Agent

The Competitor Analysis Agent identifies and compares:

Direct competitors
Indirect competitors
Existing solutions
Competitive gaps
4. SWOT & Risk Agent

The SWOT Agent uses the market and competitor context to generate:

Strengths
Weaknesses
Opportunities
Threats
Key execution risks
5. MVP Recommendation Agent

The MVP Agent recommends an initial product scope based on the validated
market opportunity and competitive context.

It focuses on the most important audience and features that should be
prioritized for an initial product.

6. Go-To-Market Agent

The GTM Agent generates a strategy covering areas such as:

Product positioning
Target audience
Acquisition channels
Early customer strategy
Initial go-to-market actions
7. Validation Report

The report generator combines the available validation results into a
structured, downloadable HTML report containing:

Startup idea and executive summary
Market analysis
Competitor analysis
SWOT and risks
MVP recommendations
Go-to-market strategy

Unavailable analysis sections are clearly marked rather than being filled
with invented information.

8. Conversational Startup Advisor

The Advisor allows follow-up questions about the completed validation.

It receives the startup idea and the existing validation context instead of
rerunning the complete validation pipeline for every question.

The advisor is designed to remain focused on the submitted startup idea and
its validation results.

Evidence and estimates

Litmus distinguishes between information supported by retrieved sources and
inferences made by the analysis agents.

When the available sources do not directly support a statement, it is marked
as:

Estimate (not from sources):

This helps the founder distinguish retrieved evidence from AI-generated
inference.

If an individual analysis stage fails, the pipeline records the failure
instead of inventing a replacement result. Other available stages can still
be returned.

Tech stack
Layer	Technology
Frontend	HTML, CSS, JavaScript
Frontend hosting	Vercel
Backend	Python, FastAPI, Uvicorn
Backend hosting	Render
Web search	Tavily Search API
AI analysis	Google Gemini (gemini-3.7-flash)
Orchestration	LangGraph
Report generation	Python-generated self-contained HTML
Project structure
backend/
  main.py                       FastAPI application, CORS and API routes
  report_generator.py           Downloadable HTML validation report
  e2e_test_runner.py            Offline five-domain E2E test runner

  agents/
    web_search_agent.py         Tavily web search
    market_agent.py             Market opportunity and customer segments
    competitor_agent.py         Competitor discovery and comparison
    swot_agent.py               SWOT and execution-risk analysis
    mvp_agent.py                MVP feature recommendations
    gtm_agent.py                Go-to-market strategy
    advisor_agent.py            Context-grounded follow-up advisor
    gemini_retry.py             Retry handling for transient Gemini failures
    response_validation.py      AI response schema/type validation
    pipeline.py                 Validation pipeline orchestration

  test_runs/                    Saved testing evidence
  experiments/                  Timing and model comparison scripts
  requirements.txt
  .env.example                  Environment variable template

frontend/
  index.html                    Startup idea submission interface
  script.js                     API calls and result rendering
  style.css                     Frontend styling

ARCHITECTURE.md                 System architecture and API contract
FINAL_DEMO.md                   Final demonstration guide
render.yaml                     Render deployment configuration
LICENSE.txt                     MIT licence
Running locally
Requirements
Python 3.11 or newer
Node.js is not required for the static frontend
Tavily API key
Google Gemini API key

The API keys must be stored in environment variables and should never be
committed to Git.

Backend

From the repository root:

cd backend
python -m venv .venv

Activate the virtual environment.

Windows PowerShell:

.\.venv\Scripts\Activate.ps1

Linux/macOS:

source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create the environment file:

cp .env.example .env

On Windows, the .env.example file can also be copied manually.

Add the required API keys to .env:

TAVILY_API_KEY=your_tavily_key
GOOGLE_API_KEY=your_google_key

Start the backend:

uvicorn main:app --reload

The backend runs at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs
Frontend

Open a second terminal from the repository root and run:

cd frontend
python -m http.server 5500

Then open:

http://127.0.0.1:5500

The frontend communicates with the local backend when running locally.

API
Method	Endpoint	Purpose
GET	/	Returns service information and confirms that the API is running
POST	/validate	Runs startup idea validation
POST	/advisor	Answers a follow-up question using validation context
POST	/report	Generates and downloads the validation report
Validate

Example request:

{
  "idea": "An app that helps students split rent with roommates"
}

The /validate response contains the startup idea, search evidence,
market analysis, competitor analysis, SWOT, MVP, GTM results, errors, and
execution timing.

Unavailable analysis sections can be returned as null, with the relevant
failure recorded in the errors field.

Advisor

The /advisor endpoint receives:

Startup idea
Follow-up question
Market analysis
Competitor analysis
SWOT analysis
MVP recommendations
GTM strategy

The endpoint is stateless, so the relevant validation context is included
with each request.

Report

The /report endpoint accepts the validation response and returns a
downloadable HTML report.

The report can be generated from the validation results without rerunning the
entire validation pipeline.

Testing
Offline end-to-end testing

Run the E2E test runner from the repository root:

python backend/e2e_test_runner.py

The runner covers five startup domains:

Domain	Example
SaaS	AI-powered inventory management
Consumer	Smart meal planning
Hardware	Smart water monitoring
Marketplace	Local photographer marketplace
EdTech	Adaptive learning platform

The offline runner replaces external Tavily and Gemini calls with explicitly
marked fixtures.

Therefore, the test does not require API credentials or network access.

It verifies:

Pipeline orchestration
Agent integration
Expected response structures
Error handling
Retry behaviour
Advisor behaviour
Report generation

The offline test is an integration/contract test and is not a live AI
quality benchmark. It does not prove the factual accuracy or usefulness of
live Gemini-generated analysis.

AI response validation

The Gemini-backed agents validate required response fields and expected data
types.

Malformed, incomplete, or incorrectly typed responses are rejected instead of
being passed blindly to later stages.

Transient Gemini failures

Transient Gemini service failures such as 503 UNAVAILABLE are handled with
bounded retry attempts.

Non-retryable failures such as authentication, invalid requests, or quota
errors are not repeatedly retried.

Deployment
Render
Setting	Value
Root Directory	backend
Build Command	pip install -r requirements.txt
Start Command	uvicorn main:app --host 0.0.0.0 --port $PORT
Required environment variables	TAVILY_API_KEY, GOOGLE_API_KEY
Vercel
Setting	Value
Root Directory	frontend
Framework Preset	Other
Build step	None

Deployment configuration is also available in:

render.yaml

The real API keys are stored in deployment environment settings and are not
committed to the repository.

The backend uses Render's free tier and may sleep after a period of
inactivity. The first request after the service wakes can therefore take
longer than normal.

Milestone status

The project has progressed through all four internship milestones.

 Milestone 1 — System architecture, idea submission interface and Web Search Agent
 Milestone 2 — Market Opportunity and Competitor Analysis with pipeline orchestration
 Milestone 3 — SWOT and Risk Analysis, MVP Recommendations, GTM Strategy and Conversational Advisor
 Milestone 4 — Downloadable Validation Report, five-domain E2E testing, response validation, prompt/query refinement and technical documentation
Known limitations
Live analysis depends on the availability and limits of the Tavily and
Gemini APIs.
Gemini quota or service availability can prevent live AI analysis from
completing.
The offline E2E runner uses fixtures and therefore cannot evaluate live
market-data accuracy or the factual quality of Gemini responses.
AI-generated business analysis should be treated as decision support and
should be independently verified before making significant business or
financial decisions.
The validation pipeline does not currently produce an overall numeric
validation score.
The Advisor uses the supplied validation context and does not maintain
persistent conversation history between independent API requests.
