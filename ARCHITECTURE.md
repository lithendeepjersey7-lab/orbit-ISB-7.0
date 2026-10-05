# System Architecture - Litmus

AI Startup Idea Validator. Orbit ISB 7.0, Milestones 1 through 4.

## 1. What the product does

A founder submits an idea through the web UI. Tavily gathers live evidence,
then the analysis agents produce market, competitor, SWOT/risk, MVP, and GTM
outputs.

The response includes cited search sources, structured analyses, a PDF report,
and a follow-up advisor grounded in report sections and live-search results.

Milestones 1 and 2 provide research and market/competitor analysis. Milestone
3 adds strategy analyses and the conversational advisor; Milestone 4 adds PDF
reporting, pipeline UI, and offline integration coverage.

## 2. What an "agent" means in this system

An agent here is a component with one job, a fixed input, a fixed output, and a
specific set of tools it is allowed to use.

| Agent | Job | Tool |
|---|---|---|
| Web Search | gather web evidence about an idea | Tavily Search API |
| Market Opportunity | market size, growth, customer segments | Gemini API |
| Competitor Discovery | competitors, comparison, market gaps | Gemini API |
| SWOT & Risk | SWOT and categorized risks with likelihood, impact, mitigations | Gemini API |
| MVP Planning | Must/Should/Nice-to-have features and phased build order | Gemini API |
| Go-to-Market | positioning, channels, first 100 users, monetization, 90-day plan | Gemini API |
| Conversational Advisor | grounded follow-ups with source IDs | Gemini API |

The Web Search Agent uses no LLM; its fixed input/output contract is its role.
The Advisor is an API capability outside the validation graph: each request
must include the startup idea and current analysis context.

Fixed inputs and outputs keep responsibilities separate. The validation
agents live in `backend/agents/`; report generation is a separate module.

## 3. How the pieces connect

```
Browser (index.html + script.js)
        |
        |  POST /validate   {"idea": "..."}
        v
FastAPI backend (main.py)
        |
        |  calls validate(idea)
        v
Pipeline (agents/pipeline.py)  -  a LangGraph state graph
        |
        v
   Web Search Agent  ------> Tavily API
        |
        |  ranked results are written into shared state
        |
        +---------------------------+
        |                           |
        v                           v
  Market Agent               Competitor Agent      (these two run
        |                           |               at the same time)
        v                           v
    Gemini API                 Gemini API
        |                           |
        +------------+--------------+
                     |
                SWOT -> MVP -> GTM
                     |
        JSON response -> UI -> advisor / PDF report
```

The frontend never talks to Tavily or Gemini directly. Both keys live on the
server.

## 4. What the Web Search Agent does, step by step

**Step 1 - Plan.** `build_queries()` turns the one idea into three search
queries:

1. `{idea} competitors and similar startups`
2. `{idea} market size and industry growth trends`
3. `existing solutions and customer complaints about {idea}`

Three instead of one, because searching the founder's raw sentence just returns
general articles about the topic. These three angles return competitors, market
size and customer complaints - which is what validating an idea actually needs.

**Step 2 - Search.** One Tavily call per query, and all three run at the same
time. A `ThreadPoolExecutor` with `max_workers=3` gives one worker per search -
there is no fourth search for a fourth worker to pick up.

Threads are the right tool here because the searches spend almost all of their
time waiting on the network rather than using the CPU, and a thread that is
waiting on a network reply is not holding the others up.

Measured on the same idea: 2.3 seconds one after another, 1.2 seconds all at
once. That is a 2x speed-up rather than 3x, and the reason is worth stating.
Run sequentially you pay the sum of all three searches. Run concurrently you
pay only the slowest one, because the request is finished when the last search
returns. The ceiling is set by the slowest call, not by how many calls there
are.

Each call is wrapped in its own `try / except`, so if one query fails the other
two still return results. One failure does not kill the whole request.

**Step 3 - Reduce.** The three result sets are merged, then sorted by Tavily's
relevance score, and then duplicate URLs are removed.

The order of those last two steps matters. Results arrive grouped by query, so
the merged list is not in overall order. If duplicates were removed first, the
code would keep whichever copy arrived first, which is often the weaker one,
and that page would then be ranked by the wrong score. Sorting first means the
highest-scoring copy of each URL is the one that survives.

Every result carries a `category` field naming the search that found it -
`Competitors`, `Market size & trends` or `Customer demand`. The label is
attached to each individual result rather than just counted per query, because
merging and sorting destroy the grouping: once the list is in relevance order
there is nothing left in it to say which search produced which page. The label
travelling on the result is the only surviving record, and it is what lets the
frontend group the sources by what they are evidence of.

