"""Single benchmark attempt with metrics collection."""

import asyncio
from typing import Optional, List

from src.config import MODELS, MODEL_DISPLAY_NAMES, MAX_CLICKS
from src.wikipedia.api import WikipediaAPI
from src.wikipedia.pathfinder import PathFinder
from src.game.engine import WikiGameEngine, GameResult
from src.game.prompts import (
    get_peer_pressure_preamble,
    get_tips_preamble,
    get_tips_request_prompt,
)
from src.openrouter_client import chat_completion
from src.reasoning_config import ReasoningMode
from src.benchmark.metrics import AttemptMetrics, StepMetrics
from src.benchmark.conditions import ConditionConfig


class AttemptRunner:
    """Runs a single game attempt with full metrics collection."""

    def __init__(
        self,
        api: WikipediaAPI,
        pathfinder: PathFinder,
        engine: WikiGameEngine,
    ):
        self.api = api
        self.pathfinder = pathfinder
        self.engine = engine

    async def run_attempt(
        self,
        model_id: str,
        attempt_id: int,
        start_title: str,
        target_title: str,
        config: ConditionConfig,
        tips: Optional[str] = None,
        best_path_length: Optional[int] = None,
    ) -> AttemptMetrics:
        """Run a single attempt and collect metrics.

        Args:
            model_id: OpenRouter model ID
            attempt_id: Attempt number (0-14)
            start_title: Starting article
            target_title: Target article
            config: Benchmark condition configuration
            tips: Tips to include (if use_tips is True)
            best_path_length: Pre-computed best path (for peer pressure)

        Returns:
            AttemptMetrics with full step-by-step data
        """
        # Compute best path if not provided
        if best_path_length is None:
            best_path_length = await self.pathfinder.compute_shortest_path(
                start_title, target_title
            )

        # Build system prompt prefix based on condition
        prompt_prefix = ""

        if config.use_tips and tips:
            prompt_prefix += get_tips_preamble(tips)

        if config.use_peer_pressure:
            prompt_prefix += get_peer_pressure_preamble(
                model_id=model_id,
                start_title=start_title,
                target_title=target_title,
                best_path_length=best_path_length,
                clicks_so_far=0,  # Updated per turn in engine
            )

        # Run the game
        result = await self.engine.play(
            model_id=model_id,
            start_title=start_title,
            target_title=target_title,
            reasoning_mode=config.reasoning_mode,
            system_prompt_prefix=prompt_prefix,
        )

        # Compute step metrics with remaining distances
        step_metrics = []
        for i, step in enumerate(result.steps):
            # Get remaining distance before and after
            if i == 0:
                distance_before = await self.pathfinder.get_remaining_distance(
                    start_title, target_title
                )
            else:
                distance_before = step_metrics[-1].remaining_distance_after

            distance_after = await self.pathfinder.get_remaining_distance(
                step.chosen_target_title, target_title
            )

            direction = self.pathfinder.classify_step(distance_before, distance_after)

            step_metrics.append(StepMetrics(
                step_index=step.step_index,
                remaining_distance_before=distance_before,
                remaining_distance_after=distance_after,
                step_direction=direction,
            ))

        # Build attempt metrics
        return AttemptMetrics(
            model_id=model_id,
            attempt_id=attempt_id,
            start_title=start_title,
            target_title=target_title,
            solved=result.solved,
            total_clicks=result.total_clicks if result.solved else MAX_CLICKS,
            best_path_length=best_path_length,
            steps=step_metrics,
        )

    async def collect_tips(
        self,
        model_id: str,
        game_result: GameResult,
    ) -> str:
        """Collect tips from model after an attempt."""
        prompt = get_tips_request_prompt(
            won=game_result.solved,
            path_taken=game_result.path,
            target=game_result.target_title,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await chat_completion(
            model_id=model_id,
            messages=messages,
            reasoning_mode=ReasoningMode.HIGHEST,
        )

        return response
