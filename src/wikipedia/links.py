"""Extract links from markdown content."""

import re
from urllib.parse import unquote, urlparse

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_links_from_markdown(markdown: str) -> list[tuple[str, str]]:
    """Extract all markdown links from content.

    Returns list of (text, href) tuples.
    Only includes Wikipedia article links (filters out external, special pages).
    """
    matches = LINK_PATTERN.findall(markdown)
    links = []

    for text, href in matches:
        # Skip empty text or href
        if not text.strip() or not href.strip():
            continue

        # Strip title attribute from href (e.g., '/wiki/Animal "Animal"' -> '/wiki/Animal')
        href = strip_title_attribute(href)

        # Check if it's a valid Wikipedia article link
        normalized = normalize_wikipedia_url(href)
        if normalized is not None:
            links.append((text, href))

    return links


def strip_title_attribute(href: str) -> str:
    """Strip title attribute from markdown link href.

    Markdown links from Wikipedia often have title attributes:
    [text](/wiki/Article "Article Title") -> href="/wiki/Article \"Article Title\""

    This extracts just the URL part.
    """
    # Title attributes start with space + quote
    if ' "' in href:
        href = href.split(' "')[0]
    elif " '" in href:
        href = href.split(" '")[0]
    return href.strip()


def normalize_wikipedia_url(href: str) -> str | None:
    """Normalize a Wikipedia URL to extract the article title.

    Returns the article title or None if not a valid Wikipedia article URL.
    """
    # Handle relative URLs (most common in Wikipedia HTML)
    if href.startswith("/wiki/"):
        title = href[6:]  # Remove '/wiki/' prefix
    elif href.startswith("//en.wikipedia.org/wiki/"):
        title = href[24:]
    elif href.startswith("https://en.wikipedia.org/wiki/"):
        title = href[30:]
    elif href.startswith("http://en.wikipedia.org/wiki/"):
        title = href[29:]
    else:
        # Not a Wikipedia article link
        return None

    # Remove URL fragment (anchor)
    if "#" in title:
        title = title.split("#")[0]

    # Skip if empty after removing fragment
    if not title:
        return None

    # Skip special pages and namespaces
    special_prefixes = (
        "Special:",
        "Wikipedia:",
        "Help:",
        "Category:",
        "Portal:",
        "Template:",
        "Template_talk:",
        "Talk:",
        "User:",
        "User_talk:",
        "File:",
        "MediaWiki:",
        "Module:",
        "Draft:",
    )
    if title.startswith(special_prefixes):
        return None

    # Skip external link indicators
    if title.startswith("//") or title.startswith("http"):
        return None

    # URL decode the title
    title = unquote(title)

    # Replace underscores with spaces (Wikipedia convention)
    title = title.replace("_", " ")

    return title


def title_from_url(url: str) -> str:
    """Extract article title from Wikipedia URL."""
    normalized = normalize_wikipedia_url(url)
    if normalized is None:
        # Try to extract from the URL path directly
        parsed = urlparse(url)
        path = parsed.path
        if "/wiki/" in path:
            title = path.split("/wiki/")[-1]
            title = unquote(title)
            title = title.replace("_", " ")
            if "#" in title:
                title = title.split("#")[0]
            return title
        return url
    return normalized