**Step 4 - Report.** The agent returns an account of its own run alongside the
results: how many searches it ran and how many of them succeeded, how many raw
results came back, how many duplicates were collapsed, how many sources are
shown, how many distinct sites those sources come from, and how long the whole
thing took.

`distinct_sites` is the one worth explaining. Eleven results from nine
different domains means nine separate sources agreeing. Eleven results from two
domains is really two sources repeated - which looks like strong evidence in a
list but is not. Counting domains puts a quality signal next to the quantity
one.


## 5. The Market Opportunity and Customer Segmentation Agent

- Job: turn search results into a structured market analysis
- Input: the idea, plus the ranked results from the Web Search Agent
- Output: market summary, market size, growth and demand, customer segments,
  and what the sources did not answer - all as JSON
- Tool: the Gemini API

**Step 1 - Condense.** `condense()` keeps the twelve highest-scoring results and
reduces each to one line of category, title and snippet. Sending all fifteen
with their URLs and scores wastes tokens and buries the useful text.

**Step 2 - Prompt.** The prompt shows the model the exact JSON skeleton it must
fill in, then states the rules. A template is followed far more reliably than a
prose description of the same shape, and it means adding a field later is a
one-line change in one place.

Four rules carry most of the quality:

**Ground every claim, and label anything that is not grounded.** Where the
sources do not cover something, the agent says so in that field and then gives
its estimate in a sentence beginning exactly `Estimate (not from sources):`.
The frontend highlights that phrase, so a founder can see which numbers came
from evidence and which are the model's own inference. Most tools blur that
line; this one draws it on the page.

**Never describe what the sources are.** An early version produced: "the search
results reference research reports covering undergraduate and postgraduate
student segments, tracking growth from 2020 through 2034" - a sentence
containing no market size at all. The rule now forces either the figure itself
or an honest statement that it is missing.

**At most three segments, and they must be genuinely different customers.** The
first version returned "undergraduate students", "postgraduate students" and
"flexible rent payment seekers" - one person wearing three hats. The rule now
says return fewer rather than pad, and explain the shortfall in
`evidence_gaps`. A later run duly returned two and wrote: "Only two distinct
customer segments are supported by the provided data."

**Every segment is labelled `buyer`, `supply`, `both` or `n/a`,** so a
two-sided marketplace is visible as one rather than read as a flat list.

**Step 3 - Parse and validate.** `parse_json()` accepts plain or fenced JSON,
then uses `agents/response_validation.py` to check the required fields and
nested types. The Market agent also enforces the three-segment maximum and
allowed `side` values. Invalid responses return `None` rather than being passed
downstream as analysis.

## 6. The Competitor Discovery and Comparison Agent

- Job: map the competitive landscape and find where the idea could fit
- Input: the same idea and the same search results
- Output: a landscape summary, up to six competitors with a comparison, and the
  overall market gaps - as JSON
- Tool: the Gemini API

The competitor agent uses the same search-result condensation and shared JSON
schema validator. What differs is its prompt and domain constraints:

**Direct or indirect, with the reasoning attached.** Each competitor carries a
`type` and a one-line `why_this_type`. A direct competitor solves the same
problem for the same customer; an indirect one solves it differently or for an
adjacent customer. On the freelance-nursing test, five gig platforms came back
`direct` and Maxim Healthcare Services - a traditional staffing agency - came
back `indirect`, which is exactly the distinction the label is for. The
frontend shows the reasoning on hover.

**Up to six, never padded.** "Returning three real ones is better than six with
three guesses."

**Listicles are sources, not competitors.** Search results for consumer ideas
are full of articles like "10 Best Rent Splitting Apps". The rule says extract
the products named inside them and never list a blog or publisher as a rival.
Across the test runs, no article has been listed as a competitor.

**Short fields.** `offering`, `positioning` and `target_customer` are one or two
lines each, because the brief asks for output that is easy to scan and compare,
and the frontend renders them as a comparison table. This is a deliberate
difference from the market agent, whose fields are full paragraphs.

**Gaps at both levels.** Each competitor has its own `weak_spots`; the overall
`market_gaps` is what the founder actually acts on.

## 7. Orchestration

`agents/pipeline.py` is a LangGraph `StateGraph`. A node is an ordinary Python
function that reads shared state and returns only the keys it changed.

```
START -> search -+-> market      -+
                 +-> competitors -+-> swot -> mvp -> gtm -> END
```

