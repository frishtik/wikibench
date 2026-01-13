"""Random Wikipedia article sampling with filtering."""

import asyncio
import random
from datetime import datetime
from typing import List, Optional, Tuple

from src.wikipedia.api import WikipediaAPI
from src.config import CUTOFF_DATE, WIKIPEDIA_API_URL


class ArticleSampler:
    """Sample random Wikipedia articles with various filters."""

    def __init__(self, api: WikipediaAPI):
        self.api = api

    async def get_random_articles(self, count: int = 10) -> List[str]:
        """Get random article titles from Wikipedia.

        Uses the random generator API to get articles from namespace 0.
        """
        params = {
            "generator": "random",
            "grnnamespace": "0",
            "grnlimit": str(count),
        }
        data = await self.api.query(**params)

        titles = []
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "title" in page:
                titles.append(page["title"])

        return titles

    async def is_valid_article(self, title: str) -> bool:
        """Check if article is valid (not disambiguation, not list, etc.)."""
        # Check for disambiguation
        if await self.api.is_disambiguation(title):
            return False

        # Skip titles that start with "List of"
        if title.startswith("List of "):
            return False

        # Skip titles containing "(disambiguation)"
        if "(disambiguation)" in title:
            return False

        return True

    async def get_creation_date(self, title: str) -> Optional[datetime]:
        """Get the creation date of an article."""
        timestamp = await self.api.get_page_creation_date(title)
        if timestamp:
            # Parse ISO timestamp like "2001-10-06T00:00:04Z"
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return None

    async def is_post_cutoff(self, title: str, cutoff: str = CUTOFF_DATE) -> bool:
        """Check if article was created after the cutoff date."""
        creation = await self.get_creation_date(title)
        if creation is None:
            return False

        cutoff_dt = datetime.fromisoformat(cutoff + "T00:00:00+00:00")
        return creation > cutoff_dt

    async def sample_valid_articles(
        self,
        count: int,
        post_cutoff_only: bool = False,
        max_attempts: int = 100
    ) -> List[str]:
        """Sample valid articles, optionally filtering for post-cutoff.

        Args:
            count: Number of valid articles to return
            post_cutoff_only: If True, only return articles created after CUTOFF_DATE
            max_attempts: Maximum sampling attempts before giving up

        Returns:
            List of valid article titles
        """
        valid_articles = []
        attempts = 0

        while len(valid_articles) < count and attempts < max_attempts:
            # Get batch of random articles
            batch_size = min(20, (count - len(valid_articles)) * 3)
            candidates = await self.get_random_articles(batch_size)
            attempts += 1

            for title in candidates:
                if len(valid_articles) >= count:
                    break

                # Check validity
                if not await self.is_valid_article(title):
                    continue

                # Check cutoff if required
                if post_cutoff_only:
                    if not await self.is_post_cutoff(title):
                        continue

                valid_articles.append(title)

        return valid_articles

    async def sample_article_pairs(
        self,
        count: int,
        post_cutoff_only: bool = False
    ) -> List[Tuple[str, str]]:
        """Sample pairs of (start, target) articles.

        For post_cutoff_only, BOTH articles must be post-cutoff.
        """
        # Sample 2x count to get pairs
        articles = await self.sample_valid_articles(
            count * 2,
            post_cutoff_only=post_cutoff_only,
            max_attempts=200 if post_cutoff_only else 100
        )

        # Pair them up
        pairs = []
        for i in range(0, len(articles) - 1, 2):
            if len(pairs) >= count:
                break
            pairs.append((articles[i], articles[i + 1]))

        return pairs
