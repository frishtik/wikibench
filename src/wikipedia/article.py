"""Fetch article content and convert to markdown."""

import re

from markdownify import markdownify

from src.wikipedia.api import WikipediaAPI


async def fetch_article_markdown(api: WikipediaAPI, title: str) -> tuple[str, str]:
    """Fetch article and convert to markdown.

    Returns (title, markdown_content).
    The markdown includes links in [text](url) format.
    """
    html_content = await api.get_page_html(title)

    # Convert HTML to markdown
    markdown = markdownify(
        html_content,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    )

    # Clean up the markdown
    markdown = _clean_markdown(markdown)

    return title, markdown


def _clean_markdown(markdown: str) -> str:
    """Clean up converted markdown content."""
    # Remove excessive blank lines (more than 2 consecutive)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # Remove leading/trailing whitespace from each line while preserving structure
    lines = markdown.split("\n")
    lines = [line.rstrip() for line in lines]
    markdown = "\n".join(lines)

    # Remove leading/trailing whitespace from the entire content
    markdown = markdown.strip()

    # Remove edit section links like [edit]
    markdown = re.sub(r"\[edit\]", "", markdown)

    # Remove empty links
    markdown = re.sub(r"\[\]\([^)]*\)", "", markdown)

    # Clean up reference markers like [1], [2], etc.
    markdown = re.sub(r"\[\d+\]", "", markdown)

    # Remove Wikipedia-specific navigation elements
    markdown = re.sub(r"\[hide\]", "", markdown)
    markdown = re.sub(r"\[show\]", "", markdown)

    return markdown
