import json

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from response_validation import parse_json_response
    from gemini_retry import invoke_with_retry
except ImportError:
    from agents.response_validation import parse_json_response
    from agents.gemini_retry import invoke_with_retry

load_dotenv()

MODEL = "gemini-3.7-flash"

# Keep the same reasoning budget as the Milestone 2 analysis agents so this
# synthesis agent uses the project's established Gemini configuration.
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
  "strengths": [""],
  "weaknesses": [""],
  "opportunities": [""],
  "threats": [""],
  "risks": [
    {
      "category": "market | product | technical | financial | regulatory | operational",
      "risk": "",
      "likelihood": "low | medium | high",
      "impact": "low | medium | high",
      "mitigation": ""
    }
  ]
}"""

RESPONSE_SCHEMA = {
    "strengths": [str],
    "weaknesses": [str],
    "opportunities": [str],
    "threats": [str],
    "risks": [{
        "category": str,
        "risk": str,
        "likelihood": str,
        "impact": str,
        "mitigation": str,
    }],
}

RULES = """RULES:
1. Use only the startup idea and the supplied market and competitor context.
   Do not introduce external facts, statistics, companies, regulations or
   customer claims that are not present in that context.
2. Return approximately three to five concise items in each SWOT category. Do not
   pad a category with generic statements when the context does not support
   them; return fewer items instead.
3. Separate evidence-supported observations from reasonable strategic
   inferences. Begin an inference with exactly "Inference (from context):".
   Do not present an inference as an established fact.
4. Strengths and weaknesses must describe the startup idea's apparent position
   based on the supplied context, not the founder personally.
5. Opportunities should be actionable openings suggested by customer needs,
   market gaps or competitor weaknesses in the context.
6. Threats should describe external competitive or market pressures supported
   by the context. Return practical risks in the "risks" array; choose the
   closest category, assess likelihood and impact as low/medium/high, and
   provide a concrete mitigation. Do not inflate ratings without evidence.
7. Keep every item to one or two concise sentences and return ONLY valid JSON,
   with no commentary before or after it."""


def build_prompt(idea, market, competitors):
    """Assemble the SWOT prompt from the existing analysis outputs."""
    return (
        "You are a startup strategy analyst helping a founder evaluate an idea.\n"
        "Create a concise SWOT and execution-risk analysis from the provided\n"
        "market and competitor context.\n\n"
        "STARTUP IDEA:\n" + idea + "\n\n"
        "MARKET CONTEXT:\n" + json.dumps(market, ensure_ascii=True) + "\n\n"
        "COMPETITOR CONTEXT:\n" + json.dumps(competitors, ensure_ascii=True) + "\n\n"
        "Return ONLY valid JSON in exactly this shape:\n\n"
        + SHAPE + "\n\n" + RULES
    )


def analyse_swot(idea, market, competitors):
    """Turn market and competitor analyses into structured SWOT results.

    Returns a dict on success, or None if the model failed or returned
    something that was not valid JSON. The caller decides what to do about it.
    """
    prompt = build_prompt(idea, market, competitors)
    try:
        reply = invoke_with_retry(llm, prompt, "SWOT agent")
        response_text = getattr(reply, "text", None)
    except Exception as error:
        print("SWOT agent failed:", error)
        return None
    result = parse_json(response_text)
    if result is None:
        return None
    categories = {"market", "product", "technical", "financial", "regulatory", "operational"}
    levels = {"low", "medium", "high"}
    if any(
        risk["category"] not in categories
        or risk["likelihood"] not in levels
        or risk["impact"] not in levels
        or not risk["risk"].strip()
        or not risk["mitigation"].strip()
        for risk in result["risks"]
    ):
        return None
    return result
