import json

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from response_validation import invoke_with_json_repair, parse_json_response
    from gemini_retry import invoke_with_retry
    from fallback_strategy import fallback_profile
except ImportError:
    from agents.response_validation import invoke_with_json_repair, parse_json_response
    from agents.gemini_retry import invoke_with_retry
    from agents.fallback_strategy import fallback_profile

load_dotenv()

MODEL = "gemini-3.7-flash"

# How many tokens the model may spend reasoning before it answers. Left
# uncapped it is dynamic and swings badly: the same competitor prompt took
# 140.8s once and 59.0s another time. Capping it at 128 gave 7.1s but the
# model stopped filling in the marketplace 'side' field, so the reasoning
# had degraded. 3.7-flash at 512 gave 4.3s and kept it. Measured 6 Sep.
THINKING_BUDGET = 512

# max_retries=0 turns off the client's own hidden retries (default 6, which
# include 429). Retrying is handled by gemini_retry.invoke_with_retry.
llm = ChatGoogleGenerativeAI(
    model=MODEL, thinking_budget=THINKING_BUDGET, max_retries=0,
    request_timeout=15,
)


def condense(results, limit=12):
    """Squash the search agent's results into compact text for the prompt.

    The search agent returns up to 15 results with scores and URLs. Sending all
    of that wastes tokens and buries the useful text, so keep the best twelve
    (they arrive already sorted by relevance) and reduce each to one line.
    """
    lines = []
    for item in results[:limit]:
        lines.append("[" + item["category"] + "] " + item["title"] + " - " + item["snippet"])
    return "\n".join(lines)


def parse_json(text):
    """Parse the model's reply as JSON, tolerating a markdown code fence.

    Models frequently wrap JSON in ```json ... ```. Strip that before parsing.
    Returns None instead of raising, so one bad reply cannot kill the request.
    """
    return parse_json_response(text, RESPONSE_SCHEMA)


# The exact JSON shape the model must return. Kept separate from the
# instructions so it is easy to add or rename a field later.
SHAPE = """{
  "market_summary": "",
  "market_size": "",
  "growth_and_demand": "",
  "segments": [
    {"name": "", "side": "", "who_they_are": "", "pain_points": "", "buying_behaviour": ""},
    {"name": "", "side": "", "who_they_are": "", "pain_points": "", "buying_behaviour": ""},
    {"name": "", "side": "", "who_they_are": "", "pain_points": "", "buying_behaviour": ""}
  ],
  "evidence_gaps": ""
}"""

RESPONSE_SCHEMA = {
    "market_summary": str,
    "market_size": str,
    "growth_and_demand": str,
    "segments": [{
        "name": str,
        "side": str,
        "who_they_are": str,
        "pain_points": str,
        "buying_behaviour": str,
    }],
    "evidence_gaps": str,
}

RULES = """RULES:
1. Ground every claim in the search results above. Say what the sources
   actually show, not what you assume about the industry.
2. If the search results do not cover something, say so plainly in that field,
   then add your estimate as a new sentence beginning exactly with
   "Estimate (not from sources):". Never present an estimate as if it came
   from the search results.
3. Never describe what documents the sources are. Do not write sentences like
   "the search results reference research reports covering X". Either give the
   actual figure or finding, or say the figure is not in the sources and then
   estimate it under rule 2.
4. Return at most three segments, and they must be genuinely different kinds
   of customer - not the same person at a different age, and not a behaviour
   that overlaps the other segments. If the evidence only supports two
   distinct segments, return two and explain why in "evidence_gaps". Never
   pad the list to reach three.
5. Set "side" on each segment to "buyer" if they pay, "supply" if they provide
   the service on a two-sided marketplace, "both" if they do each, or "n/a"
   when the idea is not a marketplace.
6. Keep the analysis concise and specific. Use one to three sentences per field,
   with concrete evidence or findings where available. Avoid repetition and
   filler.
7. Use the industry's own terminology where the sources use it.
8. Put anything a founder still needs to research, because these sources did
   not answer it, in "evidence_gaps"."""


