import time
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

from web_search_agent import search_idea
from market_agent import analyse_market, build_prompt, condense
from competitor_agent import analyse_competitors
from langchain_google_genai import ChatGoogleGenerativeAI

IDEA = "an app that helps students split rent with roommates"


def timed(label, fn):
    t = time.perf_counter()
    out = fn()
    secs = round(time.perf_counter() - t, 1)
    print("%-34s %6.1f s" % (label, secs))
    return out, secs


print("=" * 52)
data, t_search = timed("1. web search (Milestone 1)", lambda: search_idea(IDEA))
_, t_market = timed("2. market agent alone", lambda: analyse_market(IDEA, data["results"]))
_, t_comp = timed("3. competitor agent alone", lambda: analyse_competitors(IDEA, data["results"]))
print("-" * 52)
print("%-34s %6.1f s" % ("sequential total would be", t_search + t_market + t_comp))
print("=" * 52)

# Does turning off the model's thinking budget help?
prompt = build_prompt(IDEA, condense(data["results"]))
print("\nSame market prompt, thinking turned off:")
try:
    fast = ChatGoogleGenerativeAI(model="gemini-3.6-flash", thinking_budget=0)
    _, t_fast = timed("4. market prompt, thinking_budget=0", lambda: fast.invoke(prompt).text)
    print("\n   speed-up vs step 2: %.1fx" % (t_market / max(t_fast, 0.1)))
except TypeError as e:
    print("   thinking_budget not supported here:", e)
except Exception as e:
    print("   call failed:", type(e).__name__, str(e)[:160])
