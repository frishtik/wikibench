"""MediaWiki API client with rate limiting."""

import asyncio
import time

import httpx

from src.config import WIKIPEDIA_API_URL


class WikipediaAPI:
    """Basic MediaWiki API client with rate limiting (100ms between requests)."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0.0
        self._rate_limit_delay = 0.1  # 100ms

    async def _rate_limit(self):
        """Ensure minimum delay between requests."""
        current_time = time.monotonic()
        elapsed = current_time - self._last_request_time
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.monotonic()

    async def query(self, **params) -> dict:
        """Make a query to the MediaWiki API."""
        params["format"] = "json"
        params["action"] = "query"
        await self._rate_limit()
        response = await self.client.get(WIKIPEDIA_API_URL, params=params)
        return response.json()

    async def get_page_html(self, title: str) -> str:
        """Get the HTML content of a Wikipedia page."""
        params = {
            "format": "json",
            "action": "parse",
            "page": title,
            "prop": "text",
            "disableeditsection": "true",
        }
        await self._rate_limit()
        response = await self.client.get(WIKIPEDIA_API_URL, params=params)
        data = response.json()
        if "error" in data:
            raise ValueError(f"Error fetching page '{title}': {data['error'].get('info', 'Unknown error')}")
        return data.get("parse", {}).get("text", {}).get("*", "")

    async def get_page_links(self, title: str) -> list[str]:
        """Get all outgoing links from a page (namespace 0 only).

        Uses continuation to fetch all links.
        """
        links = []
        params = {
            "titles": title,
            "prop": "links",
            "pllimit": "max",
            "plnamespace": "0",
        }

        while True:
            data = await self.query(**params)
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                for link in page.get("links", []):
                    links.append(link["title"])

            if "continue" not in data:
                break
            params["plcontinue"] = data["continue"]["plcontinue"]

        return links

    async def get_page_creation_date(self, title: str) -> str | None:
        """Get the creation date (first revision timestamp) of a page."""
        data = await self.query(
            titles=title,
            prop="revisions",
            rvdir="newer",
            rvlimit="1",
            rvprop="timestamp",
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                return None
            revisions = page.get("revisions", [])
            if revisions:
                return revisions[0].get("timestamp")
        return None

    async def is_disambiguation(self, title: str) -> bool:
        """Check if a page is a disambiguation page."""
        data = await self.query(
            titles=title,
            prop="pageprops",
            ppprop="disambiguation",
        )
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "pageprops" in page and "disambiguation" in page["pageprops"]:
                return True
        return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
