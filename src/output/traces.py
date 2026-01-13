"""Human-readable trace output for game attempts."""

from pathlib import Path
from typing import List

from src.config import MODEL_DISPLAY_NAMES
from src.benchmark.metrics import BenchmarkMetrics, AttemptMetrics


def write_attempt_trace(attempt: AttemptMetrics, output_path: Path) -> None:
    """Write a human-readable trace for a single attempt."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Game Trace",
        f"Model: {MODEL_DISPLAY_NAMES.get(attempt.model_id, attempt.model_id)}",
        f"Attempt: {attempt.attempt_id + 1}",
        f"",
        f"## Route",
        f"Start: {attempt.start_title}",
        f"Target: {attempt.target_title}",
        f"",
        f"## Result",
        f"Solved: {'Yes' if attempt.solved else 'No'}",
        f"Clicks: {attempt.total_clicks}",
        f"Best Path: {attempt.best_path_length}",
        f"Trimmed Set: {'Included' if attempt.trimmed_included else 'Excluded'}",
        f"",
        f"## Steps",
    ]

    if attempt.steps:
        for step in attempt.steps:
            direction_symbol = {
                "forward": "->",
                "neutral": "==",
                "backwards": "<-",
            }.get(step.step_direction, "??")

            lines.append(
                f"  {step.step_index + 1}. [{step.remaining_distance_before}] "
                f"{direction_symbol} [{step.remaining_distance_after}] "
                f"({step.step_direction})"
            )
    else:
        lines.append("  No steps recorded")

    output_path.write_text("\n".join(lines))


def write_model_traces(
    metrics: BenchmarkMetrics,
    output_dir: Path,
) -> None:
    """Write trace files for all attempts in a benchmark run."""
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    for model_id, model_metrics in metrics.models.items():
        model_dir = traces_dir / model_id.replace("/", "_")
        model_dir.mkdir(parents=True, exist_ok=True)

        for attempt in model_metrics.attempts:
            trace_path = model_dir / f"attempt_{attempt.attempt_id + 1:02d}.txt"
            write_attempt_trace(attempt, trace_path)


def write_summary_trace(metrics: BenchmarkMetrics, output_path: Path) -> None:
    """Write a summary trace showing all models' performance."""
    lines = [
        f"# Benchmark Summary: {metrics.benchmark_name}",
        f"",
        f"## Model Performance (Trimmed Set)",
        f"",
    ]

    for model_id, model_metrics in metrics.models.items():
        display_name = MODEL_DISPLAY_NAMES.get(model_id, model_id)
        lines.extend([
            f"### {display_name}",
            f"- Median Clicks: {model_metrics.median_clicks:.1f}",
            f"- Median Best Path: {model_metrics.median_best_path:.1f}",
            f"- Solve Rate: {model_metrics.solve_rate:.1f}%",
            f"- Forward: {model_metrics.forward_pct:.1f}%",
            f"- Neutral: {model_metrics.neutral_pct:.1f}%",
            f"- Backwards: {model_metrics.backwards_pct:.1f}%",
            f"",
        ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
