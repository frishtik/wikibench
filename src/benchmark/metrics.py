"""Metrics computation for benchmark results."""

from dataclasses import dataclass, field
from typing import List, Dict
import statistics

from src.config import TRIMMED_DROP_COUNT, MAX_CLICKS


@dataclass
class StepMetrics:
    """Metrics for a single step in an attempt."""
    step_index: int
    remaining_distance_before: int
    remaining_distance_after: int
    step_direction: str  # "forward", "neutral", "backwards"


@dataclass
class AttemptMetrics:
    """Full metrics for a single attempt."""
    model_id: str
    attempt_id: int
    start_title: str
    target_title: str
    solved: bool
    total_clicks: int
    best_path_length: int
    steps: List[StepMetrics] = field(default_factory=list)
    trimmed_included: bool = False  # Set by compute_trimmed_set

    @property
    def effective_clicks(self) -> int:
        """Clicks for ranking purposes (failures count as MAX_CLICKS)."""
        if self.solved:
            return self.total_clicks
        return MAX_CLICKS


@dataclass
class ModelMetrics:
    """Aggregated metrics for a single model in a benchmark run."""
    model_id: str
    attempts: List[AttemptMetrics] = field(default_factory=list)

    # Trimmed set metrics (computed)
    trimmed_attempts: List[AttemptMetrics] = field(default_factory=list)
    median_clicks: float = 0.0
    median_best_path: float = 0.0
    forward_pct: float = 0.0
    neutral_pct: float = 0.0
    backwards_pct: float = 0.0
    solve_rate: float = 0.0

    def compute_trimmed_set(self):
        """Compute trimmed set by dropping worst TRIMMED_DROP_COUNT attempts."""
        # Sort by effective clicks (best first)
        sorted_attempts = sorted(self.attempts, key=lambda a: a.effective_clicks)

        # Drop worst N attempts
        if len(sorted_attempts) > TRIMMED_DROP_COUNT:
            self.trimmed_attempts = sorted_attempts[:-TRIMMED_DROP_COUNT]
        else:
            self.trimmed_attempts = sorted_attempts

        # Mark trimmed_included in attempts
        trimmed_ids = {(a.model_id, a.attempt_id) for a in self.trimmed_attempts}
        for attempt in self.attempts:
            attempt.trimmed_included = (attempt.model_id, attempt.attempt_id) in trimmed_ids

    def compute_statistics(self):
        """Compute all statistics for this model."""
        self.compute_trimmed_set()

        if not self.trimmed_attempts:
            return

        # Median clicks (on trimmed set)
        clicks = [a.effective_clicks for a in self.trimmed_attempts]
        self.median_clicks = statistics.median(clicks)

        # Median best path (on trimmed set)
        best_paths = [a.best_path_length for a in self.trimmed_attempts]
        self.median_best_path = statistics.median(best_paths)

        # Solve rate
        solved_count = sum(1 for a in self.trimmed_attempts if a.solved)
        self.solve_rate = solved_count / len(self.trimmed_attempts) * 100

        # Direction percentages (on all steps in trimmed set)
        all_steps = []
        for attempt in self.trimmed_attempts:
            all_steps.extend(attempt.steps)

        if all_steps:
            total_steps = len(all_steps)
            forward = sum(1 for s in all_steps if s.step_direction == "forward")
            neutral = sum(1 for s in all_steps if s.step_direction == "neutral")
            backwards = sum(1 for s in all_steps if s.step_direction == "backwards")

            self.forward_pct = forward / total_steps * 100
            self.neutral_pct = neutral / total_steps * 100
            self.backwards_pct = backwards / total_steps * 100


@dataclass
class BenchmarkMetrics:
    """Complete metrics for a benchmark run across all models."""
    benchmark_name: str
    models: Dict[str, ModelMetrics] = field(default_factory=dict)

    def add_attempt(self, attempt: AttemptMetrics):
        """Add an attempt to the appropriate model."""
        if attempt.model_id not in self.models:
            self.models[attempt.model_id] = ModelMetrics(model_id=attempt.model_id)
        self.models[attempt.model_id].attempts.append(attempt)

    def compute_all_statistics(self):
        """Compute statistics for all models."""
        for model in self.models.values():
            model.compute_statistics()


def compute_direction_percentages(steps: List[StepMetrics]) -> Dict[str, float]:
    """Compute direction percentages for a list of steps.

    Returns:
        Dict with 'forward', 'neutral', 'backwards' percentages
    """
    if not steps:
        return {"forward": 0.0, "neutral": 0.0, "backwards": 0.0}

    total = len(steps)
    forward = sum(1 for s in steps if s.step_direction == "forward")
    neutral = sum(1 for s in steps if s.step_direction == "neutral")
    backwards = sum(1 for s in steps if s.step_direction == "backwards")

    return {
        "forward": forward / total * 100,
        "neutral": neutral / total * 100,
        "backwards": backwards / total * 100,
    }
