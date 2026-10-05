# Litmus — AI Startup Idea Validator

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Litmus is a multi-agent AI platform that helps founders validate startup ideas using AI-powered business analysis and web research.

A submitted startup idea is analyzed across:

- Market Analysis
- Competitor Analysis
- SWOT & Risks
- MVP Recommendations
- Go-To-Market Strategy

The results can be downloaded as a PDF validation report or explored through a conversational AI advisor with report and live-search citations.

| Resource | Link |
|----------|------|
| Live Application | [https://orbit-isb-7-0.vercel.app](https://orbit-isb-7-0.vercel.app) |
| Backend Staging API | [https://orbit-isb-7-0-staging.onrender.com](https://orbit-isb-7-0-staging.onrender.com) |
| Interactive API Documentation | [https://orbit-isb-7-0-staging.onrender.com/docs](https://orbit-isb-7-0-staging.onrender.com/docs) |

> **Project Notice:** Built for Orbit ISB 7.0. Milestones 1 through 4 are complete.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | HTML5, CSS3, Vanilla JavaScript | Static user interface hosted via Vercel |
| Backend | Python, FastAPI, Uvicorn | REST API hosted via Render |
| AI Model | Google Gemini (`gemini-3.7-flash`) | Language model used for analysis |
| AI Integration | LangChain Google GenAI (v4.4.0) | Interface for model interactions |
| Orchestration | LangGraph | Manages the multi-agent pipeline |
| Web Research | Tavily Search API | Web search for gathering supporting evidence |
| PDF Reports | ReportLab | Builds the downloadable validation report |
| Configuration | python-dotenv | Environment variable management |
| Validation | Custom response validation | Structural validation of agent outputs |

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

## How It Works

```text
Startup Idea
     ↓
Web Search
     ↓
Market Analysis + Competitor Analysis
     ↓
SWOT & Risks
     ↓
MVP Recommendations
     ↓
Go-To-Market Strategy
     ↓
Validation Context
     ├── Downloadable PDF Validation Report
     └── Conversational AI Advisor
```

### Pipeline Stages

| Stage | Description |
|-------|-------------|
| Web Search | Uses the Tavily Search API to gather relevant web-search evidence. |
| Market Analysis | Analyzes market opportunities, demand, and relevant customer segments. |
| Competitor Analysis | Identifies competitors, existing solutions, and potential market gaps. |
| SWOT & Risks | Returns structured risks with category, likelihood, impact, and mitigation alongside SWOT findings. |
| MVP Recommendations | Groups Must/Should/Nice-to-have features and orders phased build priorities. |
| Go-To-Market Strategy | Provides positioning, target users, channels, first-100-user plan, monetization hypothesis, and a 90-day roadmap. |
| Validation Report | Generates a PDF with the analysis, evidence sources, roadmap, and an explicitly labeled evidence-coverage score. |
| Conversational AI Advisor | Answers follow-ups from report/live-search context, keeps recent in-session history, and returns validated citations. |

The advisor does not rerun the validation pipeline. The frontend supplies the validation context and recent conversation history with each request. Citations are restricted to report sections and source URLs included in that request.

---

## Project Structure

```text
orbit-ISB-7.0/
├── backend/
│   ├── main.py                  # API entrypoint and app configuration
│   ├── report_generator.py      # PDF validation report generation
│   ├── e2e_test_runner.py       # Offline end-to-end test runner
│   └── agents/
│       ├── web_search_agent.py      # Tavily Search API integration
│       ├── market_agent.py          # Market analysis
│       ├── competitor_agent.py      # Competitor analysis
│       ├── swot_agent.py            # SWOT & risks
│       ├── mvp_agent.py             # MVP recommendations
│       ├── gtm_agent.py             # Go-to-market strategy
│       ├── advisor_agent.py         # Context-aware follow-up advisor
│       ├── gemini_retry.py          # Bounded retry handling for transient Gemini failures
│       ├── response_validation.py   # Shared JSON structure validation
│       └── pipeline.py              # LangGraph validation pipeline orchestration
├── frontend/
│   ├── index.html               # User interface
│   ├── script.js                # Client logic and local/remote API selection
│   └── style.css                # Styling
├── ARCHITECTURE.md              # Technical design documentation
├── render.yaml                  # Render deployment configuration
├── requirements.txt             # Python project dependencies
└── LICENSE.txt                  # MIT License
```

---

## Local Installation

### Prerequisites

- Python 3.11+
- pip

Node.js and npm are **not** required.

### Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open the `.env` file and add your API keys:

```env
TAVILY_API_KEY=your_tavily_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
```

Start the backend:

```powershell
uvicorn main:app --reload
```

- Local backend: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs

### Frontend Setup

In a second terminal, serve the static frontend with Python's built-in server:

```powershell
cd frontend
python -m http.server 5500
```

- Local frontend: http://127.0.0.1:5500

The frontend automatically selects the local backend when running on localhost.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Service health and project information |
| POST | `/validate` | Runs the complete startup validation pipeline |
| POST | `/advisor` | Answers follow-up questions using the supplied validation context |
| POST | `/report` | Generates the downloadable PDF validation report |

---

## Testing

Run the offline end-to-end test runner:

```powershell
python backend/e2e_test_runner.py
```

The tests cover five startup domains:

- SaaS
- Consumer
- Hardware
- Marketplace
- EdTech

The tests use synthetic/offline fixtures and do **not** call live Gemini or Tavily APIs. They verify:

- Application integration
- Pipeline orchestration
- Response validation
- Error handling
- Retry behavior
- Advisor behavior
- PDF report sections, media type, and download headers

These tests verify technical integration and response contracts. They do not measure the factual quality or real-world usefulness of live AI-generated business analysis.

---

## Reliability & Error Handling

- **Transient failures:** Bounded retry handling (`gemini_retry.py`) is used for temporary Gemini service disruptions such as `503 UNAVAILABLE`. Retries are limited and intended only for temporary issues.
- **Non-retryable failures:** Authentication errors, invalid requests, and quota errors are not repeatedly retried.

---

## Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M1 | Idea Submission, Architecture, Web Search | Complete |
| M2 | Market Analysis, Competitor Analysis, Orchestration | Complete |
| M3 | SWOT, MVP, GTM, Conversational Advisor | Complete |
| M4 | Validation Report, E2E Testing, Optimization, Documentation | Complete |

---

## Important Notes

- Live analysis depends on Gemini and Tavily API availability and usage limits.
- Temporary upstream service failures or quota limits can affect live validation.
- AI-generated business analysis should be independently reviewed before important business decisions.
- The PDF's 0–100 score measures evidence-section coverage only; it is not a startup viability or investment score.

---

## License

Licensed under the MIT License. See `LICENSE.txt` for details.
