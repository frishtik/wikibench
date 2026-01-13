"""Integration test for wikibench - tests game loop with a single attempt."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_single_game():
    """Test a single game with one model (requires API key)."""
    from src.config import OPENROUTER_API_KEY
    from src.wikipedia.api import WikipediaAPI
    from src.wikipedia.pathfinder import PathFinder
    from src.game.engine import WikiGameEngine
    from src.reasoning_config import ReasoningMode

    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY not set - skipping API test")
        return

    print("\n=== Integration Test: Single Game ===")
    print("Testing with easy pair: Dog -> Animal")

    async with WikipediaAPI() as api:
        pathfinder = PathFinder(api)
        engine = WikiGameEngine(api)

        # Compute best path first
        print("\nComputing best path...")
        best_path = await pathfinder.compute_shortest_path("Dog", "Animal")
        print(f"Best path length: {best_path}")

        # Play a single game with one model
        print("\nPlaying game with gemini-3-flash-preview...")
        result = await engine.play(
            model_id="google/gemini-3-flash-preview",
            start_title="Dog",
            target_title="Animal",
            reasoning_mode=ReasoningMode.HIGHEST,
        )

        print(f"\nResult:")
        print(f"  Solved: {result.solved}")
        print(f"  Clicks: {result.total_clicks}")
        print(f"  Path: {' -> '.join(result.path)}")

    print("\n[PASS] Integration test completed!")


async def test_imports():
    """Test that all modules import correctly."""
    print("\n=== Testing Imports ===")

    try:
        from src.config import MODELS, MAX_CLICKS
        print(f"  config: OK (MODELS={MODELS[:2]}...)")

        from src.reasoning_config import ReasoningMode, get_reasoning_params
        print(f"  reasoning_config: OK")

        from src.openrouter_client import chat_completion
        print(f"  openrouter_client: OK")

        from src.wikipedia.api import WikipediaAPI
        from src.wikipedia.article import fetch_article_markdown
        from src.wikipedia.links import extract_links_from_markdown
        from src.wikipedia.pathfinder import PathFinder
        from src.wikipedia.sampler import ArticleSampler
        print(f"  wikipedia modules: OK")

        from src.game.engine import WikiGameEngine
        from src.game.prompts import get_system_prompt
        from src.game.parser import parse_response
        print(f"  game modules: OK")

        from src.benchmark.metrics import BenchmarkMetrics, AttemptMetrics
        from src.benchmark.conditions import BenchmarkCondition
        from src.benchmark.attempt import AttemptRunner
        from src.benchmark.orchestrator import BenchmarkOrchestrator
        print(f"  benchmark modules: OK")

        from src.output.csv_writer import write_benchmark_csv
        from src.output.graphs import generate_all_graphs
        from src.output.traces import write_model_traces
        print(f"  output modules: OK")

        print("\n[PASS] All imports successful!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run integration tests."""
    print("=" * 60)
    print("WikiBench Integration Test")
    print("=" * 60)

    # Test imports first
    if not await test_imports():
        sys.exit(1)

    # Test single game if API key available
    await test_single_game()


if __name__ == "__main__":
    asyncio.run(main())