def build_prompt(idea, evidence):
    """Assemble the full prompt. Plain concatenation so it stays easy to edit."""
    return (
        "You are a market analyst helping a founder validate a startup idea.\n"
        "Below are real web search results gathered for this idea. Read them and\n"
        "produce a market opportunity and customer segmentation analysis.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "WEB SEARCH RESULTS:\n" + evidence + "\n\n"
        "Return ONLY valid JSON, with no commentary before or after it, in\n"
        "exactly this shape:\n\n" + SHAPE + "\n\n" + RULES
    )


def _fallback_analysis(results, idea=""):
    profile = fallback_profile(idea)
    evidence = [
        {
            "title": str(item.get("title") or "Untitled source")[:160],
            "url": str(item.get("url") or ""),
            "category": str(item.get("category") or ""),
            "snippet": str(item.get("snippet") or "")[:300],
        }
        for item in results[:8]
        if isinstance(item, dict) and (item.get("title") or item.get("snippet"))
    ]
    market_sources = [
        item for item in evidence
        if "market" in item["category"].lower() or "demand" in item["category"].lower()
    ]
    if not market_sources:
        market_sources = evidence[:5]
    summary = (
        "Candidate customer segments are inferred from the submitted idea. Search leads below provide context but are not independently verified market findings."
        if market_sources
        else "Candidate customer segments are inferred from the submitted idea; market size and demand are not established."
    )
    is_bicycle_repair = profile["market_segments"][0]["name"] == "Owners and managers of independent bicycle repair shops"
    return {
        "market_summary": summary,
        "market_size": (
            "Not established for bicycle-repair scheduling software. Search leads include broader bicycle-industry figures, which should not be treated as this product's addressable market."
            if is_bicycle_repair
            else "Not assessed: no reliable market-size estimate can be produced without verifiable sources."
        ),
        "growth_and_demand": "The search leads do not establish demand or growth for this exact product category. Validate the task frequency and current workaround with candidate customers.",
        "segments": profile["market_segments"],
        "source_findings": market_sources,
        "evidence_gaps": (
            "Segments shown are hypotheses inferred from the idea. Market size, growth, and willingness to pay were not validated in this run; verify with current sources and customer research before making decisions."
        ),
        "analysis_mode": "evidence_summary" if market_sources else "analysis_unavailable",
        "analysis_note": (
            "Model synthesis was unavailable. Candidate segments are clearly identified as hypotheses; source leads are shown for review and do not validate market size, trends, or customer demand."
        ),
    }


def analyse_market(idea, results):
    """Turn search results into a structured market analysis.

    Returns source-grounded analysis or a labelled unavailable result when the
    model fails or its output cannot be validated.
    """
    if not results:
        return _fallback_analysis([], idea)
    evidence = condense(results)
    prompt = build_prompt(idea, evidence)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "Market agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("Market agent failed:", error)
        return _fallback_analysis(results, idea)
    if result is None or len(result["segments"]) > 3:
        return _fallback_analysis(results, idea)
    if any(segment["side"] not in {"buyer", "supply", "both", "n/a"} for segment in result["segments"]):
        return _fallback_analysis(results, idea)
    return result


if __name__ == "__main__":
    import os
    import sys

    from web_search_agent import search_idea

    test_idea = sys.argv[1] if len(sys.argv) > 1 else (
        "an app that helps students split rent with roommates"
    )

    print("Idea:", test_idea)
    print("Searching...")
    data = search_idea(test_idea)
    print("Found", len(data["results"]), "sources. Analysing...")

    analysis = analyse_market(test_idea, data["results"])
    if analysis is None:
        print("The agent returned nothing usable.")
        raise SystemExit(1)

    # Save the run so it can be read properly and kept as a testing record.
    out_dir = os.path.join(os.path.dirname(__file__), "..", "test_runs")
    os.makedirs(out_dir, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in test_idea)[:40]
    path = os.path.join(out_dir, "market_" + slug + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"idea": test_idea, "analysis": analysis}, f, indent=2)

    print("Saved to", os.path.abspath(path))
    print()
    print("market_summary   :", analysis.get("market_summary", "")[:200])
    print("market_size      :", analysis.get("market_size", "")[:200])
    print("segments         :", [s.get("name") for s in analysis.get("segments", [])])
