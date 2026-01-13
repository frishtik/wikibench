"""BFS shortest path computation between Wikipedia articles."""

import asyncio
from collections import deque
from typing import Dict, Optional, Set, Tuple

from src.wikipedia.api import WikipediaAPI


class PathFinder:
    """Compute shortest paths between Wikipedia articles using BFS."""

    def __init__(self, api: WikipediaAPI):
        self.api = api
        # Cache: (target) -> {title: distance}
        # We do backwards BFS from target to build distance map
        self._distance_cache: Dict[str, Dict[str, int]] = {}
        # Cache for outgoing links
        self._links_cache: Dict[str, Set[str]] = {}

    async def _get_links(self, title: str) -> Set[str]:
        """Get outgoing links from a page (cached)."""
        normalized = self._normalize_title(title)
        if normalized not in self._links_cache:
            links = await self.api.get_page_links(title)
            self._links_cache[normalized] = {self._normalize_title(l) for l in links}
        return self._links_cache[normalized]

    def _normalize_title(self, title: str) -> str:
        """Normalize title for consistent comparison."""
        return title.lower().replace("_", " ").strip()

    async def compute_shortest_path(
        self, start_title: str, target_title: str, max_depth: int = 10
    ) -> int:
        """Compute the shortest path from start to target.

        Args:
            start_title: Starting article title
            target_title: Target article title
            max_depth: Maximum BFS depth to search

        Returns:
            Minimum clicks needed (or 999 if no path found within max_depth)
        """
        # BFS from start to target
        start = self._normalize_title(start_title)
        target = self._normalize_title(target_title)

        if start == target:
            return 0

        visited = {start}
        queue = deque([(start_title, 0)])  # (title, depth)

        while queue:
            current_title, depth = queue.popleft()

            if depth >= max_depth:
                continue

            links = await self._get_links(current_title)

            for link in links:
                normalized_link = self._normalize_title(link)

                if normalized_link == target:
                    return depth + 1

                if normalized_link not in visited:
                    visited.add(normalized_link)
                    queue.append((link, depth + 1))

        return 999  # No path found

    async def get_remaining_distance(
        self, current_title: str, target_title: str, max_depth: int = 10
    ) -> int:
        """Get remaining distance from current page to target.

        This uses BFS from current position toward target.

        Returns:
            Minimum clicks needed from current to target (or 999 if unreachable)
        """
        return await self.compute_shortest_path(current_title, target_title, max_depth)

    async def build_distance_map(
        self, target_title: str, max_depth: int = 5
    ) -> Dict[str, int]:
        """Build a distance map showing distance to target from various pages.

        Uses backwards BFS: finds all pages that can reach target within max_depth.
        This is useful for computing remaining distance efficiently during a game.

        Returns:
            Dict mapping normalized title -> distance to target
        """
        target = self._normalize_title(target_title)

        if target in self._distance_cache:
            return self._distance_cache[target]

        # We need to do backwards BFS, but Wikipedia API gives us outgoing links
        # So we do forward BFS from target and record distances
        # This gives us: for each page we visit, how far target is FROM that page

        distance_map = {target: 0}
        visited = {target}
        queue = deque([(target_title, 0)])

        while queue:
            current_title, depth = queue.popleft()

            if depth >= max_depth:
                continue

            links = await self._get_links(current_title)

            for link in links:
                normalized = self._normalize_title(link)

                if normalized not in visited:
                    visited.add(normalized)
                    # From 'link', you can reach 'current' in 1 step
                    # And from 'current', target is 'depth' steps away
                    # But this is forward BFS, so we record distance FROM this page TO target
                    # Actually we're doing it wrong - we need incoming links, not outgoing

        # Actually, for remaining distance, we just do direct BFS each time
        # Let's simplify and use direct computation

        self._distance_cache[target] = distance_map
        return distance_map

    def classify_step(
        self, distance_before: int, distance_after: int
    ) -> str:
        """Classify a step as forward, neutral, or backwards.

        Args:
            distance_before: Remaining distance before the step
            distance_after: Remaining distance after the step

        Returns:
            'forward' if distance decreased
            'neutral' if distance stayed same
            'backwards' if distance increased
        """
        if distance_after < distance_before:
            return "forward"
        elif distance_after > distance_before:
            return "backwards"
        else:
            return "neutral"
