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
  "positioning": {
    "statement": "",
    "differentiation": "",
    "evidence_basis": ""
  },
  "early_target_customers": [
    {"segment": "", "why_start_here": "", "validation_signal": ""}
  ],
  "customer_acquisition_channels": [
    {"channel": "", "rationale": "", "low_cost_test": ""}
  ],
  "first_90_days": {
    "days_1_30": [""],
    "days_31_60": [""],
    "days_61_90": [""]
  }
}"""

RESPONSE_SCHEMA = {
  "positioning": {
    "statement": str,
    "differentiation": str,
    "evidence_basis": str,
  },
  "early_target_customers": [{
    "segment": str,
    "why_start_here": str,
    "validation_signal": str,
  }],
  "customer_acquisition_channels": [{
    "channel": str,
    "rationale": str,
    "low_cost_test": str,
  }],
  "first_90_days": {
    "days_1_30": [str],
    "days_31_60": [str],
    "days_61_90": [str],
  },
}

RULES = """RULES:
1. Base the strategy only on the startup idea, customer segments, competitor
   gaps, and any SWOT context supplied. Do not invent market facts, customer
   behavior, partnerships, budgets, conversion rates, or traction.
2. Make strategic inferences explicit by beginning them with exactly
   "Inference (from context):". Keep evidence-supported observations distinct
   from those inferences.
3. Choose a narrow initial audience from the supplied customer segments.
   Explain why it is a sensible starting point using the supplied context.
4. Recommend practical, low-cost channels and tests an early-stage team can
   execute. Do not assume access to a large audience or paid acquisition budget.
5. Make the 90-day actions sequential, specific, and focused on learning and
   validating demand before scaling. Do not promise outcomes.
6. If the context does not support a requested detail, say that it needs
   validation instead of filling the gap with an unsupported claim.
7. Keep each item concise and actionable. Return ONLY valid JSON in exactly
   the requested shape, with no commentary before or after it."""


def build_prompt(idea, market, competitors, swot=None):
    """Assemble a practical GTM prompt from existing analysis outputs."""
    swot_context = (
        json.dumps(swot, ensure_ascii=True)
        if swot
        else "Not supplied; do not infer SWOT findings."
    )
    return (
        "You are a pragmatic go-to-market strategist helping an early-stage "
        "founder plan initial customer discovery and acquisition. Create a "
        "grounded strategy from the supplied context.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "CUSTOMER SEGMENTS FROM MARKET ANALYSIS:\n"
        + json.dumps(market.get("segments", []), ensure_ascii=True)
        + "\n\nCOMPETITOR GAPS:\n"
        + json.dumps(competitors.get("market_gaps", ""), ensure_ascii=True)
        + "\n\nSWOT CONTEXT (OPTIONAL):\n" + swot_context + "\n\n"
        "Return ONLY valid JSON in exactly this shape:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def develop_gtm_strategy(idea, market, competitors, swot=None):
    """Create a structured GTM strategy, or return None on model/JSON failure."""
    prompt = build_prompt(idea, market, competitors, swot)
    try:
        reply = llm.invoke(prompt)
        response_text = getattr(reply, "text", None)
    except Exception as error:
        print("GTM strategy agent failed:", error)
        return None
    result = parse_json(response_text)
    if result is None:
        return None
    if not result["early_target_customers"] or not result["customer_acquisition_channels"]:
        return None
    if any(not result["first_90_days"][period] for period in ("days_1_30", "days_31_60", "days_61_90")):
        return None
    return result