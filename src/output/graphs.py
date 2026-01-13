"""Graph generation for benchmark results."""

from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from src.config import MODELS, MODEL_DISPLAY_NAMES
from src.benchmark.metrics import BenchmarkMetrics


# Define consistent colors for models
MODEL_COLORS = {
    "openai/gpt-5.2": "#10a37f",  # OpenAI green
    "anthropic/claude-opus-4.5": "#d4a574",  # Anthropic brown/tan
    "x-ai/grok-4.1-fast": "#1da1f2",  # X/Twitter blue
    "google/gemini-3-flash-preview": "#4285f4",  # Google blue
}

# Direction colors
DIRECTION_COLORS = {
    "forward": "#2ecc71",  # Green
    "neutral": "#f39c12",  # Yellow/orange
    "backwards": "#e74c3c",  # Red
}


def setup_style():
    """Set up clean plot style."""
    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["figure.dpi"] = 300
    plt.rcParams["font.size"] = 12


def plot_performance_comparison(
    metrics: BenchmarkMetrics,
    output_path: Path,
    title: str = "Performance (Trimmed Set)",
) -> None:
    """Plot median clicks vs best path for each model.

    Grouped bar chart showing actual median clicks and best path median.
    """
    setup_style()

    models = []
    actual_clicks = []
    best_paths = []

    for model_id in MODELS:
        if model_id in metrics.models:
            model_metrics = metrics.models[model_id]
            models.append(MODEL_DISPLAY_NAMES[model_id])
            actual_clicks.append(model_metrics.median_clicks)
            best_paths.append(model_metrics.median_best_path)

    x = range(len(models))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    bars1 = ax.bar([i - width/2 for i in x], actual_clicks, width,
                   label="Median Clicks", color="#3498db")
    bars2 = ax.bar([i + width/2 for i in x], best_paths, width,
                   label="Best Path Median", color="#95a5a6", alpha=0.7)

    ax.set_xlabel("Model")
    ax.set_ylabel("Clicks")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15, ha="right")
    ax.legend()

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}",
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_direction_distribution(
    metrics: BenchmarkMetrics,
    output_path: Path,
    title: str = "Click Direction Distribution (Trimmed Set)",
) -> None:
    """Plot stacked bar chart of forward/neutral/backwards percentages."""
    setup_style()

    models = []
    forward_pcts = []
    neutral_pcts = []
    backwards_pcts = []

    for model_id in MODELS:
        if model_id in metrics.models:
            model_metrics = metrics.models[model_id]
            models.append(MODEL_DISPLAY_NAMES[model_id])
            forward_pcts.append(model_metrics.forward_pct)
            neutral_pcts.append(model_metrics.neutral_pct)
            backwards_pcts.append(model_metrics.backwards_pct)

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(models))
    width = 0.6

    # Stacked bars
    ax.bar(x, forward_pcts, width, label="Forward", color=DIRECTION_COLORS["forward"])
    ax.bar(x, neutral_pcts, width, bottom=forward_pcts,
           label="Neutral", color=DIRECTION_COLORS["neutral"])
    ax.bar(x, backwards_pcts, width,
           bottom=[f + n for f, n in zip(forward_pcts, neutral_pcts)],
           label="Backwards", color=DIRECTION_COLORS["backwards"])

    ax.set_xlabel("Model")
    ax.set_ylabel("Percentage (%)")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15, ha="right")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 100)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_all_graphs(
    all_metrics: Dict[str, BenchmarkMetrics],
    output_dir: Path,
) -> None:
    """Generate all 6 graphs for the benchmark.

    Args:
        all_metrics: Dict mapping condition name to BenchmarkMetrics
        output_dir: Base output directory for graphs
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Graph 1: Baseline performance
    if "baseline" in all_metrics:
        plot_performance_comparison(
            all_metrics["baseline"],
            output_dir / "graph1_baseline_performance.png",
            "Baseline Performance (Trimmed Set)",
        )

    # Graph 2: Getting lost (baseline direction distribution)
    if "baseline" in all_metrics:
        plot_direction_distribution(
            all_metrics["baseline"],
            output_dir / "graph2_direction_distribution.png",
            "Click Direction Distribution - Baseline (Trimmed Set)",
        )

    # Graph 3: Post-cutoff performance
    if "cutoff" in all_metrics:
        plot_performance_comparison(
            all_metrics["cutoff"],
            output_dir / "graph3_cutoff_performance.png",
            "Post-Cutoff Performance (Trimmed Set)",
        )

    # Graph 4: Tips performance
    if "tips" in all_metrics:
        plot_performance_comparison(
            all_metrics["tips"],
            output_dir / "graph4_tips_performance.png",
            "Tips Available Performance (Trimmed Set)",
        )

    # Graph 5: Low reasoning performance
    if "low_reasoning" in all_metrics:
        plot_performance_comparison(
            all_metrics["low_reasoning"],
            output_dir / "graph5_low_reasoning_performance.png",
            "Low Reasoning Performance (Trimmed Set)",
        )

    # Graph 6: Peer pressure performance
    if "peer_pressure" in all_metrics:
        plot_performance_comparison(
            all_metrics["peer_pressure"],
            output_dir / "graph6_peer_pressure_performance.png",
            "Peer Pressure Performance (Trimmed Set)",
        )

    print(f"Generated graphs in {output_dir}")
