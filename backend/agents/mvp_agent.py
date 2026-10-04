import json

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from response_validation import parse_json_response
except ImportError:
    from agents.response_validation import parse_json_response

load_dotenv()

MODEL = "gemini-3.7-flash"
THINKING_BUDGET = 512

llm = ChatGoogleGenerativeAI(model=MODEL, thinking_budget=THINKING_BUDGET)


def parse_json(text):
    """Parse the model's reply as JSON, tolerating a markdown code fence."""
    return parse_json_response(text, RESPONSE_SCHEMA)


SHAPE = """{
  "target_audience": "",
  "product_summary": "",
  "must_have_features": [
    {"feature": "", "why_important": ""}
  ],
  "nice_to_have_features": [
    {"feature": "", "why_later": ""}
  ]
}"""

RESPONSE_SCHEMA = {
    "target_audience": str,
    "product_summary": str,
    "must_have_features": [{"feature": str, "why_important": str}],
    "nice_to_have_features": [{"feature": str, "why_later": str}],
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
7. Return ONLY valid JSON in exactly the requested shape, with no commentary
   before or after it."""


def build_prompt(idea, market, competitors):
    """Assemble an MVP recommendation prompt from existing analysis results."""
    return (
        "You are a pragmatic product strategist helping a founder define the "
        "smallest useful first version of a startup.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "MARKET ANALYSIS, INCLUDING CUSTOMER SEGMENTS AND EVIDENCE GAPS:\n"
        + json.dumps(market, ensure_ascii=True) + "\n\n"
        "COMPETITOR ANALYSIS, INCLUDING MARKET GAPS:\n"
        + json.dumps(competitors, ensure_ascii=True) + "\n\n"
        "Return ONLY valid JSON in exactly this shape:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def recommend_mvp(idea, market, competitors):
    """Recommend a minimal first version, or return None on model/JSON failure."""
    prompt = build_prompt(idea, market, competitors)
    try:
        reply = llm.invoke(prompt)
        response_text = getattr(reply, "text", None)
    except Exception as error:
        print("MVP recommendation agent failed:", error)
        return None
    result = parse_json(response_text)
    if result is None or not result["must_have_features"]:
        return None
    return result