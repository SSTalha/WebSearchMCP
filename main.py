import os
import logging, sys
from dotenv import load_dotenv
from typing import Any, Dict
import requests

from mcp.server.fastmcp import FastMCP

load_dotenv()

LOG = logging.getLogger("web_search_mcp")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# initialize server (stateless_http recommended for simple deployments)
mcp = FastMCP("web-search-tool", stateless_http=True)


@mcp.tool()
def web_search(query: str, country: str = None , max_results: int = 5, provider: str = "serper") -> Dict[str, Any]:
    """
    Search the web using Tavily or Serper.
    Args:
        query: query string
        country: string (Alpha 2 codes e.g : "US" , "HK" etc)
        max_results: results limit
        provider: 'tavily' or 'serper'
    Returns:
        dict (parsed JSON from provider)
    """
    provider_lower = provider.lower()
    LOG.info("web_search called: provider=%s query=%s", provider_lower, query)

    if provider_lower == "tavily":
        if not TAVILY_API_KEY:
            return {"error": "Missing TAVILY_API_KEY env var"}
        url = "https://api.tavily.com/search"
        headers = {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}
        payload = {"query": query, "max_results": max_results}
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()

    elif provider_lower == "serper":
        if not SERPER_API_KEY:
            return {"error": "Missing SERPER_API_KEY env var"}
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "gl": country , "num": max_results}
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()
    

    else:
        return {"error": "Unsupported provider. Use 'serper' or 'tavily'."}


if __name__ == "__main__":
    LOG.info("Starting MCP server for web search")
    mcp.run(transport="stdio")