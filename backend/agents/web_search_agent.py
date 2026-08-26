import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def build_queries(idea):
    """Turn one startup idea into three targeted search queries."""
    return [
        f"{idea} competitors and similar startups",
        f"{idea} market size and industry growth trends",
        f"existing solutions and customer complaints about {idea}",
    ]


def search_idea(idea):
    """Search the web for evidence about a startup idea."""
    queries = build_queries(idea)
    results = []
    summary = None

    for query in queries:
        try:
            response = client.search(query, max_results=5, include_answer=True)
        except Exception as error:
            print("Search failed for:", query, "-", error)
            continue

        if summary is None and response.get("answer"):
            summary = response["answer"]

        for item in response.get("results", []):
            results.append({
                "title": item.get("title") or "Untitled",
                "url": item.get("url") or "",
                "snippet": (item.get("content") or "")[:300],
                "score": item.get("score") or 0,
            })

    # Best result first
    results.sort(key=lambda r: r["score"], reverse=True)

    # Remove duplicate URLs, keeping the highest-scoring copy
    unique = {}
    for result in results:
        if result["url"] and result["url"] not in unique:
            unique[result["url"]] = result

    return {
        "idea": idea,
        "queries": queries,
        "summary": summary,
        "results": list(unique.values()),
    }


if __name__ == "__main__":
    output = search_idea("an app that helps students split rent with roommates")
    print("Queries:", output["queries"])
    print("Summary:", output["summary"])
    print("Results found:", len(output["results"]))
    for r in output["results"][:3]:
        print(round(r["score"], 2), r["title"])