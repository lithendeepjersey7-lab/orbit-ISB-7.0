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
THINKING_BUDGET = 512

# max_retries=0 turns off the client's own hidden retries (default 6, which
# include 429). Retrying is handled by gemini_retry.invoke_with_retry.
llm = ChatGoogleGenerativeAI(
    model=MODEL, thinking_budget=THINKING_BUDGET, max_retries=0
)


def parse_json(text):
    """Parse the model's reply as JSON, tolerating a markdown code fence."""
    return parse_json_response(text, RESPONSE_SCHEMA)


SHAPE = """{
  "target_audience": "",
  "product_summary": "",
  "must_have_features": [
    {"feature": "", "why_important": ""}
  ],
  "should_have_features": [
    {"feature": "", "why_important": ""}
  ],
  "nice_to_have_features": [
    {"feature": "", "why_later": ""}
  ],
  "build_phases": [
    {"phase": "", "features": [""], "exit_criteria": ""}
  ],
  "prioritization_rationale": ""
}"""

RESPONSE_SCHEMA = {
    "target_audience": str,
    "product_summary": str,
    "must_have_features": [{"feature": str, "why_important": str}],
    "should_have_features": [{"feature": str, "why_important": str}],
    "nice_to_have_features": [{"feature": str, "why_later": str}],
    "build_phases": [{"phase": str, "features": [str], "exit_criteria": str}],
    "prioritization_rationale": str,
}

RULES = """RULES:
1. Base recommendations only on the startup idea, customer segments and market
   or competitor gaps provided. Do not invent customer needs or external facts.
2. Focus the first version on the narrowest useful customer segment and one
   core workflow that tests the strongest supported market gap.
3. Keep must-have features to the smallest practical set, normally two to five.
   Include only what is needed to deliver that workflow and learn whether it
   solves the stated customer problem.
4. For every must-have, briefly explain in "why_important" how it serves the
   selected audience or addresses a provided gap.
5. Put useful but nonessential ideas in "nice_to_have_features" and explain
   briefly in "why_later" why each can wait until after the core workflow is
   validated. Do not repeat must-have features in that list.
6. Avoid expanding the first version with payments, integrations, or other
   complex capabilities unless the supplied context makes them essential.
7. Group recommendations into must-have, should-have, and nice-to-have;
   prioritize explicit competitor gaps and the narrowest useful workflow,
   while considering the effort implied by the idea. Explain prioritization
   and order the work into phases with measurable learning/exit criteria.
8. Return ONLY valid JSON in exactly the requested shape, with no commentary
   before or after it."""


def build_prompt(idea, market, competitors, swot=None):
    """Assemble an MVP recommendation prompt from existing analysis results."""
    risk_context = json.dumps(swot, ensure_ascii=True) if swot else "Not supplied."
    return (
        "You are a pragmatic product strategist helping a founder define the "
        "smallest useful first version of a startup.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "MARKET ANALYSIS, INCLUDING CUSTOMER SEGMENTS AND EVIDENCE GAPS:\n"
        + json.dumps(market, ensure_ascii=True) + "\n\n"
        "COMPETITOR ANALYSIS, INCLUDING MARKET GAPS:\n"
        + json.dumps(competitors, ensure_ascii=True) + "\n\n"
        "SWOT AND RISKS:\n" + risk_context + "\n\n"
        "Return ONLY valid JSON in exactly this shape:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def recommend_mvp(idea, market, competitors, swot=None):
    """Recommend a minimal first version, or return None on model/JSON failure."""
    prompt = build_prompt(idea, market, competitors, swot)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "MVP agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("MVP recommendation agent failed:", error)
        return None
    if result is None or not result["must_have_features"] or not result["build_phases"]:
        return None
    if any(not phase["features"] or not phase["exit_criteria"].strip() for phase in result["build_phases"]):
        return None
    return result