import time, warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

from web_search_agent import search_idea
import competitor_agent as ca
from langchain_google_genai import ChatGoogleGenerativeAI

IDEA = "an app that helps students split rent with roommates"
print("Fetching search results once, to reuse for every test...")
results = search_idea(IDEA)["results"]
prompt = ca.build_prompt(IDEA, ca.condense(results))
print("prompt is", len(prompt), "characters\n")

CANDIDATES = [
    ("gemini-3.6-flash", {}),
    ("gemini-3.7-flash", {}),
    ("gemini-3.8-flash", {}),
    ("gemini-3.6-flash", {"thinking_budget": 128}),
    ("gemini-3.6-flash", {"thinking_budget": -1}),
]

print("%-20s %-22s %8s %8s  %s" % ("MODEL", "OPTIONS", "SECONDS", "CHARS", "PARSED?"))
print("-" * 76)
for model, opts in CANDIDATES:
    label = ", ".join("%s=%s" % kv for kv in opts.items()) or "default"
    try:
        llm = ChatGoogleGenerativeAI(model=model, **opts)
        t = time.perf_counter()
        text = llm.invoke(prompt).text
        secs = time.perf_counter() - t
        parsed = ca.parse_json(text)
        ok = "yes (%d competitors)" % len(parsed.get("competitors", [])) if parsed else "NO - bad JSON"
        print("%-20s %-22s %8.1f %8d  %s" % (model, label, secs, len(text), ok))
    except Exception as e:
        print("%-20s %-22s %8s %8s  %s" % (model, label, "-", "-", type(e).__name__ + ": " + str(e)[:60]))
