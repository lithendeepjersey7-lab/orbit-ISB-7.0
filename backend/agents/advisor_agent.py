import json

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from response_validation import invoke_with_json_repair, parse_json_response
    from gemini_retry import invoke_with_retry, take_failure
except ImportError:
    from agents.response_validation import invoke_with_json_repair, parse_json_response
    from agents.gemini_retry import invoke_with_retry, take_failure

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
    result = parse_json_response(text, RESPONSE_SCHEMA)
    if result is not None and not result["has_sufficient_context"] and not result["missing_context"]:
        return None
    return result


SHAPE = """{
  "answer": "",
  "has_sufficient_context": true,
  "missing_context": [],
  "citations": [{"source_id": "", "reason": ""}]
}"""

RESPONSE_SCHEMA = {
    "answer": str,
    "has_sufficient_context": bool,
    "missing_context": [str],
    "citations": [{"source_id": str, "reason": str}],
}

RULES = """RULES:
1. Answer only from the startup idea and the supplied analysis context. Do
   not introduce outside facts, assumptions, forecasts, or recommendations
   that are unsupported by that context.
2. If the context does not contain enough information to answer reliably,
   say so clearly in "answer", set "has_sufficient_context" to false, and
   list the missing information in "missing_context". Do not guess.
3. If the context is sufficient, set "has_sufficient_context" to true and
   return an actionable, concise answer. Use "missing_context": [] unless a
   material part of the question remains unanswered.
4. Distinguish a direct finding from an inference. Label an inference with
   exactly "Inference (from provided context):".
5. Cite every factual answer using source_id values from the permitted source
   list. Never invent IDs or URLs. Cite the relevant report section or live
   search result; if nothing supports a claim, state that limitation.
6. Use the conversation history to resolve follow-ups, but do not treat earlier
   assistant statements as evidence unless they are supported by the report.
7. Return ONLY valid JSON in exactly the requested shape, with no commentary
   before or after it."""


