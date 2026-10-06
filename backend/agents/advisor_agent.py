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


def answer_follow_up(question, idea, market, competitors, swot, mvp, gtm, history=None, sources=None):
    """Answer a follow-up from pipeline context, or return None on failure."""
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
    return {
        "answer": (
            "The AI advisor could not produce a reliable response, so I can't "
            "answer this from the supplied validation. Please use the available "
            "report sections and try again later; no unsupported answer or citation "
            "has been generated."
        ),
        "has_sufficient_context": False,
        "missing_context": [
            "A successful advisor response grounded in the supplied analysis is unavailable."
        ],
        "citations": [],
        "analysis_mode": "advisor_unavailable",
        "analysis_note": take_failure() or (
            "No reliable advisor response could be generated from the available context."
        ),
    }