**Market and competitor analysts run at the same time.** Both read search
results; SWOT then follows both branches, followed by MVP and GTM.

**The `errors` key needs a reducer.** It is declared as
`Annotated[list, operator.add]`. Both analysts can append to it, and when two
parallel branches write the same key LangGraph raises `InvalidUpdateError` -
it has no way to know which should win. `operator.add` tells it not to pick a
winner but to concatenate. Every other field is written by exactly one node, so
only `errors` needs this.

**Failure is partial where a stage can be skipped.** Search exceptions and
unusable Market, Competitor, SWOT, MVP, or GTM responses are recorded in
`errors`. SWOT requires Market and Competitor; MVP requires Market and
Competitor; GTM requires Market, Competitor, and SWOT. A missing prerequisite
leaves that result `null` and the later stage reports why it was skipped. The
frontend displays the error list above its rendered results.

**The graph is compiled once at import,** not per request. Compiling inside the
route handler would rebuild it on every call.

## 8. Milestone 3 analysis stages

After the parallel Market and Competitor analyses finish, the pipeline runs
three synthesis stages:

1. **SWOT** (`swot_agent.py`) receives the idea, Market analysis, and
  Competitor analysis. It returns strengths, weaknesses, opportunities,
  threats, and execution risks.
2. **MVP** (`mvp_agent.py`) receives the idea, Market analysis, and Competitor
  analysis. It returns a target audience, product summary, must-have features,
  and optional nice-to-have features.
3. **GTM** (`gtm_agent.py`) receives the idea, Market analysis, Competitor
  analysis, and SWOT. It returns positioning, early target customers,
  acquisition channels, and actions grouped into the first three 30-day
  periods.

The pipeline keeps each result under its own response field. There is no
overall numeric validation score in the current implementation.

The **Startup Advisor** is a separate endpoint, not a LangGraph node. It accepts
a question plus the idea and all five analysis objects (Market, Competitor,
SWOT, MVP, and GTM). Its structured response includes an answer, a
`has_sufficient_context` boolean, and `missing_context` details. The current
frontend has no Advisor form, and the route is stateless: the caller must send
the context with each question.

## 9. Report generation, testing, and reliability

`POST /report` passes the complete `/validate` result to
`report_generator.py`. The module uses those supplied values, escapes text for
HTML, and creates six sections: startup idea/executive summary, Market,
Competitor, SWOT and risks, MVP, and GTM. Missing or null sections show a
not-available message. The response is an HTML attachment. The frontend's
Download validation report button sends the current validation result and
saves the returned HTML.

`backend/e2e_test_runner.py` runs the complete pipeline and report endpoint for
five domains: SaaS, Consumer, Hardware, Marketplace, and EdTech. It replaces
Tavily and Gemini calls with labelled offline fixtures. This checks graph
dependencies, result shapes, report sections, and download response headers;
it does **not** evaluate live AI output quality or factual accuracy.

Each Gemini-backed agent uses `agents/response_validation.py` to parse plain
or fenced JSON and verify required fields and nested types. Agent-specific
checks also enforce constraints such as competitor classifications and
required MVP/GTM content. Invalid responses become unusable results and are
reported through the pipeline's partial-failure path; there is no automatic
retry or repair step.

## 10. The API contract

**POST /validate**

Request:

```json
{ "idea": "an app that helps students split rent with roommates" }
```

Response - the original search fields remain, with each analysis returned
separately:

```json
{
  "idea": "...",
  "queries": ["...", "...", "..."],
  "categories": ["Competitors", "Market size & trends", "Customer demand"],
  "counts": { "Competitors": 5, "Market size & trends": 5, "Customer demand": 5 },
  "summary": "...",
  "results": [
    { "title": "...", "url": "...", "snippet": "...", "score": 0.73,
      "category": "Competitors" }
  ],
  "stats": {
    "searches_run": 3, "searches_succeeded": 3, "raw_results": 15,
    "duplicates_removed": 0, "shown": 15, "distinct_sites": 15,
    "elapsed_seconds": 1.6
  },
  "market": {
    "market_summary": "...", "market_size": "...", "growth_and_demand": "...",
    "segments": [
      { "name": "...", "side": "buyer", "who_they_are": "...",
        "pain_points": "...", "buying_behaviour": "..." }
    ],
    "evidence_gaps": "..."
  },
  "competitors": {
    "landscape_summary": "...",
    "competitors": [
      { "name": "...", "type": "direct", "why_this_type": "...",
        "offering": "...", "positioning": "...", "target_customer": "...",
        "weak_spots": "..." }
    ],
    "market_gaps": "..."
  },
  "swot": { "strengths": [], "weaknesses": [], "opportunities": [],
            "threats": [], "execution_risks": [] },
  "mvp": { "target_audience": "...", "product_summary": "...",
           "must_have_features": [], "nice_to_have_features": [] },
  "gtm": { "positioning": {}, "early_target_customers": [],
           "customer_acquisition_channels": [], "first_90_days": {} },
  "errors": [],
  "elapsed_seconds": 6.0
}
```

