import os
import time
from concurrent.futures import ThreadPoolExecutor

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

    for category, query, response in searches:
        if response is None:
            continue

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

    return {
        "idea": idea,
        "queries": [query for _, query in angles],
        "categories": [category for category, _ in angles],
        "counts": counts,
        "summary": summary,
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 1),
    }


if __name__ == "__main__":
    output = search_idea("an app that helps students split rent with roommates")
    print("Took:", output["elapsed_seconds"], "seconds")
    print("Counts:", output["counts"])
    for r in output["results"][:5]:
        print(f"  [{r['category']}] {round(r['score'], 2)} {r['title']}")