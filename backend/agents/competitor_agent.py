import json

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from response_validation import invoke_with_json_repair, parse_json_response
    from gemini_retry import invoke_with_retry
except ImportError:
    from agents.response_validation import invoke_with_json_repair, parse_json_response
    from agents.gemini_retry import invoke_with_retry

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
    model=MODEL, thinking_budget=THINKING_BUDGET, max_retries=0
)


def condense(results, limit=12):
    """Squash the search agent's results into compact text for the prompt."""
    lines = []
    for item in results[:limit]:
        lines.append("[" + item["category"] + "] " + item["title"] + " - " + item["snippet"])
    return "\n".join(lines)


def parse_json(text):
    """Parse the model's reply as JSON, tolerating a markdown code fence."""
    return parse_json_response(text, RESPONSE_SCHEMA)


SHAPE = """{
  "landscape_summary": "",
  "competitors": [
    {
      "name": "",
      "type": "",
      "why_this_type": "",
      "offering": "",
      "positioning": "",
      "target_customer": "",
      "weak_spots": ""
    }
  ],
  "market_gaps": ""
}"""

RESPONSE_SCHEMA = {
    "landscape_summary": str,
    "competitors": [{
        "name": str,
        "type": str,
        "why_this_type": str,
        "offering": str,
        "positioning": str,
        "target_customer": str,
        "weak_spots": str,
    }],
    "market_gaps": str,
}

RULES = """RULES:
1. Ground every claim in the search results above. Say what the sources
   actually show, not what you assume about these companies.
2. If the search results do not cover something, say so plainly in that field,
   then add your estimate as a new sentence beginning exactly with
   "Estimate (not from sources):". Never present an estimate as if it came
   from the search results.
3. Never describe what documents the sources are. Do not write sentences like
   "the search results reference a comparison article". Give the finding.
4. Return at most six competitors, and only ones the evidence actually
   supports. Never invent a competitor to fill the list. Returning three real
   ones is better than six with three guesses.
5. "type" must be exactly "direct" or "indirect". "why_this_type" is one line
   explaining the classification - a direct competitor solves the same problem
   for the same customer, an indirect one solves it differently or for an
   adjacent customer.
6. Many search results are articles such as "10 Best Rent Splitting Apps".
   Those are sources, not competitors. Extract the products named inside them,
   and never list a blog, publisher or article as a competitor.
7. Keep "offering", "positioning" and "target_customer" to one or two lines
   each, short enough to compare side by side in a table.
8. "weak_spots" is where that specific competitor is weak, missing features,
   or leaving users underserved - taken from complaints and reviews in the
   sources where they exist.
9. "market_gaps" is the overall list of needs that no competitor above serves.
   This is what the founder acts on, so make it specific."""


def build_prompt(idea, evidence):
    """Assemble the full prompt. Plain concatenation so it stays easy to edit."""
    return (
        "You are a competitive analyst helping a founder validate a startup\n"
        "idea. Below are real web search results gathered for this idea. Read\n"
        "them and map the competitive landscape.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "WEB SEARCH RESULTS:\n" + evidence + "\n\n"
        "Return ONLY valid JSON, with no commentary before or after it, in\n"
        "exactly this shape. Repeat the competitor object once per competitor:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def _fallback_analysis():
    return {
        "landscape_summary": "A source-grounded competitor analysis is unavailable for this validation run.",
        "competitors": [],
        "market_gaps": (
            "No competitor gap was validated from this run. Identify direct and "
            "indirect alternatives and validate unmet needs before claiming "
            "differentiation; this result does not establish that competitors "
            "or market gaps are absent."
        ),
        "analysis_mode": "analysis_unavailable",
        "analysis_note": (
            "The competitor analyst could not produce a source-grounded result. "
            "No companies or competitor claims have been invented."
        ),
    }


def analyse_competitors(idea, results):
    """Map the competitive landscape from search results.

    Returns source-grounded analysis or a labelled unavailable result when the
    model fails or its output cannot be validated.
    """
    if not results:
        return _fallback_analysis()
    evidence = condense(results)
    prompt = build_prompt(idea, evidence)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "Competitor agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("Competitor agent failed:", error)
        return _fallback_analysis()
    if result is None or len(result["competitors"]) > 6:
        return _fallback_analysis()
    if any(competitor["type"] not in {"direct", "indirect"} for competitor in result["competitors"]):
        return _fallback_analysis()
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

    analysis = analyse_competitors(test_idea, data["results"])
    if analysis is None:
        print("The agent returned nothing usable.")
        raise SystemExit(1)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "test_runs")
    os.makedirs(out_dir, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in test_idea)[:40]
    path = os.path.join(out_dir, "competitor_" + slug + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"idea": test_idea, "analysis": analysis}, f, indent=2)

    print("Saved to", os.path.abspath(path))
    print()
    for c in analysis.get("competitors", []):
        print("  %-26s %-9s %s" % (c.get("name"), c.get("type"), c.get("offering", "")[:70]))
    print()
    print("market_gaps:", analysis.get("market_gaps", "")[:250])
