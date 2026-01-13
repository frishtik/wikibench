"""Random Wikipedia article sampling with filtering."""

import asyncio
import random
from datetime import datetime
from typing import List, Optional, Tuple, TYPE_CHECKING

from src.wikipedia.api import WikipediaAPI
from src.config import CUTOFF_DATE, WIKIPEDIA_API_URL

if TYPE_CHECKING:
    from src.wikipedia.pathfinder import PathFinder


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
        post_cutoff_only: bool = False,
        pathfinder: Optional["PathFinder"] = None,
        max_path_depth: int = 6
    ) -> List[Tuple[str, str]]:
        """Sample pairs of (start, target) articles.

        For post_cutoff_only, BOTH articles must be post-cutoff.
        If pathfinder is provided, verifies pairs have a path within max_path_depth.
        """
        pairs = []
        attempts = 0
        max_attempts = 50

        while len(pairs) < count and attempts < max_attempts:
            attempts += 1

            # Sample batch of candidate articles
            batch_size = max(4, (count - len(pairs)) * 4)
            articles = await self.sample_valid_articles(
                batch_size,
                post_cutoff_only=post_cutoff_only,
                max_attempts=200 if post_cutoff_only else 100
            )

            # Try to form pairs
            random.shuffle(articles)
            i = 0
            while i < len(articles) - 1 and len(pairs) < count:
                start, target = articles[i], articles[i + 1]
                i += 2

                # Skip if same article
                if start.lower() == target.lower():
                    continue

                # Verify path exists if pathfinder provided
                if pathfinder is not None:
                    try:
                        path_len = await pathfinder.compute_shortest_path(
                            start, target, max_depth=max_path_depth
                        )
                        if path_len >= 999:
                            # No path found, skip this pair
                            continue
                    except Exception:
                        # Error computing path, skip
                        continue

                pairs.append((start, target))

        return pairs
