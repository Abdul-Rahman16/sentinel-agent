import httpx

from core.config import settings


def web_search(query: str, max_results: int = 5) -> dict:
    """Calls Tavily's search API. Returns a dict with results or an error —
    never raises, since a tool failure should be handled by the agent loop,
    not crash the whole run."""
    if not settings.tavily_api_key:
        return {"error": "TAVILY_API_KEY not configured"}

    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "results": [
                {"title": r["title"], "url": r["url"], "content": r["content"]}
                for r in data.get("results", [])
            ]
        }
    except Exception as e:
        return {"error": str(e)}