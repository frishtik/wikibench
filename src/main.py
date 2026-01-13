"""WikiBench CLI - Wikipedia Wiki Game Benchmark."""

import asyncio
import argparse
import sys
from pathlib import Path

from src.config import OUTPUTS_DIR
from src.benchmark.orchestrator import BenchmarkOrchestrator
from src.benchmark.conditions import BenchmarkCondition
from src.output.csv_writer import write_benchmark_csv, write_summary_csv
from src.output.graphs import generate_all_graphs
from src.output.traces import write_model_traces, write_summary_trace


async def run_sanity_check():
    """Run quick sanity check to verify setup."""
    print("Running sanity check...")
    from tests.test_sanity import main as sanity_main
    await sanity_main()


async def run_single_benchmark(condition_name: str):
    """Run a single benchmark condition."""
    condition_map = {
        "baseline": BenchmarkCondition.BASELINE,
        "cutoff": BenchmarkCondition.CUTOFF,
        "tips": BenchmarkCondition.TIPS,
        "low_reasoning": BenchmarkCondition.LOW_REASONING,
        "peer_pressure": BenchmarkCondition.PEER_PRESSURE,
    }

    if condition_name not in condition_map:
        print(f"Unknown condition: {condition_name}")
        print(f"Available: {list(condition_map.keys())}")
        return

    orchestrator = BenchmarkOrchestrator()

    # Load tips if running tips condition
    if condition_name == "tips":
        orchestrator.load_tips()

    condition = condition_map[condition_name]
    metrics = await orchestrator.run_benchmark(condition)

    # Write outputs
    output_dir = OUTPUTS_DIR / condition_name
    write_benchmark_csv(metrics, output_dir / "results.csv")
    write_summary_csv(metrics, output_dir / "summary.csv")
    write_model_traces(metrics, output_dir)
    write_summary_trace(metrics, output_dir / "summary.txt")

    print(f"\nResults written to {output_dir}")


async def run_all_benchmarks():
    """Run all 5 benchmark conditions."""
    orchestrator = BenchmarkOrchestrator()
    all_metrics = await orchestrator.run_all_benchmarks()

    # Write outputs for each condition
    for name, metrics in all_metrics.items():
        output_dir = OUTPUTS_DIR / name
        write_benchmark_csv(metrics, output_dir / "results.csv")
        write_summary_csv(metrics, output_dir / "summary.csv")
        write_model_traces(metrics, output_dir)
        write_summary_trace(metrics, output_dir / "summary.txt")

    # Generate all graphs
    graphs_dir = OUTPUTS_DIR / "graphs"
    generate_all_graphs(all_metrics, graphs_dir)

    print(f"\nAll results written to {OUTPUTS_DIR}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="WikiBench - Wikipedia Wiki Game Benchmark"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Sanity check command
    subparsers.add_parser("sanity", help="Run sanity check")

    # Benchmark commands
    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmarks")
    benchmark_parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 5 benchmark conditions",
    )
    benchmark_parser.add_argument(
        "--condition",
        choices=["baseline", "cutoff", "tips", "low_reasoning", "peer_pressure"],
        help="Run a specific benchmark condition",
    )

    # Graphs command
    graphs_parser = subparsers.add_parser("graphs", help="Generate graphs from existing data")
    graphs_parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUTS_DIR / "graphs",
        help="Output directory for graphs",
    )

    args = parser.parse_args()

    if args.command == "sanity":
        asyncio.run(run_sanity_check())
    elif args.command == "benchmark":
        if args.all:
            asyncio.run(run_all_benchmarks())
        elif args.condition:
            asyncio.run(run_single_benchmark(args.condition))
        else:
            print("Please specify --all or --condition")
            parser.print_help()
    elif args.command == "graphs":
        print("Graph regeneration from existing data not yet implemented")
        print("Run 'benchmark --all' to generate graphs with data")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
