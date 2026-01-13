"""Wikipedia API modules for fetching and processing Wikipedia articles."""

from src.wikipedia.api import WikipediaAPI, WIKIPEDIA_API_URL
from src.wikipedia.article import fetch_article_markdown
from src.wikipedia.links import (
    extract_links_from_markdown,
    normalize_wikipedia_url,
    title_from_url,
    LINK_PATTERN,
)

__all__ = [
    "WikipediaAPI",
    "WIKIPEDIA_API_URL",
    "fetch_article_markdown",
    "extract_links_from_markdown",
    "normalize_wikipedia_url",
    "title_from_url",
    "LINK_PATTERN",
]
