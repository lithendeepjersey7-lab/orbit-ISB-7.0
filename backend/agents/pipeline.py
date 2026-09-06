"""Orchestration for the AI Startup Idea Validator.

One idea in, a full validation out. The web search agent runs first, then the
market and competitor agents run at the same time on its results.

    START -> search -+-> market      -+-> END
                     +-> competitors -+
"""

import operator
import time
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

# This file has to work two ways: run directly for testing, and imported by
# main.py as `agents.pipeline`. Those two contexts need different import paths.
try:
    from web_search_agent import search_idea
    from market_agent import analyse_market
    from competitor_agent import analyse_competitors
except ImportError:
    from agents.web_search_agent import search_idea
    from agents.market_agent import analyse_market
    from agents.competitor_agent import analyse_competitors


class State(TypedDict):
    """The shared clipboard every node reads from and writes to.

    `errors` is Annotated with operator.add because the market and competitor
    nodes run at the same time and can both append to it. Without that reducer
    LangGraph raises InvalidUpdateError when two parallel branches write the
    same key - it has no way to know which one should win. The reducer says:
    don't pick, concatenate.
    """

    idea: str
    search: Optional[dict]
    market: Optional[dict]
    competitors: Optional[dict]
    errors: Annotated[list, operator.add]


def search_node(state: State) -> dict:
    """Milestone 1's agent, unchanged, as step one."""
    try:
        return {"search": search_idea(state["idea"])}
    except Exception as error:
        return {"search": None, "errors": ["Web search failed: " + str(error)]}


def market_node(state: State) -> dict:
    if not state.get("search"):
        return {"market": None, "errors": ["Market agent skipped: no search results"]}
    result = analyse_market(state["idea"], state["search"]["results"])
    if result is None:
        return {"market": None, "errors": ["Market agent returned no usable JSON"]}
    return {"market": result}


def competitor_node(state: State) -> dict:
    if not state.get("search"):
        return {"competitors": None, "errors": ["Competitor agent skipped: no search results"]}
    result = analyse_competitors(state["idea"], state["search"]["results"])
    if result is None:
        return {"competitors": None, "errors": ["Competitor agent returned no usable JSON"]}
    return {"competitors": result}


_graph = StateGraph(State)
_graph.add_node("search", search_node)
_graph.add_node("market", market_node)
_graph.add_node("competitors", competitor_node)

_graph.add_edge(START, "search")
_graph.add_edge("search", "market")        # fan out - these two
_graph.add_edge("search", "competitors")   # run at the same time
_graph.add_edge("market", END)
_graph.add_edge("competitors", END)

# Compiled once at import, never per request. Compiling inside the route
# handler would rebuild the graph on every call.
pipeline = _graph.compile()


def validate(idea: str) -> dict:
    """Run the whole pipeline and shape the API response.

    Every Milestone 1 field is still here under the same name, so the existing
    frontend keeps working. Milestone 2 adds market, competitors and errors.
    """
    started = time.perf_counter()

    final = pipeline.invoke({
        "idea": idea,
        "search": None,
        "market": None,
        "competitors": None,
        "errors": [],
    })

    search = final.get("search") or {}
    return {
        "idea": idea,
        # --- Milestone 1, unchanged ---
        "queries": search.get("queries", []),
        "categories": search.get("categories", []),
        "counts": search.get("counts", {}),
        "summary": search.get("summary"),
        "results": search.get("results", []),
        "stats": search.get("stats", {}),
        # --- Milestone 2 ---
        "market": final.get("market"),
        "competitors": final.get("competitors"),
        "errors": final.get("errors", []),
        "elapsed_seconds": round(time.perf_counter() - started, 1),
    }


if __name__ == "__main__":
    import json
    import os
    import sys

    test_idea = sys.argv[1] if len(sys.argv) > 1 else (
        "an app that helps students split rent with roommates"
    )

    print("Idea:", test_idea)
    print("Running the full pipeline...")
    out = validate(test_idea)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "test_runs")
    os.makedirs(out_dir, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in test_idea)[:40]
    path = os.path.join(out_dir, "pipeline_" + slug + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("Saved to", os.path.abspath(path))
    print()
    print("sources found :", len(out["results"]))
    print("market agent  :", "ok" if out["market"] else "FAILED")
    print("competitors   :", len(out["competitors"]["competitors"]) if out["competitors"] else "FAILED")
    print("errors        :", out["errors"] or "none")
    print("total time    :", out["elapsed_seconds"], "seconds")