Any failed agent output is `null`; `errors` reports the failed or skipped stage.

**POST /advisor**

**POST /advisor** accepts analysis outputs, live search results, and recent
conversation turns. It returns an answer, sufficiency flag, missing context,
and citations resolved against only supplied report sections and URLs, labeled
`From report` or `From live search`.

**POST /report** returns a downloadable PDF (`application/pdf`) with analysis
sections, sources, roadmap, and a 0–100 evidence-coverage score. This measures
report completeness, not business viability or investment merit.

## 9. Decisions and why

**Query expansion instead of searching the raw sentence.** Explained in
section 4. It is the main reason the results are useful instead of generic.

**The API key stays on the server.** `script.js` runs inside the user's
browser, so anything written in it can be read by anyone who opens DevTools.
The key is kept in `backend/.env`, which is listed in `.gitignore` so it never
reaches GitHub either.

**Analysis and report logic are separate from routes.** `main.py` delegates to
the validation pipeline, Advisor agent, and HTML report builder.

**The three searches run concurrently.** They do not depend on each other, so
running them one after another only made the founder wait longer for the same
answer.

**The agent reports on its own run.** The `stats` block is not decoration - it
is what makes the agent's work checkable from the outside. The numbers have to
add up: `raw_results` minus `duplicates_removed` must equal `shown`.

**CORS is set to `allow_origins=["*"]` for now.** This lets any website call
the API. That is fine for a milestone demo and it avoids CORS problems during a
presentation, but it does mean anyone could call the API and spend the Tavily
credits. Before this goes public it should be changed to only the deployed
frontend URL.

**LangGraph rather than CrewAI.** Both were installed and measured on Python
3.13 before choosing. LangGraph's stack is 87 MB on disk and about 99 MB of
memory at runtime; CrewAI's is 833 MB and about 224 MB, and 424 MB if
`memory=True` is left on. Render's free tier kills the service above 512 MB, so
the margin mattered. LangGraph also does not raise from an `async def` route,
and a LangGraph node is an ordinary function that can be called and printed
inside, whereas a CrewAI agent's behaviour is tuned by rewording its backstory.

**Gemini's free tier, and `gemini-3.7-flash` specifically.** No credit card is
required. `gemini-2.5-flash` is closed to new accounts, so the model list was
queried from the API rather than copied from a tutorial.

**A thinking budget of 512 tokens.** Uncapped, the same competitor prompt took
140.8 seconds on one run and 59.0 on another - the model decides how long to
think and it varies enormously. Capping it at 128 tokens took the whole pipeline
from 126 seconds to 27, but the output degraded: the model stopped filling in
the `side` field on segments. 512 tokens on `gemini-3.7-flash` gave 6 seconds
end to end with the reasoning intact. The speed-up was worth having; the
quality check on it was worth more.

**The analysts run concurrently, the pipeline degrades partially.** Both
covered in section 7.

## 10. Milestones 3 and 4: contracts and limitations

`response_validation.py` enforces required JSON fields and nested types.
Pipeline failures degrade partially and are reported. Transient Gemini 503
errors receive four bounded retries; if Gemini 3.7 Flash stays overloaded, the
same prompt is sent to Gemini 2.5 Flash with its own bounded retry budget. A
malformed structured reply receives one bounded JSON-repair attempt. The
offline integration runner stubs all external providers and covers SaaS,
consumer, hardware, marketplace, and EdTech ideas, including agent schemas,
failures, advisor calls, and PDF output.

The browser carries up to four question/answer pairs into advisor follow-ups;
there is no server-side user or session store. The advisor can use history to
resolve context but must cite current report/source inputs.

The frontend offers section-level “Ask about this” actions, suggested
questions, citations, and PDF download. Report status uses a transparent
evidence-coverage score, not an unsupported prediction of startup success.

Operational follow-ups include restricting wildcard CORS before public
production use and defining a freshness policy before adding search caching.
