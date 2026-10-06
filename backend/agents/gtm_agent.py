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
  "first_100_users": {
    "plan": [""],
    "success_signal": ""
  },
  "monetization": {
    "model": "",
    "pricing_hypothesis": "",
    "validation_test": ""
  },
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
  "first_100_users": {"plan": [str], "success_signal": str},
  "monetization": {
    "model": str,
    "pricing_hypothesis": str,
    "validation_test": str,
  },
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
6. Give a practical, low-cost plan to recruit the first 100 users and state
   what signal would count as meaningful validation. Include a monetization
   model and clearly label any pricing as a hypothesis to test.
7. If the context does not support a requested detail, say that it needs
   validation instead of filling the gap with an unsupported claim.
8. Keep each item concise and actionable. Return ONLY valid JSON in exactly
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


def _fallback_strategy(idea, market):
    profile = fallback_profile(idea, market)
    segments = market.get("segments") or []
    segment = next(
        (
            item.get("name", "").strip()
            for item in segments
            if isinstance(item, dict) and item.get("name", "").strip()
        ),
        profile["audience"],
    )
    return {
        "positioning": {
            "statement": "For " + segment + ", test a simple promise: " + profile["workflow_text"] + ".",
            "differentiation": "No differentiation claim is supported until competitor evidence and customer feedback are available.",
            "evidence_basis": "Fallback based on the submitted idea only; market and competitor evidence may be incomplete.",
        },
        "early_target_customers": [{
            "segment": segment,
            "why_start_here": "Treat this only as a discovery starting point; the segment has not been validated.",
            "validation_signal": "Several target users independently describe the problem and agree to test a prototype.",
        }],
        "customer_acquisition_channels": [{
            "channel": profile["channels"][0],
            "rationale": profile["channels"][1],
            "low_cost_test": "Recruit 10 people matching the candidate segment; document their current workaround and invite qualified participants to a guided pilot.",
        }],
        "first_100_users": {
            "plan": [
                "Interview 10 candidate users in " + segment + " and verify they experience the target problem.",
                "Recruit the first 10 qualified pilot users through " + profile["channels"][0].lower() + ".",
                "Iterate with pilot feedback, then request referrals to reach 100 interested users; track activation and repeat use without assuming conversion.",
            ],
            "success_signal": "A repeatable source of qualified pilot users and evidence that users return to complete the core task.",
        },
        "monetization": {
            "model": "Not selected; validate who pays and what outcome they value before choosing a model.",
            "pricing_hypothesis": "No price point is supported by the available evidence; test willingness to pay through customer interviews and a clearly described pilot offer.",
            "validation_test": "Compare stated interest with concrete commitments to a pilot or paid trial; do not treat stated intent alone as proof.",
        },
        "first_90_days": {
            "days_1_30": [
                "Interview candidate users and document their current workflow and alternatives.",
                "Select one problem and define a measurable pilot goal for " + profile["workflow_text"] + ".",
            ],
            "days_31_60": [
                "Run a small, manually supported prototype pilot.",
                "Measure task completion, repeat use, and specific reasons users stop.",
            ],
            "days_61_90": [
                "Revise the product and positioning using observed pilot evidence.",
                "Test a payment commitment before investing in scalable acquisition.",
            ],
        },
        "analysis_mode": "conservative_fallback",
        "analysis_note": (
            "Gemini was unavailable or returned an unusable response. This is "
            "an idea-specific heuristic discovery draft, not a validated GTM strategy; validate "
            "segments, channels, differentiation, and pricing with customers."
        ),
    }


def develop_gtm_strategy(idea, market, competitors, swot=None):
    """Create a structured GTM strategy, or return None on model/JSON failure."""
    if (
        market.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}
        and competitors.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}
        and (not swot or swot.get("analysis_mode") == "conservative_fallback")
    ):
        return _fallback_strategy(idea, market)
    prompt = build_prompt(idea, market, competitors, swot)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "GTM agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("GTM strategy agent failed:", error)
        return _fallback_strategy(idea, market)
    if result is None:
        return _fallback_strategy(idea, market)
    if not result["early_target_customers"] or not result["customer_acquisition_channels"]:
        return _fallback_strategy(idea, market)
    if not result["first_100_users"]["plan"] or not result["first_100_users"]["success_signal"].strip():
        return _fallback_strategy(idea, market)
    if not all(result["monetization"][key].strip() for key in ("model", "pricing_hypothesis", "validation_test")):
        return _fallback_strategy(idea, market)
    if any(not result["first_90_days"][period] for period in ("days_1_30", "days_31_60", "days_61_90")):
        return _fallback_strategy(idea, market)
    return result