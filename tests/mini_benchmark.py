"""Mini benchmark test - run a few games to verify the system works."""

import asyncio
import sys
sys.path.insert(0, '.')

from src.config import MODELS
from src.wikipedia.api import WikipediaAPI
from src.wikipedia.pathfinder import PathFinder
from src.wikipedia.sampler import ArticleSampler
from src.game.engine import WikiGameEngine
from src.reasoning_config import ReasoningMode


async def main():
    print('Starting mini benchmark...', flush=True)

    async with WikipediaAPI() as api:
        sampler = ArticleSampler(api)
        pathfinder = PathFinder(api)
        engine = WikiGameEngine(api)

        # Sample 2 article pairs (without path verification for speed)
        print('Sampling article pairs...', flush=True)
        pairs = await sampler.sample_article_pairs(
            count=2,
            post_cutoff_only=False
        )
        print(f'Got {len(pairs)} pairs:', flush=True)
        for start, target in pairs:
            print(f'  {start} -> {target}', flush=True)

        if not pairs:
            print('ERROR: No pairs sampled!')
            return

        # Test with one model, one pair
        model_id = 'google/gemini-3-flash-preview'
        start, target = pairs[0]

        print(f'\nRunning game: {start} -> {target}', flush=True)
        print(f'Model: {model_id}', flush=True)

        # Compute best path (with limited search)
        print('Computing best path (limited search)...', flush=True)
        best_path = await pathfinder.compute_shortest_path(start, target, max_depth=4)
        print(f'Best path: {best_path} (999 = not found within limit)', flush=True)

        # Play game
        result = await engine.play(
            model_id=model_id,
            start_title=start,
            target_title=target,
            reasoning_mode=ReasoningMode.HIGHEST,
        )

        print(f'\nResult:', flush=True)
        print(f'  Solved: {result.solved}', flush=True)
        print(f'  Clicks: {result.total_clicks}', flush=True)
        path_str = ' -> '.join(result.path)
        print(f'  Path: {path_str}', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
