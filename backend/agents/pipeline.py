"""Orchestration for the AI Startup Idea Validator.

One idea in, a full validation out. The web search agent runs first, then the
market and competitor agents run at the same time on its results, followed by
SWOT, MVP, and go-to-market strategy in sequence.

    START -> search -+-> market      -+
                     +-> competitors -+-> swot -> mvp -> gtm -> END
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
    from swot_agent import analyse_swot
    from mvp_agent import recommend_mvp
    from gtm_agent import develop_gtm_strategy
    from gemini_retry import take_failure
except ImportError:
    from agents.web_search_agent import search_idea
    from agents.market_agent import analyse_market
    from agents.competitor_agent import analyse_competitors
    from agents.swot_agent import analyse_swot
    from agents.mvp_agent import recommend_mvp
    from agents.gtm_agent import develop_gtm_strategy
    from agents.gemini_retry import take_failure


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
    swot: Optional[dict]
    mvp: Optional[dict]
    gtm: Optional[dict]
    errors: Annotated[list, operator.add]


def _agent_failure(label: str) -> str:
    """Explain why an agent produced nothing.

    If the Gemini call itself failed (for example 503 after retries) say so,
    including the original error. Otherwise the model answered but its reply
    was empty or failed validation, which is the old "no usable JSON" case.
    """
    reason = take_failure()
    if reason:
        return label + " failed: " + reason
    return label + " returned no usable JSON"


def search_node(state: State) -> dict:
    """Milestone 1's agent, unchanged, as step one."""
    try:
        return {"search": search_idea(state["idea"])}
    except Exception as error:
        return {"search": None, "errors": ["Web search failed: " + str(error)]}


def market_node(state: State) -> dict:
    result = analyse_market(
        state["idea"],
        (state.get("search") or {}).get("results", []),
    )
    if result is None:
        return {"market": None, "errors": [_agent_failure("Market agent")]}
    if result.get("analysis_mode") == "analysis_unavailable":
        return {
            "market": result,
            "errors": ["Market agent has no source-grounded analysis for this run"],
        }
    return {"market": result}


def competitor_node(state: State) -> dict:
    result = analyse_competitors(
        state["idea"],
        (state.get("search") or {}).get("results", []),
    )
    if result is None:
        return {"competitors": None, "errors": [_agent_failure("Competitor agent")]}
    if result.get("analysis_mode") == "analysis_unavailable":
        return {
            "competitors": result,
            "errors": ["Competitor agent has no source-grounded analysis for this run"],
        }
    return {"competitors": result}


def swot_node(state: State) -> dict:
    """Run SWOT even with missing research; the agent labels any fallback draft."""
    result = analyse_swot(
        state["idea"],
        state.get("market") or {},
        state.get("competitors") or {},
    )
    if result is None:
        return {"swot": None, "errors": [_agent_failure("SWOT agent")]}
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "swot": result,
            "errors": ["SWOT agent used a conservative fallback because it could not produce a reliable analysis"],
        }
    return {"swot": result}


def mvp_node(state: State) -> dict:
    """Recommend an MVP from available research, or the idea alone if needed."""
    result = recommend_mvp(
        state["idea"],
        state.get("market") or {},
        state.get("competitors") or {},
        state.get("swot"),
    )
    if result is None:
        return {"mvp": None, "errors": [_agent_failure("MVP agent")]}
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "mvp": result,
            "errors": ["MVP agent used a conservative fallback because it could not produce a reliable recommendation"],
        }
    return {"mvp": result}


def gtm_node(state: State) -> dict:
    """Create a GTM strategy after the existing analyses and MVP stage."""
    if not state.get("market") and not state.get("competitors") and not state.get("swot"):
        return {"gtm": None, "errors": ["GTM agent skipped: no upstream analysis available"]}
    result = develop_gtm_strategy(
        state["idea"],
        state.get("market") or {},
        state.get("competitors") or {},
        state.get("swot") or {},
    )
    if result is None:
        return {"gtm": None, "errors": [_agent_failure("GTM agent")]}
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "gtm": result,
            "errors": ["GTM agent used a conservative fallback because it could not produce a reliable strategy"],
        }
    return {"gtm": result}


_graph = StateGraph(State)
_graph.add_node("search", search_node)
_graph.add_node("market", market_node)
_graph.add_node("competitors", competitor_node)
_graph.add_node("swot", swot_node)
_graph.add_node("mvp", mvp_node)
_graph.add_node("gtm", gtm_node)

_graph.add_edge(START, "search")
_graph.add_edge("search", "market")        # fan out - these two
_graph.add_edge("search", "competitors")   # run at the same time
_graph.add_edge("market", "swot")
_graph.add_edge("competitors", "swot")
_graph.add_edge("swot", "mvp")
_graph.add_edge("mvp", "gtm")
_graph.add_edge("gtm", END)

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
        "swot": None,
        "mvp": None,
        "gtm": None,
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
        "swot": final.get("swot"),
        "mvp": final.get("mvp"),
        "gtm": final.get("gtm"),
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