def build_prompt(question, idea, market, competitors, swot, mvp, gtm, history=None, sources=None):
    """Assemble an advisor prompt from the complete pipeline analysis."""
    context = {
        "market": market,
        "competitors": competitors,
        "swot": swot,
        "mvp": mvp,
        "gtm": gtm,
        "conversation_history": history or [],
        "permitted_sources": sources or [],
    }
    return (
        "You are a concise startup advisor answering a founder's follow-up "
        "question using only the analysis provided below.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "FOLLOW-UP QUESTION:\n" + question + "\n\n"
        "STARTUP ANALYSIS CONTEXT:\n"
        + json.dumps(context, ensure_ascii=True)
        + "\n\nReturn ONLY valid JSON in exactly this shape:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def _fallback_advisor_answer(question, idea, market, competitors, swot, mvp, gtm, sources):
    """Answer common follow-ups from report fields without inventing evidence."""
    query = (question or "").lower()
    sections = {
        "market": market or {},
        "competitors": competitors or {},
        "swot": swot or {},
        "mvp": mvp or {},
        "gtm": gtm or {},
    }
    permitted = {
        item.get("id"): item
        for item in (sources or [])
        if isinstance(item, dict) and item.get("id")
    }

    def text(value):
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            return "; ".join(
                "{}: {}".format(key.replace("_", " "), text(item))
                for key, item in value.items()
                if item not in (None, "", [], {})
            )
        if isinstance(value, (list, tuple)):
            return "; ".join(filter(None, (text(item) for item in value)))
        return ""

    def values(section, key):
        value = sections[section].get(key, [])
        if not isinstance(value, list):
            value = [value]
        return [text(item) for item in value if text(item)]

    def cite(section, reason):
        source_id = "report:" + section
        if source_id in permitted:
            return [{"source_id": source_id, "reason": reason}]
        return []

    answer = ""
    citations = []
    missing = []
    sufficient = True

    if any(word in query for word in ("risk", "threat", "weakness", "swot", "mitigat")):
        risks = sections["swot"].get("risks", [])
        if isinstance(risks, list) and risks:
            first = risks[0]
            answer = "The report’s top listed risk is {} (likelihood: {}, impact: {}). Mitigation: {}.".format(
                text(first.get("risk")),
                text(first.get("likelihood")) or "not rated",
                text(first.get("impact")) or "not rated",
                text(first.get("mitigation")) or "review with target users",
            )
            citations = cite("swot", "risk and mitigation listed in the report")
        else:
            answer = "The report does not contain a validated risk assessment for this question. Interview target users and test the core workflow before treating any risk rating as established."
            missing = ["A completed, evidence-grounded SWOT and risk assessment."]
            sufficient = False
    elif any(word in query for word in ("mvp", "feature", "build", "product")):
        features = values("mvp", "must_have_features")
        if features:
            rationale = text(sections["mvp"].get("prioritization_rationale"))
            answer = "Start with these must-have MVP items: {}.".format("; ".join(features[:3]))
            if rationale:
                answer += " Prioritization: " + rationale
            citations = cite("mvp", "must-have features and prioritization rationale")
        else:
            answer = "The report does not include a usable must-have feature list yet. Start by validating the smallest end-to-end workflow described in the idea: {}.".format(text(idea))
            missing = ["A completed MVP recommendation grounded in market and competitor evidence."]
            sufficient = False
        if sections["mvp"].get("analysis_mode") == "conservative_fallback":
            answer += " This is a conservative pilot draft, not a validated product requirement."
    elif any(word in query for word in ("first 100", "users", "customer", "segment", "launch", "channel", "market")):
        gtm = sections["gtm"]
        customers = gtm.get("early_target_customers", [])
        plan = (gtm.get("first_100_users") or {}).get("plan", [])
        segments = values("market", "segments")
        if customers or plan:
            answer = "The report suggests testing {}. First-user steps: {}.".format(
                text(customers[0].get("segment")) if isinstance(customers, list) and customers else "one narrow customer segment",
                text(plan[:3]) if isinstance(plan, list) and plan else "use direct discovery, invite qualified people to a small pilot, and ask engaged users for referrals",
            )
            citations = cite("gtm", "early customer and first-user plan from the report")
        elif segments:
            answer = "The market section lists these candidate segments: {}. Treat them as hypotheses until target-customer interviews validate the problem and willingness to test.".format(text(segments[:3]))
            citations = cite("market", "candidate segments listed in the report")
        else:
            answer = "The report does not verify a target segment or acquisition channel. Start with customer interviews around the problem described in the idea, then recruit a small manually supported pilot."
            missing = ["Validated customer segments and acquisition channels."]
            sufficient = False
    elif any(word in query for word in ("price", "pricing", "revenue", "monetiz", "charge", "pay")):
        monetization = sections["gtm"].get("monetization", {})
        if isinstance(monetization, dict) and text(monetization):
            answer = "The report’s monetization view: {}. Treat its pricing as a hypothesis and test it with a concrete pilot or paid-trial offer; the report does not establish willingness to pay.".format(text(monetization))
            citations = cite("gtm", "monetization and pricing hypothesis from the report")
        else:
            answer = "No pricing or willingness-to-pay evidence is available in this report. Test who would pay and for what outcome through customer interviews and a concrete pilot offer."
            missing = ["Pricing and willingness-to-pay evidence."]
            sufficient = False
    elif any(word in query for word in ("competitor", "competition", "differentiat", "alternative", "gap")):
        summary = text(sections["competitors"].get("landscape_summary"))
        gap = text(sections["competitors"].get("market_gaps"))
        if summary:
            answer = summary
            if gap:
                answer += " " + gap
            if sections["competitors"].get("analysis_mode") == "evidence_summary":
                answer += " These are search leads, not verified competitor findings."
            citations = cite("competitors", "competitor landscape and gap notes from the report")
        else:
            answer = "The report does not confirm specific competitors or differentiation. Review the linked search leads and verify alternatives before making a competitive claim."
            missing = ["Verified direct and indirect competitor analysis."]
            sufficient = False
    elif sections["market"].get("market_summary"):
        answer = text(sections["market"]["market_summary"])
        if sections["market"].get("analysis_mode") == "evidence_summary":
            answer += " The linked items are search leads only, not verified market findings."
        citations = cite("market", "market summary from the report")
    else:
        answer = "I can only use information present in this validation report. The idea is: {}. Ask about the listed risks, MVP features, launch plan, pricing hypothesis, or market evidence.".format(text(idea))
        missing = ["A completed report section that directly answers this question."]
        sufficient = False

    citations = [
        {"source_id": item["source_id"], "reason": item["reason"]}
        for item in citations
        if item["source_id"] in permitted
    ]
    return {
        "answer": answer,
        "has_sufficient_context": sufficient,
        "missing_context": missing,
        "citations": citations,
        "analysis_mode": "conservative_fallback",
        "analysis_note": "Gemini is unavailable. This response uses only the supplied validation report and is not a new live analysis.",
    }


def answer_follow_up(question, idea, market, competitors, swot, mvp, gtm, history=None, sources=None):
    """Answer from report context, using a transparent local fallback on failure."""
    prompt = build_prompt(question, idea, market, competitors, swot, mvp, gtm, history, sources)
    try:
        result = invoke_with_json_repair(
            llm, prompt, "Advisor agent", RESPONSE_SCHEMA, invoke_with_retry
        )
    except Exception as error:
        print("Startup advisor failed:", error)
        result = None
    answer = parse_json(json.dumps(result)) if result is not None else None
    if answer is not None:
        return answer
    take_failure()
    return _fallback_advisor_answer(
        question, idea, market, competitors, swot, mvp, gtm, sources
    )