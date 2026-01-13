"""MediaWiki API client with rate limiting."""

import asyncio
import time

import httpx

from src.config import WIKIPEDIA_API_URL


class WikipediaAPI:
    """Basic MediaWiki API client with rate limiting (100ms between requests).

    Uses an async lock to ensure rate limiting works with concurrent requests.
    """

    def __init__(self):
        # Wikipedia requires a User-Agent header
        headers = {
            "User-Agent": "WikiBench/1.0 (https://github.com/wikibench; wikibench@example.com)"
        }
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
        # Allow up to 3 concurrent requests with delay between each
        self._semaphore = asyncio.Semaphore(3)
        self._request_delay = 0.2  # 200ms between requests within semaphore

    async def _rate_limit(self):
        """Limit concurrent requests using a semaphore."""
        await self._semaphore.acquire()
        # Small delay before making request
        await asyncio.sleep(self._request_delay)

    def _release_rate_limit(self):
        """Release semaphore after request completes."""
        self._semaphore.release()

    async def query(self, **params) -> dict:
        """Make a query to the MediaWiki API with retry logic."""
        params["format"] = "json"
        params["action"] = "query"

        last_error = None
        for attempt in range(3):  # Up to 3 attempts
            await self._rate_limit()
            try:
                response = await self.client.get(WIKIPEDIA_API_URL, params=params)
                response.raise_for_status()
                result = response.json()
                self._release_rate_limit()
                return result
            except (httpx.HTTPStatusError, ValueError) as e:
                self._release_rate_limit()
                last_error = e
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise ValueError(f"Wikipedia API query failed after 3 attempts: {e}")
        return {}

    async def get_page_html(self, title: str) -> str:
        """Get the HTML content of a Wikipedia page with retry logic."""
        params = {
            "format": "json",
            "action": "parse",
            "page": title,
            "prop": "text",
            "disableeditsection": "true",
        }

        for attempt in range(3):
            await self._rate_limit()
            try:
                response = await self.client.get(WIKIPEDIA_API_URL, params=params)
                response.raise_for_status()
                data = response.json()
                self._release_rate_limit()
                if "error" in data:
                    raise ValueError(f"Error fetching page '{title}': {data['error'].get('info', 'Unknown error')}")
                return data.get("parse", {}).get("text", {}).get("*", "")
            except (httpx.HTTPStatusError, ValueError) as e:
                self._release_rate_limit()
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise ValueError(f"Failed to fetch page '{title}' after 3 attempts: {e}")
        return ""

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
