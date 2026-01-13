"""Sanity check tests for wikibench core functionality."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.wikipedia.api import WikipediaAPI
from src.wikipedia.article import fetch_article_markdown
from src.wikipedia.links import extract_links_from_markdown, title_from_url
from src.game.parser import parse_response
from src.reasoning_config import ReasoningMode, get_reasoning_params
from src.config import MODELS


async def test_wikipedia_api():
    """Test basic Wikipedia API functionality."""
    print("\n=== Testing Wikipedia API ===")

    async with WikipediaAPI() as api:
        # Test fetching an article
        print("Fetching 'Dog' article...")
        title, markdown = await fetch_article_markdown(api, "Dog")
        print(f"  Title: {title}")
        print(f"  Markdown length: {len(markdown)} chars")
        print(f"  First 200 chars: {markdown[:200]}...")

        # Test link extraction
        links = extract_links_from_markdown(markdown)
        print(f"  Found {len(links)} links")
        if links:
            print(f"  Sample links: {links[:5]}")

        # Test page links API
        print("\nFetching links from 'Dog' page...")
        page_links = await api.get_page_links("Dog")
        print(f"  Found {len(page_links)} outgoing links")
        if page_links:
            print(f"  Sample: {page_links[:10]}")

        # Test disambiguation check
        print("\nChecking disambiguation pages...")
        is_disambig = await api.is_disambiguation("Dog")
        print(f"  'Dog' is disambiguation: {is_disambig}")
        is_disambig = await api.is_disambiguation("Mercury (disambiguation)")
        print(f"  'Mercury (disambiguation)' is disambiguation: {is_disambig}")

        # Test creation date
        print("\nGetting creation dates...")
        creation = await api.get_page_creation_date("Dog")
        print(f"  'Dog' created: {creation}")

    print("\n[PASS] Wikipedia API tests completed")


def test_response_parser():
    """Test response parsing."""
    print("\n=== Testing Response Parser ===")

    # Good response
    response = "[Animal](https://en.wikipedia.org/wiki/Animal)"
    parsed = parse_response(response)
    print(f"  Good response: {parsed}")
    assert parsed == ("Animal", "https://en.wikipedia.org/wiki/Animal")

    # Response with extra text (should still work)
    response = "I'll click on [Mammal](https://en.wikipedia.org/wiki/Mammal)"
    parsed = parse_response(response)
    print(f"  With extra text: {parsed}")

    # Multiple links (should fail strict, but find wikipedia one)
    response = "[Dog](https://example.com) and [Cat](https://en.wikipedia.org/wiki/Cat)"
    parsed = parse_response(response)
    print(f"  Multiple links: {parsed}")

    # No links
    response = "I don't know which link to click"
    parsed = parse_response(response)
    print(f"  No links: {parsed}")
    assert parsed is None

    print("\n[PASS] Response parser tests completed")


def test_reasoning_config():
    """Test reasoning configuration."""
    print("\n=== Testing Reasoning Config ===")

    for model_id in MODELS:
        print(f"\n  Model: {model_id}")

        highest = get_reasoning_params(model_id, ReasoningMode.HIGHEST)
        print(f"    HIGHEST: {highest}")

        lowest = get_reasoning_params(model_id, ReasoningMode.LOWEST)
        print(f"    LOWEST: {lowest}")

        # Verify structure
        assert "reasoning" in highest
        assert "reasoning" in lowest
        assert highest["reasoning"].get("exclude") == True
        assert lowest["reasoning"].get("exclude") == True

    print("\n[PASS] Reasoning config tests completed")


def test_title_from_url():
    """Test URL to title conversion."""
    print("\n=== Testing Title Extraction ===")

    test_cases = [
        ("https://en.wikipedia.org/wiki/Dog", "Dog"),
        ("https://en.wikipedia.org/wiki/United_States", "United States"),
        ("/wiki/Cat", "Cat"),
        ("https://en.wikipedia.org/wiki/New_York_City#History", "New York City"),
    ]

    for url, expected in test_cases:
        result = title_from_url(url)
        print(f"  {url} -> {result}")
        assert result == expected, f"Expected {expected}, got {result}"

    print("\n[PASS] Title extraction tests completed")


async def main():
    """Run all sanity checks."""
    print("=" * 60)
    print("WikiBench Sanity Check")
    print("=" * 60)

    try:
        await test_wikipedia_api()
        test_response_parser()
        test_reasoning_config()
        test_title_from_url()

        print("\n" + "=" * 60)
        print("ALL SANITY CHECKS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
