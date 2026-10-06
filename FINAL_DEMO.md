# Litmus Final Demo

A practical 3–5 minute walkthrough of the current Milestone 1–4 implementation.

## Before the demo

For a live validation, configure `TAVILY_API_KEY` and `GOOGLE_API_KEY` in
`backend/.env`. Start the backend and frontend in separate terminals:

```powershell
cd backend
..\.venv-1\Scripts\Activate.ps1
uvicorn main:app --reload
```

```powershell
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500. The frontend uses the hosted staging API by default.
To use the local API instead, open
http://127.0.0.1:5500/?api=local. The full live flow requires valid API
credentials and network access. Do not present offline fixtures as live
analysis.

## Demo flow

| Time | What to click/type | What should appear | Feature demonstrated |
|---|---|---|---|
| 0:00–0:30 | Start the backend and static frontend using the commands above; open `http://127.0.0.1:5500`. | Litmus idea form appears. The backend can also be checked at `http://127.0.0.1:8000/docs`. | Local application startup and API availability. |
| 0:30–0:50 | Enter `An app that helps independent grocery stores predict stock needs and reduce expired inventory` and click **Validate idea**. | Status text progresses while the request runs; the response includes search evidence and available analysis fields. | Idea submission and the full validation request. |
| 0:50–1:30 | In the page, scroll through **Market opportunity** and **Competitor landscape**. | Market summary, segments, evidence gaps, competitor comparison, and market gaps appear when returned. | Web evidence synthesized into Market and Competitor analysis. |
| 1:30–2:10 | Open browser developer tools, select **Network**, select the `/validate` request, and inspect its JSON **Response**. Expand `swot`. | `strengths`, `weaknesses`, `opportunities`, `threats`, and `execution_risks` appear if the SWOT stage succeeded. The UI does not currently render this section inline. | SWOT synthesis and risk output in the API result. |
| 2:10–2:40 | In the same `/validate` JSON response, expand `mvp`. | Target audience, product summary, must-have features, and nice-to-have features appear if the MVP stage succeeded. | MVP recommendation output. |
| 2:40–3:05 | In the same response, expand `gtm`. | Positioning, target customers, acquisition channels, and first-90-day actions appear if GTM succeeded. | Go-to-market strategy output. |
| 3:05–3:35 | Return to the page and click **Download validation report**. Open the downloaded `.html` file. | A standalone report appears with six headings: Executive Summary, Market, Competitor, SWOT & Risks, MVP, and GTM. Missing results are labelled as unavailable. | Report generation from the actual `/validate` payload and browser download. |
| 3:35–4:00 | Optionally show the Advisor API docs at `http://127.0.0.1:8000/docs`, expand `POST /advisor`, and submit a question with the idea and the five analysis objects from the validation response. | A structured answer with `answer`, `has_sufficient_context`, and `missing_context` is returned. If context is insufficient, the response is expected to say so. | Context-grounded follow-up Advisor API. There is no Advisor form in the current frontend. |
| 4:00–4:35 | In a terminal at the repository root, run `python backend/e2e_test_runner.py`. | A five-domain table reports Search, Market, Competitor, SWOT, MVP, GTM, and Report contract results. | Repeatable SaaS, Consumer, Hardware, Marketplace, and EdTech integration checks. All calls use offline fixtures. |
| 4:35–5:00 | Point out the runner's explicit offline notice and summarize response validation. | The runner states no live APIs were called. Agents reject malformed JSON, missing required fields, and invalid field types; affected pipeline results can be reported as unavailable. | Milestone 4 reliability work and honest test scope. |

## Important demo notes

- The frontend currently renders Market and Competitor results, but not SWOT,
  MVP, or GTM. Show those outputs in the `/validate` Network response or in the
  downloaded report.
- The Advisor currently has an API endpoint but no frontend question form.
- The five-domain runner uses synthetic stub fixtures. Its passes verify graph
  wiring, response contracts, and report generation; they do **not** prove live
  AI analysis quality, factual accuracy, or domain relevance.
- Live analysis requires working Tavily and Google Gemini credentials. Report
  any errors or null analysis fields visible during a live run; do not replace
  them with fixture output during the demo.
- `GET /` still returns a legacy milestone label. Use `/docs` to confirm the
  current API routes.
