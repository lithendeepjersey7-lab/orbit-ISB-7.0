# Litmus - AI Startup Idea Validator

Litmus is a multi-agent AI platform that helps founders validate startup ideas using AI-powered business analysis and live web research.

A user submits a startup idea, and Litmus analyzes the opportunity across the market, competitors, SWOT, MVP, and go-to-market strategy. The results can be downloaded as a validation report or explored through a conversational AI advisor.

**Built for Orbit ISB 7.0 - Milestones 1 through 4.**

## Live Project

- **Live Application:** https://orbit-isb-7-0.vercel.app
- **Backend API:** https://orbit-isb-7-0-staging.onrender.com
- **API Documentation:** https://orbit-isb-7-0-staging.onrender.com/docs

## How It Works

```text
Startup Idea
     |
     v
Web Search
     |
     +---------------------+
     |                     |
     v                     v
Market Analysis      Competitor Analysis
     |                     |
     +----------+----------+
                |
                v
          SWOT & Risks
                |
                v
       MVP Recommendations
                |
                v
      Go-To-Market Strategy
                |
        +-------+-------+
        |               |
        v               v
   Validation       AI Advisor
     Report
Key Features
Market Research

Uses the Tavily Search API to gather relevant information from the live web.

Market & Customer Analysis

Analyzes market opportunities, demand, and relevant customer segments.

Competitor Analysis

Identifies competitors, existing solutions, and potential market gaps.

SWOT & Risk Analysis

Generates strengths, weaknesses, opportunities, threats, and key execution risks.

MVP Recommendations

Recommends the most important product features and initial MVP scope.

Go-To-Market Strategy

Provides recommendations for positioning, target users, acquisition channels, and early market entry.

Validation Report

Generates a downloadable HTML report containing the startup validation results.

Conversational AI Advisor

Allows users to ask follow-up questions about their validation results without rerunning the complete validation pipeline.

Validation Pipeline
Stage	Purpose
Web Search	Gather relevant live web evidence
Market Analysis	Analyze market opportunity and customers
Competitor Analysis	Identify and compare competitors
SWOT & Risk	Identify strengths, weaknesses, opportunities, threats, and risks
MVP	Recommend initial product features
Go-To-Market	Develop an initial market entry strategy
Validation Report	Present the complete validation results
AI Advisor	Answer follow-up questions using the validation context
Technology Stack
Component	Technology
Frontend	HTML, CSS, JavaScript
Backend	Python, FastAPI, Uvicorn
AI	Google Gemini
Web Search	Tavily Search API
Orchestration	LangGraph
Frontend Hosting	Vercel
Backend Hosting	Render
Project Structure
orbit-ISB-7.0/
|
+-- backend/
|   +-- main.py
|   +-- report_generator.py
|   +-- e2e_test_runner.py
|   |
|   +-- agents/
|       +-- web_search_agent.py
|       +-- market_agent.py
|       +-- competitor_agent.py
|       +-- swot_agent.py
|       +-- mvp_agent.py
|       +-- gtm_agent.py
|       +-- advisor_agent.py
|       +-- gemini_retry.py
|       +-- response_validation.py
|       +-- pipeline.py
|
+-- frontend/
|   +-- index.html
|   +-- script.js
|   +-- style.css
|
+-- ARCHITECTURE.md
+-- FINAL_DEMO.md
+-- render.yaml
+-- requirements.txt
+-- LICENSE.txt
API Endpoints
Method	Endpoint	Purpose
GET	/	API health and project information
POST	/validate	Validate a startup idea
POST	/advisor	Ask a follow-up question
POST	/report	Generate the validation report

Interactive API documentation:

https://orbit-isb-7-0-staging.onrender.com/docs

Testing

Litmus includes an offline end-to-end test runner covering five startup domains:

SaaS
Consumer
Hardware
Marketplace
EdTech

Run the tests with:

python backend/e2e_test_runner.py

The offline test suite uses synthetic fixtures instead of live Tavily and Gemini requests.

It verifies:

Agent integration
Pipeline orchestration
Response validation
Error handling
Retry behaviour
Advisor behaviour
Report generation

Offline tests verify application integration and response contracts. They do not measure the factual quality of live AI-generated analysis.

Reliability

Litmus validates AI-generated responses before passing them to later stages.

Transient Gemini service failures such as 503 UNAVAILABLE are handled using bounded retry attempts.

Non-retryable failures, such as invalid requests, authentication failures, or quota errors, are reported instead of being repeatedly retried.

Milestone Progress
Milestone	Work Completed	Status
M1	Idea submission, system architecture, and Web Search Agent	Complete
M2	Market Analysis, Competitor Analysis, and pipeline orchestration	Complete
M3	SWOT, MVP Recommendations, GTM Strategy, and Conversational Advisor	Complete
M4	Validation Report, E2E Testing, optimization, and documentation	Complete
Important Notes
Live validation depends on the availability and usage limits of the Gemini and Tavily APIs.
API quotas or temporary service availability can affect live validation.
AI-generated analysis should be independently verified before making important business decisions.
Litmus currently does not generate an overall numeric validation score.
License

This project is licensed under the MIT License.

See LICENSE.txt for details.


This is the version I would use for the **main repository**: professional, readable, and detailed enough f
