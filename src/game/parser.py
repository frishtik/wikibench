import re

LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def strip_title_attribute(href: str) -> str:
    """Strip title attribute from markdown link href.

    Models sometimes include title attributes in their responses:
    [text](/wiki/Article "Article Title")
    """
    if ' "' in href:
        href = href.split(' "')[0]
    elif " '" in href:
        href = href.split(" '")[0]
    return href.strip()


def parse_response(response: str) -> tuple[str, str] | None:
    """Extract exactly one markdown link from model response.

    Returns (text, href) or None if parsing fails.
    Strict: must be exactly one link in response.
    """
    response = response.strip()
    matches = LINK_PATTERN.findall(response)

    if len(matches) == 1:
        text, href = matches[0]
        return (text, strip_title_attribute(href))

    # Try to be slightly lenient - find first valid Wikipedia link
    for text, href in matches:
        if "wikipedia.org" in href or href.startswith("/wiki/"):
            return (text, strip_title_attribute(href))

    return None
