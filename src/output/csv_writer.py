"""CSV output generation for benchmark results."""

import csv
from pathlib import Path
from typing import List
from datetime import datetime

from src.config import WIKIPEDIA_BASE_URL
from src.benchmark.metrics import BenchmarkMetrics, AttemptMetrics, StepMetrics


def write_benchmark_csv(metrics: BenchmarkMetrics, output_path: Path) -> None:
    """Write detailed CSV for a benchmark run.

    Each row represents a step in an attempt.
    Attempts without steps still get one row with empty step fields.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "benchmark_run_name",
        "model_id",
        "attempt_id",
        "start_page_title",
        "start_page_url",
        "target_page_title",
        "target_page_url",
        "solved",
        "total_clicks",
        "best_path_length",
        "trimmed_included",
        "step_index",
        "current_page_title",
        "current_page_url",
        "remaining_distance_before",
        "remaining_distance_after",
        "step_direction",
        "timestamp_utc",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for model_metrics in metrics.models.values():
            for attempt in model_metrics.attempts:
                base_row = {
                    "benchmark_run_name": metrics.benchmark_name,
                    "model_id": attempt.model_id,
                    "attempt_id": attempt.attempt_id,
                    "start_page_title": attempt.start_title,
                    "start_page_url": f"{WIKIPEDIA_BASE_URL}{attempt.start_title.replace(' ', '_')}",
                    "target_page_title": attempt.target_title,
                    "target_page_url": f"{WIKIPEDIA_BASE_URL}{attempt.target_title.replace(' ', '_')}",
                    "solved": str(attempt.solved).lower(),
                    "total_clicks": attempt.total_clicks,
                    "best_path_length": attempt.best_path_length,
                    "trimmed_included": str(attempt.trimmed_included).lower(),
                }

                if attempt.steps:
                    for step in attempt.steps:
                        row = base_row.copy()
                        row.update({
                            "step_index": step.step_index + 1,  # 1-indexed
                            "current_page_title": "",  # We don't store this in StepMetrics
                            "current_page_url": "",
                            "remaining_distance_before": step.remaining_distance_before,
                            "remaining_distance_after": step.remaining_distance_after,
                            "step_direction": step.step_direction,
                            "timestamp_utc": datetime.utcnow().isoformat(),
                        })
                        writer.writerow(row)
                else:
                    # Write at least one row for attempts with no steps
                    row = base_row.copy()
                    row.update({
                        "step_index": "",
                        "current_page_title": "",
                        "current_page_url": "",
                        "remaining_distance_before": "",
                        "remaining_distance_after": "",
                        "step_direction": "",
                        "timestamp_utc": "",
                    })
                    writer.writerow(row)


def write_summary_csv(metrics: BenchmarkMetrics, output_path: Path) -> None:
    """Write summary CSV with per-model statistics."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "benchmark_run_name",
        "model_id",
        "total_attempts",
        "trimmed_attempts",
        "median_clicks",
        "median_best_path",
        "solve_rate",
        "forward_pct",
        "neutral_pct",
        "backwards_pct",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for model_metrics in metrics.models.values():
            writer.writerow({
                "benchmark_run_name": metrics.benchmark_name,
                "model_id": model_metrics.model_id,
                "total_attempts": len(model_metrics.attempts),
                "trimmed_attempts": len(model_metrics.trimmed_attempts),
                "median_clicks": round(model_metrics.median_clicks, 2),
                "median_best_path": round(model_metrics.median_best_path, 2),
                "solve_rate": round(model_metrics.solve_rate, 2),
                "forward_pct": round(model_metrics.forward_pct, 2),
                "neutral_pct": round(model_metrics.neutral_pct, 2),
                "backwards_pct": round(model_metrics.backwards_pct, 2),
            })
