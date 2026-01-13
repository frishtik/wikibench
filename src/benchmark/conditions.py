"""Benchmark condition configurations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict

from src.reasoning_config import ReasoningMode


class BenchmarkCondition(Enum):
    """The 5 benchmark conditions."""
    BASELINE = "baseline"
    CUTOFF = "cutoff"
    TIPS = "tips"
    LOW_REASONING = "low_reasoning"
    PEER_PRESSURE = "peer_pressure"


@dataclass
class ConditionConfig:
    """Configuration for a benchmark condition."""
    name: str
    reasoning_mode: ReasoningMode
    post_cutoff_only: bool = False
    use_tips: bool = False
    use_peer_pressure: bool = False
    collect_tips: bool = False  # Only baseline collects tips

    @property
    def output_dir_name(self) -> str:
        """Directory name for outputs."""
        return self.name


# Pre-defined condition configurations
CONDITIONS: Dict[BenchmarkCondition, ConditionConfig] = {
    BenchmarkCondition.BASELINE: ConditionConfig(
        name="baseline",
        reasoning_mode=ReasoningMode.HIGHEST,
        collect_tips=True,
    ),
    BenchmarkCondition.CUTOFF: ConditionConfig(
        name="cutoff",
        reasoning_mode=ReasoningMode.HIGHEST,
        post_cutoff_only=True,
    ),
    BenchmarkCondition.TIPS: ConditionConfig(
        name="tips",
        reasoning_mode=ReasoningMode.HIGHEST,
        use_tips=True,
    ),
    BenchmarkCondition.LOW_REASONING: ConditionConfig(
        name="low_reasoning",
        reasoning_mode=ReasoningMode.LOWEST,
    ),
    BenchmarkCondition.PEER_PRESSURE: ConditionConfig(
        name="peer_pressure",
        reasoning_mode=ReasoningMode.HIGHEST,
        use_peer_pressure=True,
    ),
}


def get_condition_config(condition: BenchmarkCondition) -> ConditionConfig:
    """Get configuration for a benchmark condition."""
    return CONDITIONS[condition]
