"""
Brave Search API client with DuckDuckGo fallback.

This module provides a web search function that:
1. Tries Brave Search API (free tier: 2000 req/month)
2. Falls back to DuckDuckGo (unlimited, free) if Brave fails
3. Retries transient errors with exponential backoff
4. Gracefully degrades on malformed results
"""

import os
import logging
from typing import List, Dict, Optional
from src.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


def web_search(query: str, limit: int = 5, ddgs_class=None) -> List[Dict]:
    """
    Search the web using Brave Search API with DuckDuckGo fallback.

    Args:
        query: Search query string
        limit: Maximum number of results to return (default: 5)
        ddgs_class: Dependency injection for DDGS (testing only)

    Returns:
        List of dicts with keys: title, url, snippet
    """
    if not query or not query.strip():
        logger.warning("Empty query provided")
        return []

    # Try Brave Search first
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if brave_api_key:
        try:
            results = _brave_search(query, limit, brave_api_key)
            if results:
                return results
            logger.warning("Brave Search returned no results, trying fallback")
        except Exception as e:
            logger.warning(f"Brave Search failed: {e}, trying fallback")

    # Fallback to DuckDuckGo
    try:
        return _duckduckgo_search(query, limit, ddgs_class)
    except Exception as e:
        logger.error(f"DuckDuckGo fallback failed: {e}")
        return []


@retry_with_backoff(max_attempts=3)
def _brave_search(query: str, limit: int, api_key: str) -> List[Dict]:
    """Execute Brave Search API call."""
    import requests

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": limit}

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", "Untitled"),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
        })

    return results


def _duckduckgo_search(query: str, limit: int, ddgs_class=None) -> List[Dict]:
    """Execute DuckDuckGo search (fallback)."""
    if ddgs_class is None:
        from ddgs import DDGS
        ddgs_class = DDGS

    results = []
    with ddgs_class() as ddgs:
        for result in ddgs.text(query, max_results=limit):
            results.append({
                "title": result.get("title", "Untitled"),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
            })
    return results