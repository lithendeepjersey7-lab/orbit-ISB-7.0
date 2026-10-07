"""Orchestration for the AI Startup Idea Validator.

One idea in, a full validation out. The web search agent runs first, then the
market and competitor agents run at the same time on its results, followed by
SWOT, MVP, and go-to-market strategy in sequence.

    START -> search -+-> market      -+
                     +-> competitors -+-> swot -> mvp -> gtm -> END
"""

import json
import operator
import time
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

# This file has to work two ways: run directly for testing, and imported by
# main.py as `agents.pipeline`. Those two contexts need different import paths.
try:
    from web_search_agent import search_idea
    from market_agent import (
        analyse_market,
        _fallback_analysis as market_fallback,
        parse_json as parse_market,
    )
    from competitor_agent import (
        analyse_competitors,
        _fallback_analysis as competitor_fallback,
        parse_json as parse_competitors,
    )
    from swot_agent import (
        analyse_swot,
        _fallback_analysis as swot_fallback,
        parse_json as parse_swot,
    )
    from mvp_agent import (
        recommend_mvp,
        _fallback_recommendation as mvp_fallback,
        parse_json as parse_mvp,
    )
    from gtm_agent import (
        develop_gtm_strategy,
        _fallback_strategy as gtm_fallback,
        parse_json as parse_gtm,
    )
    from gemini_retry import take_failure
except ImportError:
    from agents.web_search_agent import search_idea
    from agents.market_agent import (
        analyse_market,
        _fallback_analysis as market_fallback,
        parse_json as parse_market,
    )
    from agents.competitor_agent import (
        analyse_competitors,
        _fallback_analysis as competitor_fallback,
        parse_json as parse_competitors,
    )
    from agents.swot_agent import (
        analyse_swot,
        _fallback_analysis as swot_fallback,
        parse_json as parse_swot,
    )
    from agents.mvp_agent import (
        recommend_mvp,
        _fallback_recommendation as mvp_fallback,
        parse_json as parse_mvp,
    )
    from agents.gtm_agent import (
        develop_gtm_strategy,
        _fallback_strategy as gtm_fallback,
        parse_json as parse_gtm,
    )
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


def _fallback_notice(label: str, fallback_detail: str) -> str:
    provider_failure = take_failure()
    detail = provider_failure or fallback_detail
    return label + ": " + detail


def _has_content(value, path=(), allow_empty_lists=()):
    """Reject blank reports while allowing no verified competitors."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return all(
            _has_content(child, path + (key,), allow_empty_lists)
            for key, child in value.items()
        )
    if isinstance(value, list):
        if not value and path not in allow_empty_lists:
            return False
        return all(_has_content(child, path, allow_empty_lists) for child in value)
    return value is not None


def _usable_result(result, parser, allow_empty_lists=()):
    """Require both the agent's schema and non-empty required report content."""
    if not isinstance(result, dict):
        return False
    try:
        if parser(json.dumps(result)) is None:
            return False
    except (TypeError, ValueError):
        return False
    return _has_content(
        result,
        allow_empty_lists={
            ("competitors",),
            ("research_leads",),
            ("source_findings",),
            *allow_empty_lists,
        },
    )


def _unexpected_failure(label: str, error: Exception) -> str:
    take_failure()
    return "{} failed unexpectedly ({}); used a local fallback draft".format(
        label, type(error).__name__
    )


def search_node(state: State) -> dict:
    """Milestone 1's agent, unchanged, as step one."""
    try:
        result = search_idea(state["idea"])
        if not isinstance(result, dict) or not isinstance(result.get("results"), list):
            raise ValueError("search returned an incomplete response")
        return {"search": result}
    except Exception as error:
        empty_search = {
            "idea": state["idea"],
            "queries": [],
            "categories": [],
            "counts": {},
            "summary": None,
            "results": [],
            "stats": {
                "searches_run": 0,
                "searches_succeeded": 0,
                "raw_results": 0,
                "duplicates_removed": 0,
                "shown": 0,
                "distinct_sites": 0,
                "elapsed_seconds": 0.0,
            },
            "analysis_mode": "analysis_unavailable",
            "analysis_note": "Live search failed; no external evidence is available for this run.",
        }
        return {
            "search": empty_search,
            "errors": [_unexpected_failure("Web search", error)],
        }


def market_node(state: State) -> dict:
    try:
        result = analyse_market(
            state["idea"],
            (state.get("search") or {}).get("results", []),
        )
    except Exception as error:
        return {
            "market": market_fallback([], state["idea"]),
            "errors": [_unexpected_failure("Market agent", error)],
        }
    if not _usable_result(result, parse_market):
        error = _agent_failure("Market agent") if result is None else "incomplete or blank response"
        return {
            "market": market_fallback(
                (state.get("search") or {}).get("results", []), state["idea"]
            ),
            "errors": ["Market agent returned no usable analysis: " + error],
        }
    if result.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}:
        return {
            "market": result,
            "errors": [_fallback_notice(
                "Market agent returned search leads only",
                "no source-grounded synthesis was available",
            )],
        }
    return {"market": result}


def competitor_node(state: State) -> dict:
    try:
        result = analyse_competitors(
            state["idea"],
            (state.get("search") or {}).get("results", []),
        )
    except Exception as error:
        return {
            "competitors": competitor_fallback([]),
            "errors": [_unexpected_failure("Competitor agent", error)],
        }
    if not _usable_result(result, parse_competitors):
        error = _agent_failure("Competitor agent") if result is None else "incomplete or blank response"
        return {
            "competitors": competitor_fallback(
                (state.get("search") or {}).get("results", [])
            ),
            "errors": ["Competitor agent returned no usable analysis: " + error],
        }
    if result.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}:
        return {
            "competitors": result,
            "errors": [_fallback_notice(
                "Competitor agent returned search leads only",
                "competitors were not independently verified",
            )],
        }
    return {"competitors": result}


def swot_node(state: State) -> dict:
    """Run SWOT even with missing research; the agent labels any fallback draft."""
    market = state.get("market") or {}
    competitors = state.get("competitors") or {}
    try:
        result = analyse_swot(state["idea"], market, competitors)
    except Exception as error:
        return {
            "swot": swot_fallback(state["idea"], market, competitors),
            "errors": [_unexpected_failure("SWOT agent", error)],
        }
    if not _usable_result(result, parse_swot):
        error = _agent_failure("SWOT agent") if result is None else "incomplete or blank response"
        return {
            "swot": swot_fallback(state["idea"], market, competitors),
            "errors": ["SWOT agent returned no usable analysis: " + error],
        }
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "swot": result,
            "errors": [_fallback_notice(
                "SWOT agent used a conservative fallback",
                "it could not produce a reliable analysis",
            )],
        }
    return {"swot": result}


def mvp_node(state: State) -> dict:
    """Recommend an MVP from available research, or the idea alone if needed."""
    market = state.get("market") or {}
    competitors = state.get("competitors") or {}
    try:
        result = recommend_mvp(
            state["idea"], market, competitors, state.get("swot")
        )
    except Exception as error:
        return {
            "mvp": mvp_fallback(state["idea"], market, competitors),
            "errors": [_unexpected_failure("MVP agent", error)],
        }
    if not _usable_result(
        result,
        parse_mvp,
        allow_empty_lists=(("should_have_features",), ("nice_to_have_features",)),
    ):
        error = _agent_failure("MVP agent") if result is None else "incomplete or blank response"
        return {
            "mvp": mvp_fallback(state["idea"], market, competitors),
            "errors": ["MVP agent returned no usable analysis: " + error],
        }
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "mvp": result,
            "errors": [_fallback_notice(
                "MVP agent used a conservative fallback",
                "it could not produce a reliable recommendation",
            )],
        }
    return {"mvp": result}


def gtm_node(state: State) -> dict:
    """Create a GTM strategy after the existing analyses and MVP stage."""
    market = state.get("market") or {}
    competitors = state.get("competitors") or {}
    try:
        result = develop_gtm_strategy(
            state["idea"], market, competitors, state.get("swot") or {}
        )
    except Exception as error:
        return {
            "gtm": gtm_fallback(state["idea"], market),
            "errors": [_unexpected_failure("GTM agent", error)],
        }
    if not _usable_result(result, parse_gtm):
        error = _agent_failure("GTM agent") if result is None else "incomplete or blank response"
        return {
            "gtm": gtm_fallback(state["idea"], market),
            "errors": ["GTM agent returned no usable analysis: " + error],
        }
    if result.get("analysis_mode") == "conservative_fallback":
        return {
            "gtm": result,
            "errors": [_fallback_notice(
                "GTM agent used a conservative fallback",
                "it could not produce a reliable strategy",
            )],
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
