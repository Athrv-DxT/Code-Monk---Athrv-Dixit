import httpx
import logging
from typing import List, Dict, Any
from app.config import settings
from app.utils.redaction import redact_pii

logger = logging.getLogger("intellix.tavily")

def search_tavily(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Performs an external web search using Tavily API.
    Redacts any sensitive PII in the query before sending.
    """
    if not settings.TAVILY_API_KEY:
        logger.warning("Tavily API key not configured. Skipping external search.")
        return []
        
    # Redact query for privacy
    redacted_query = redact_pii(query)
    logger.info(f"Invoking Tavily external search for query: '{redacted_query}'")
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": redacted_query,
        "search_depth": "basic",
        "max_results": max_results
    }
    
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            raw_results = res_data.get("results", [])
            formatted_results = []
            for r in raw_results:
                formatted_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0)
                })
            logger.info(f"Tavily search completed. Found {len(formatted_results)} results.")
            return formatted_results
            
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []
