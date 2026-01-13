"""Benchmark orchestrator for parallel execution."""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import json
from tqdm.asyncio import tqdm_asyncio

from src.config import MODELS, ATTEMPTS_PER_MODEL, OUTPUTS_DIR
from src.reasoning_config import ReasoningMode
from src.wikipedia.api import WikipediaAPI
from src.wikipedia.pathfinder import PathFinder
from src.wikipedia.sampler import ArticleSampler
from src.game.engine import WikiGameEngine
from src.benchmark.attempt import AttemptRunner
from src.benchmark.conditions import (
    BenchmarkCondition,
    ConditionConfig,
    get_condition_config,
)
from src.benchmark.metrics import BenchmarkMetrics, AttemptMetrics


class BenchmarkOrchestrator:
    """Orchestrates running benchmark conditions with parallelization."""

    def __init__(self, max_concurrent: int = 4):
        """Initialize orchestrator.

        Args:
            max_concurrent: Maximum concurrent attempts across all models
                           (keep low to avoid overwhelming Wikipedia API)
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.tips: Dict[str, str] = {}  # model_id -> tips

    async def run_benchmark(
        self,
        condition: BenchmarkCondition,
    ) -> BenchmarkMetrics:
        """Run a complete benchmark for a condition.

        Args:
            condition: Which benchmark condition to run

        Returns:
            BenchmarkMetrics with all attempt results
        """
        config = get_condition_config(condition)
        metrics = BenchmarkMetrics(benchmark_name=config.name)

        # Set up output directory
        output_dir = OUTPUTS_DIR / config.output_dir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        async with WikipediaAPI() as api:
            sampler = ArticleSampler(api)
            pathfinder = PathFinder(api)
            engine = WikiGameEngine(api)
            runner = AttemptRunner(api, pathfinder, engine)

            # Sample article pairs
            print(f"Sampling {ATTEMPTS_PER_MODEL} article pairs...")
            pairs = await sampler.sample_article_pairs(
                count=ATTEMPTS_PER_MODEL,
                post_cutoff_only=config.post_cutoff_only,
            )

            if len(pairs) < ATTEMPTS_PER_MODEL:
                print(f"Warning: Only got {len(pairs)} pairs")

            # Pre-compute best paths only if needed (for peer pressure)
            best_paths = {}
            if config.use_peer_pressure:
                print("Computing best paths (needed for peer pressure)...")
                for i, (start, target) in enumerate(pairs):
                    print(f"  Path {i+1}/{len(pairs)}: {start} -> {target}", flush=True)
                    best_paths[(start, target)] = await pathfinder.compute_shortest_path(
                        start, target, max_depth=4
                    )
                    print(f"    Result: {best_paths[(start, target)]}", flush=True)

            # Create all tasks
            tasks = []
            for model_id in MODELS:
                for attempt_id, (start, target) in enumerate(pairs):
                    task = self._run_single_attempt(
                        runner=runner,
                        model_id=model_id,
                        attempt_id=attempt_id,
                        start_title=start,
                        target_title=target,
                        config=config,
                        tips=self.tips.get(model_id),
                        best_path=best_paths.get((start, target)),
                    )
                    tasks.append(task)

            # Run all attempts in parallel with progress bar
            print(f"Running {len(tasks)} attempts...")
            results = await tqdm_asyncio.gather(*tasks, desc=config.name)

            # Collect results
            for result in results:
                if result is not None:
                    metrics.add_attempt(result)

            # Collect tips if this is baseline
            if config.collect_tips:
                await self._collect_all_tips(api, engine, pairs)

        # Compute statistics
        metrics.compute_all_statistics()

        return metrics

    async def _run_single_attempt(
        self,
        runner: AttemptRunner,
        model_id: str,
        attempt_id: int,
        start_title: str,
        target_title: str,
        config: ConditionConfig,
        tips: Optional[str],
        best_path: Optional[int],
    ) -> Optional[AttemptMetrics]:
        """Run a single attempt with semaphore for rate limiting."""
        async with self.semaphore:
            try:
                return await runner.run_attempt(
                    model_id=model_id,
                    attempt_id=attempt_id,
                    start_title=start_title,
                    target_title=target_title,
                    config=config,
                    tips=tips,
                    best_path_length=best_path,
                )
            except Exception as e:
                print(f"Error in {model_id} attempt {attempt_id}: {e}")
                return None

    async def _collect_all_tips(
        self,
        api: WikipediaAPI,
        engine: WikiGameEngine,
        pairs: List[tuple],
    ):
        """Collect tips from all models after baseline attempts."""
        print("Collecting tips from models...")
        pathfinder = PathFinder(api)
        runner = AttemptRunner(api, pathfinder, engine)

        for model_id in MODELS:
            # Run a single game to get result for tips
            if pairs:
                start, target = pairs[0]
                result = await engine.play(
                    model_id=model_id,
                    start_title=start,
                    target_title=target,
                    reasoning_mode=ReasoningMode.HIGHEST,
                )
                tips = await runner.collect_tips(model_id, result)
                self.tips[model_id] = tips

                # Save tips to file
                tips_dir = OUTPUTS_DIR / "baseline" / "tips"
                tips_dir.mkdir(parents=True, exist_ok=True)
                tips_file = tips_dir / f"{model_id.replace('/', '_')}.txt"
                tips_file.write_text(tips)

    def load_tips(self):
        """Load tips from baseline run."""
        tips_dir = OUTPUTS_DIR / "baseline" / "tips"
        if tips_dir.exists():
            for tips_file in tips_dir.glob("*.txt"):
                model_id = tips_file.stem.replace("_", "/")
                self.tips[model_id] = tips_file.read_text()

    async def run_all_benchmarks(self) -> Dict[str, BenchmarkMetrics]:
        """Run all 5 benchmark conditions in order."""
        results = {}

        # 1. Baseline (collects tips)
        print("\n" + "=" * 60)
        print("Running Benchmark 1: Baseline")
        print("=" * 60)
        results["baseline"] = await self.run_benchmark(BenchmarkCondition.BASELINE)

        # 2. Post-cutoff
        print("\n" + "=" * 60)
        print("Running Benchmark 2: Post-cutoff")
        print("=" * 60)
        results["cutoff"] = await self.run_benchmark(BenchmarkCondition.CUTOFF)

        # 3. Tips (load tips from baseline)
        print("\n" + "=" * 60)
        print("Running Benchmark 3: Tips Available")
        print("=" * 60)
        self.load_tips()
        results["tips"] = await self.run_benchmark(BenchmarkCondition.TIPS)

        # 4. Low reasoning
        print("\n" + "=" * 60)
        print("Running Benchmark 4: Low Reasoning")
        print("=" * 60)
        results["low_reasoning"] = await self.run_benchmark(BenchmarkCondition.LOW_REASONING)

        # 5. Peer pressure
        print("\n" + "=" * 60)
        print("Running Benchmark 5: Peer Pressure")
        print("=" * 60)
        results["peer_pressure"] = await self.run_benchmark(BenchmarkCondition.PEER_PRESSURE)

        return results
