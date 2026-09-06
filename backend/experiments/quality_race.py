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
print("Fetching search results once...")
results = search_idea(IDEA)["results"]
prompt = ca.build_prompt(IDEA, ca.condense(results))
print()

CANDIDATES = [
    ("gemini-3.6-flash", {"thinking_budget": 128}),
    ("gemini-3.6-flash", {"thinking_budget": 512}),
    ("gemini-3.6-flash", {"thinking_budget": 1024}),
    ("gemini-3.7-flash", {}),
    ("gemini-3.7-flash", {"thinking_budget": 512}),
]

for model, opts in CANDIDATES:
    label = model + " " + (", ".join("%s=%s" % kv for kv in opts.items()) or "default")
    try:
        llm = ChatGoogleGenerativeAI(model=model, **opts)
        t = time.perf_counter()
        parsed = ca.parse_json(llm.invoke(prompt).text)
        secs = time.perf_counter() - t
        if not parsed:
            print("%-42s %5.1fs   BAD JSON" % (label, secs)); continue
        comps = parsed.get("competitors", [])
        n_direct = sum(1 for c in comps if c.get("type") == "direct")
        print("%-42s %5.1fs   %d found, %d direct / %d indirect" %
              (label, secs, len(comps), n_direct, len(comps) - n_direct))
        for c in comps:
            print("        %-10s %s" % (c.get("type"), c.get("name")))
    except Exception as e:
        print("%-42s   ERROR %s" % (label, str(e)[:70]))
    print()
