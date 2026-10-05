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

The Web Search Agent uses no LLM and does not need one - what makes it an agent
is the fixed contract, not the intelligence behind it. The two analysts do need
one, because they produce judgements rather than retrieve documents.

That contract is the important part. Because the input and output shapes are
fixed, Milestone 2 added two agents as new files in `agents/` without changing
the Milestone 1 agent by a single line.

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

**Step 3 - Parse.** `parse_json()` strips a markdown code fence if the model
wrapped its JSON in one, then parses. It returns `None` rather than raising, so
one bad reply cannot kill the request.

## 6. The Competitor Discovery and Comparison Agent

- Job: map the competitive landscape and find where the idea could fit
- Input: the same idea and the same search results
- Output: a landscape summary, up to six competitors with a comparison, and the
  overall market gaps - as JSON
- Tool: the Gemini API

Same three steps and the same two helpers. What differs is the prompt:

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

**Failure is partial, not total.** Each node catches its own failure, returns
`None` for its slice of the result, and appends a line to `errors`. If the
market agent fails and the competitor agent succeeds, the founder gets the
competitor analysis plus a note saying which part is missing - not a blank
page. The frontend renders that list in a red panel above the results.

**The graph is compiled once at import,** not per request. Compiling inside the
route handler would rebuild it on every call.

## 8. The API contract

**POST /validate**

Request:

```json
{ "idea": "an app that helps students split rent with roommates" }
```

Response - every Milestone 1 field is still present under the same name, so the
existing frontend kept working when the route was switched over:

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
  "errors": [],
  "elapsed_seconds": 6.0
}
```

Any failed agent output is `null`; `errors` reports the failed or skipped stage.

There is also **GET /** which returns a short service message, used to check the
API is running.

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

**The agent lives in its own file.** Routes in `main.py` stay thin - the
`/validate` route just calls the agent and returns the result. Keeping the
logic separate is what lets Milestone 2 add more agents as new files without
touching `main.py`.

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

**Gemini model identifiers are deployment-sensitive.** The app uses
`gemini-3.7-flash` as its configured primary and falls back to `gemini-3.8-flash`
when the primary is overloaded or model-quota limited. A live API response
confirmed `gemini-2.5-flash` is no longer available to new users, so it is not
used as the fallback.

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
Pipeline failures degrade partially and are reported. Transient Gemini 503 and
500 INTERNAL errors receive one quick retry; if Gemini 3.7 Flash stays
overloaded, the same prompt is sent to Gemini 3.8 Flash with one retry. A model-specific 429
quota response switches models once without repeating the limited-model call.
Project-wide quota exhaustion still requires an operator to restore quota or
configure billing/API credentials. A malformed structured reply receives one
bounded JSON-repair attempt. The offline integration runner stubs all external providers and covers SaaS,
consumer, hardware, marketplace, and EdTech ideas, including agent schemas,
failures, advisor calls, and PDF output.

Downstream strategy agents continue from whatever market and competitor
context is available. SWOT and MVP still run when both research stages fail;
their clearly labelled fallback drafts use only the idea and mark the missing
evidence instead of skipping these important sections.

SWOT and MVP also return a conservative, context-limited draft when Gemini
fails or produces unusable output. The response includes `analysis_mode` and
`analysis_note`, and the pipeline surfaces a warning; these drafts are not
represented as model-generated analysis and should be validated with customers.

The browser carries up to four question/answer pairs into advisor follow-ups;
there is no server-side user or session store. The advisor can use history to
resolve context but must cite current report/source inputs.

The frontend offers section-level “Ask about this” actions, suggested
questions, citations, and PDF download. Report status uses a transparent
evidence-coverage score, not an unsupported prediction of startup success.

Operational follow-ups include restricting wildcard CORS before public
production use and defining a freshness policy before adding search caching.
