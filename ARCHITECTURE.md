# System Architecture - AI Startup Idea Validator

Milestone 1, Orbit ISB 7.0.

## 1. What the product does

A founder types their startup idea into a web page. The system searches the
live web for information about that idea and shows what it found.

They get back three things: a short summary of what the web says, the list of
search queries the agent actually ran, and a list of real sources they can
click through to.

The point is to turn a vague idea into real evidence - who the competitors are,
how big the market is, and what people complain about in existing solutions.

## 2. What an "agent" means in this system

An agent here is a component with one job, a fixed input, a fixed output, and a
specific set of tools it is allowed to use.

The Web Search Agent in this project:

- Job: gather web evidence about a startup idea
- Input: one idea, as a string
- Output: a summary, the queries it ran, and a ranked list of sources
- Tool: the Tavily Search API

It does not use an LLM. It does not need one. What makes it an agent is the
fixed contract, not the intelligence behind it.

That contract is the important part. Because the input and output shapes are
fixed, Milestone 2 can add a Competitor Agent and a Market Sizing Agent as new
files in `agents/` without changing this one at all.

The same reasoning already applies inside this agent. Its three searches do not
depend on each other, so they are run at the same time rather than one after
another. Independent agents can be run the same way in Milestone 2.

## 3. How the pieces connect

```
Browser (index.html + script.js)
        |
        |  POST /validate   {"idea": "..."}
        v
FastAPI backend (main.py)
        |
        |  calls search_idea(idea)
        v
Web Search Agent (agents/web_search_agent.py)
        |
        |  3 search calls, all at the same time
        v
Tavily Search API
        |
        |  results come back
        v
Agent merges, ranks, de-duplicates and counts
        |
        v
JSON response -> script.js -> results and run stats on the page
```

The frontend never talks to Tavily directly. Everything goes through the
backend.

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

## 5. The API contract

**POST /validate**

Request:

```json
{ "idea": "an app that helps students split rent with roommates" }
```

Response:

```json
{
  "idea": "an app that helps students split rent with roommates",
  "queries": [
    "... competitors and similar startups",
    "... market size and industry growth trends",
    "existing solutions and customer complaints about ..."
  ],
  "categories": ["Competitors", "Market size & trends", "Customer demand"],
  "counts": {
    "Competitors": 4,
    "Market size & trends": 4,
    "Customer demand": 3
  },
  "summary": "Splitwise, Tricount and Settle Up are top apps for splitting rent...",
  "results": [
    {
      "title": "Best Roommate Expense Tracker Apps",
      "url": "https://www.tryzedger.com/blog/best-roommate-expense-tracker-apps",
      "snippet": "Compare Zedger, Splitwise, Venmo and more for splitting rent...",
      "score": 0.73,
      "category": "Competitors"
    }
  ],
  "elapsed_seconds": 1.2,
  "stats": {
    "searches_run": 3,
    "searches_succeeded": 3,
    "raw_results": 15,
    "duplicates_removed": 4,
    "shown": 11,
    "distinct_sites": 9,
    "elapsed_seconds": 1.2
  }
}
```

There is also **GET /** which returns a short service message, used to check
the API is running.

## 6. Decisions and why

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

## 7. What comes next

- More agents in `agents/` - a Competitor Agent and a Market Sizing Agent - run
  concurrently with each other, the same way the three searches already are.
- Caching repeated searches, so the same idea submitted twice does not spend
  Tavily credits twice.
- An LLM writing the search queries instead of the fixed templates in
  `build_queries()`. Only that one function would need to change.
- A synthesis agent that takes the other agents' output and scores the idea.
