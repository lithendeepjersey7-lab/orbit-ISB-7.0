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
    model=MODEL, thinking_budget=THINKING_BUDGET, max_retries=0,
    request_timeout=15,
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


def _fallback_recommendation(idea, market, competitors):
    """Create a transparent pilot plan when Gemini cannot generate one."""
    profile = fallback_profile(idea, market)
    segments = market.get("segments") or []
    primary_segment = next(
        (
            segment.get("name", "").strip()
            for segment in segments
            if isinstance(segment, dict) and segment.get("name", "").strip()
        ),
        profile["audience"],
    )
    market_gap = str(competitors.get("market_gaps") or "").strip()
    core_features = [feature for feature, _ in profile["must"]]
    if core_features[0] == "A minimal end-to-end core workflow":
        core_features[0] += " to " + profile["workflow_text"]
    core_rationales = [why for _, why in profile["must"]]
    pilot_feature = core_features[-1]
    onboarding_feature = profile["should"][0]
    extension_feature = profile["later"][0]

    return {
        "target_audience": primary_segment,
        "product_summary": idea.strip(),
        "must_have_features": [
            {"feature": feature, "why_important": rationale}
            for feature, rationale in zip(core_features, core_rationales)
        ],
        "should_have_features": [
            {
                "feature": onboarding_feature,
                "why_important": profile["should"][1],
            },
        ],
        "nice_to_have_features": [
            {
                "feature": extension_feature,
                "why_later": profile["later"][1],
            },
        ],
        "build_phases": [
            {
                "phase": "Phase 1 - Validate the core workflow",
                "features": core_features,
                "exit_criteria": "Target users can complete the core task in a guided pilot and provide specific feedback.",
            },
            {
                "phase": "Phase 2 - Improve the pilot experience",
                "features": [onboarding_feature],
                "exit_criteria": "Pilot users can start and complete the workflow with less founder assistance.",
            },
            {
                "phase": "Phase 3 - Expand selectively",
                "features": [extension_feature],
                "exit_criteria": "Pilot users repeatedly request a deferred capability and can explain its value.",
            },
        ],
        "prioritization_rationale": (
            "This idea-specific heuristic draft prioritizes a testable workflow and low-cost learning. "
            + (
                "The competitor analysis identifies this gap to investigate: " + market_gap
                if market_gap
                else "No competitor gap was available, so differentiation must be validated in customer interviews."
            )
            + " Defer integrations and automation until pilot evidence supports them."
        ),
        "analysis_mode": "conservative_fallback",
        "analysis_note": (
            "Gemini was unavailable or returned an unusable response, so this "
            "is a conservative pilot plan based only on the idea and supplied "
            "analysis; validate scope with target users."
        ),
    }


def recommend_mvp(idea, market, competitors, swot=None):
    """Recommend a minimal first version, or return None on model/JSON failure."""
    if (
        market.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}
        and competitors.get("analysis_mode") in {"analysis_unavailable", "evidence_summary"}
    ):
        return _fallback_recommendation(idea, market, competitors)
    prompt = build_prompt(idea, market, competitors, swot)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "MVP agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("MVP recommendation agent failed:", error)
        return _fallback_recommendation(idea, market, competitors)
    if result is None or not result["must_have_features"] or not result["build_phases"]:
        return _fallback_recommendation(idea, market, competitors)
    if any(not phase["features"] or not phase["exit_criteria"].strip() for phase in result["build_phases"]):
        return _fallback_recommendation(idea, market, competitors)
    return result