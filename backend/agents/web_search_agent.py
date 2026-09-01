import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def build_queries(idea):
    """Turn one startup idea into three targeted searches, each with a label."""
    return [
        ("Competitors", f"{idea} competitors and similar startups"),
        ("Market size & trends", f"{idea} market size and industry growth trends"),
        ("Customer demand", f"existing solutions and customer complaints about {idea}"),
    ]


def run_one_search(angle):
    """Run one Tavily search. Returns (category, query, response) or None on failure."""
    category, query = angle
    try:
        response = client.search(query, max_results=5, include_answer=True)
    except Exception as error:
        print("Search failed for:", query, "-", error)
        return category, query, None
    return category, query, response


def site_of(url):
    """Domain name of a URL, without the leading www."""
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def search_idea(idea):
    """Search the web for evidence about a startup idea."""
    started = time.perf_counter()
    angles = build_queries(idea)

    # The three searches do not depend on each other, so run them at the same
    # time instead of one after another.
    with ThreadPoolExecutor(max_workers=3) as pool:
        searches = list(pool.map(run_one_search, angles))

    results = []
    summary = None
    searches_succeeded = 0

    for category, query, response in searches:
        if response is None:
            continue
        searches_succeeded += 1

        if summary is None and response.get("answer"):
            summary = response["answer"]

        for item in response.get("results", []):
            results.append({
                "title": item.get("title") or "Untitled",
                "url": item.get("url") or "",
                "snippet": (item.get("content") or "")[:300],
                "score": item.get("score") or 0,
                "category": category,
            })

    raw_count = len(results)

    # Best result first
    results.sort(key=lambda r: r["score"], reverse=True)

    # Remove duplicate URLs, keeping the highest-scoring copy
    unique = {}
    for result in results:
        if result["url"] and result["url"] not in unique:
            unique[result["url"]] = result
    results = list(unique.values())

    # How many sources ended up in each category
    counts = {category: 0 for category, _ in angles}
    for result in results:
        counts[result["category"]] += 1

    elapsed = round(time.perf_counter() - started, 1)

    return {
        "idea": idea,
        "queries": [query for _, query in angles],
        "categories": [category for category, _ in angles],
        "counts": counts,
        "summary": summary,
        "results": results,
        "elapsed_seconds": elapsed,
        # A report of what the agent actually did on this run
        "stats": {
            "searches_run": len(angles),
            "searches_succeeded": searches_succeeded,
            "raw_results": raw_count,
            "duplicates_removed": raw_count - len(results),
            "shown": len(results),
            "distinct_sites": len({site_of(r["url"]) for r in results if r["url"]}),
            "elapsed_seconds": elapsed,
        },
    }


if __name__ == "__main__":
    output = search_idea("an app that helps students split rent with roommates")
    print("Stats:", output["stats"])
    print("Counts:", output["counts"])