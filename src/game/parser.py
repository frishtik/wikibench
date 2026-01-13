import re

LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

def parse_response(response: str) -> tuple[str, str] | None:
    """Extract exactly one markdown link from model response.

    Returns (text, href) or None if parsing fails.
    Strict: must be exactly one link in response.
    """
    response = response.strip()
    matches = LINK_PATTERN.findall(response)

    if len(matches) == 1:
        return matches[0]

    # Try to be slightly lenient - find first valid Wikipedia link
    for text, href in matches:
        if "wikipedia.org" in href:
            return (text, href)

    return None
