import os
import logging, sys
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, Optional
import requests

from mcp.server.fastmcp import FastMCP

load_dotenv()
# Load strategies from JSON file
STRATEGIES_FILE = Path(__file__).parent / "strategies.json"

LOG = logging.getLogger("mcp_server")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "DEBUG"),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# initialize server (stateless_http recommended for simple deployments)
mcp = FastMCP("peoplemake-ai-tool", stateless_http=True)


@mcp.tool()
def web_search(query: str, country: str = None , max_results: int = 10, provider: str = "serper") -> Dict[str, Any]:
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



def load_strategies():
    """Load strategies from the JSON file."""
    try:
        with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('strategies', [])
    except Exception as e:
        LOG.error(f"Failed to load strategies: {e}")
        return []

@mcp.tool()
def get_strategy(strategy_name: str, industry: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve a search strategy focus pool by strategy name and optionally filter by industry.
    
    AVAILABLE STRATEGIES:
    
    1. 'sub_industry' - Sub-Industry Strategy
       This strategy focuses on searching within smaller, specialized industry segments rather than broad industry categories.
       
       What it does:
       - Breaks down major industries (like Fintech, Healthcare, E-commerce, etc.) into specific sub-sectors
       - Enables targeted searches within niche markets such as "Payments" within Fintech or "Telemedicine" within Healthcare
       - Helps identify companies operating in specialized verticals within broader industry categories
       
       Use cases:
       - When you need to find companies in a specific niche (e.g., "BNPL" platforms instead of all "Fintech")
       - To narrow down search results to highly relevant segments
       - For competitive analysis within a specific sub-sector
       - To discover emerging players in specialized markets
       
       Example: Instead of searching all "Healthcare" companies, you can target "Digital Health" or "Wearables" specifically.
    
    2. 'problem_based' - Problem-Based Strategy
       This strategy identifies companies by the specific problems they solve rather than their industry classification.
       
       What it does:
       - Categorizes companies based on the challenges and pain points they address
       - Maps industry-specific problems to solution providers
       - Enables search by outcome or value proposition rather than product category
       
       Use cases:
       - When looking for solutions to a specific business challenge (e.g., "Cart Abandonment Solutions")
       - To find innovative companies addressing emerging problems
       - For identifying alternative solutions across different industries
       - When the problem is known but the solution space is unclear
       
       Example: Instead of searching "E-commerce SaaS", you can find companies solving "Checkout Optimization" or "Inventory Management" problems.
    
    3. 'customer_based' - Customer-Based Strategy
       This strategy segments companies by their target customer types and markets they serve.
       
       What it does:
       - Classifies companies based on who they sell to (e.g., SMB Banks, Hospitals, DTC Brands)
       - Groups businesses by their ideal customer profile (ICP)
       - Enables B2B market segmentation and customer-centric searches
       
       Use cases:
       - When targeting companies that serve specific customer segments (e.g., "Neobanks" in Fintech)
       - For finding vendors, partners, or competitors serving similar customer bases
       - To understand market positioning by customer type
       - When building account-based marketing (ABM) lists
       
       Example: Instead of searching all "Fintech" companies, you can target those specifically serving "SMB Banks" or "Lending Platforms".
    
    AVAILABLE Industries:
        Fintech, Healthcare, E-commerce, Education, Logistics, Technology, Manufacturing, Media, Real Estate, Food, Energy
    Args:
        strategy_name: The type of strategy to retrieve ('sub_industry', 'problem_based', or 'customer_based')
        industry: Optional industry name to filter results (e.g., 'Fintech', 'Healthcare', 'E-commerce')
    
    Returns:
        - If only strategy_name provided: Returns the complete focus_pool object with all industries
        - If both strategy_name and industry provided: Returns only the array of focus areas for that industry
        - On error: Returns error message with available options
    """
    
    # Normalize strategy name
    strategy_name_lower = strategy_name.lower()
    
    # Load strategies from file
    strategies = load_strategies()
    
    if not strategies:
        return {"error": "Failed to load strategies from file"}
    
    # Find the matching strategy
    matching_strategy = None
    for strategy in strategies:
        if strategy.get('strategy_type', '').lower() == strategy_name_lower:
            matching_strategy = strategy
            break
    
    if not matching_strategy:
        available_types = [s.get('strategy_type') for s in strategies]
        return {
            "error": f"Strategy '{strategy_name}' not found",
            "available_strategies": available_types
        }
    
    focus_pool = matching_strategy.get('focus_pool', {})
    
    # If industry is specified, return only that industry's array
    if industry:
        if industry in focus_pool:
            return focus_pool[industry]
        else:
            return {
                "error": f"Industry '{industry}' not found in this strategy",
                "available_industries": list(focus_pool.keys())
            }
    return focus_pool


if __name__ == "__main__":
    LOG.info("Starting MCP server")
    mcp.run(transport="stdio")