# WikiBench - Wikipedia Wiki Game Benchmark

A comprehensive benchmark comparing LLM performance on the Wikipedia "wiki game" - navigating from one Wikipedia article to another using only hyperlinks.

## Overview

The Wikipedia game challenges players to navigate from a starting article to a target article by clicking only the links within each article. This benchmark tests how well different AI models perform at this task, measuring:

- **Navigation efficiency** - How many clicks to reach the target
- **Strategic decision-making** - Forward vs. backward navigation choices
- **Knowledge utilization** - Whether reasoning capabilities help

## Models Tested

| Model | Provider |
|-------|----------|
| `openai/gpt-5.2` | OpenAI |
| `anthropic/claude-opus-4.5` | Anthropic |
| `x-ai/grok-4.1-fast` | xAI |
| `google/gemini-3-flash-preview` | Google |

## Benchmark Conditions

The benchmark runs 5 different conditions:

1. **Baseline** - Standard gameplay with highest reasoning effort
2. **Post-cutoff** - Only articles created after 2025-09-01 (tests knowledge recency)
3. **Tips Available** - Models receive tips they generated after baseline runs
4. **Low Reasoning** - Reduced reasoning effort
5. **Peer Pressure** - Models are told other models achieved optimal paths (not true)

Each condition runs 15 attempts per model with:
- Maximum 30 clicks per attempt
- Trimmed set analysis (drop worst 3 attempts)

## Installation

```bash
# Clone the repository
git clone https://github.com/frishtik/wikibench.git
cd wikibench

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Or create a `.env` file:

```
OPENROUTER_API_KEY=your_key_here
```

## Usage

### Run Sanity Check

Verify the setup works:

```bash
python -m src.main sanity
```

### Run All Benchmarks

Run all 5 benchmark conditions:

```bash
python -m src.main benchmark --all
```

### Run Single Condition

Run a specific benchmark:

```bash
python -m src.main benchmark --condition baseline
python -m src.main benchmark --condition cutoff
python -m src.main benchmark --condition tips
python -m src.main benchmark --condition low_reasoning
python -m src.main benchmark --condition peer_pressure
```

## Outputs

Each benchmark run generates:

### Directory Structure

```
outputs/
├── baseline/
│   ├── results.csv          # Detailed step-by-step data
│   ├── summary.csv          # Per-model statistics
│   ├── summary.txt          # Human-readable summary
│   ├── tips/                # Model tips (baseline only)
│   │   ├── openai_gpt-5.2.txt
│   │   └── ...
│   └── traces/              # Per-attempt game traces
│       ├── openai_gpt-5.2/
│       │   ├── attempt_01.txt
│       │   └── ...
│       └── ...
├── cutoff/
├── tips/
├── low_reasoning/
├── peer_pressure/
└── graphs/
    ├── graph1_baseline_performance.png
    ├── graph2_direction_distribution.png
    ├── graph3_cutoff_performance.png
    ├── graph4_tips_performance.png
    ├── graph5_low_reasoning_performance.png
    └── graph6_peer_pressure_performance.png
```

### CSV Schema

The detailed `results.csv` contains one row per step with:

| Field | Description |
|-------|-------------|
| `benchmark_run_name` | Condition name |
| `model_id` | Full model identifier |
| `attempt_id` | Attempt number (0-14) |
| `start_page_title` | Starting Wikipedia article |
| `target_page_title` | Target Wikipedia article |
| `solved` | Whether target was reached |
| `total_clicks` | Number of clicks (30 for failures) |
| `best_path_length` | Optimal path length |
| `trimmed_included` | In trimmed set (top 12) |
| `step_index` | Step number (1-30) |
| `remaining_distance_before` | Distance to target before step |
| `remaining_distance_after` | Distance to target after step |
| `step_direction` | forward/neutral/backwards |

### Graphs

All graphs are generated at 300 DPI with clear labels:

1. **Performance comparison** - Median clicks vs optimal path
2. **Direction distribution** - Stacked bar of forward/neutral/backwards %
3-6. Performance comparison for each condition

## Technical Details

### Reasoning Mode Abstraction

The benchmark uses a clean abstraction for reasoning modes across providers:

```python
from src.reasoning_config import ReasoningMode, get_reasoning_params

# Get params for any model
params = get_reasoning_params("openai/gpt-5.2", ReasoningMode.HIGHEST)
# Returns: {"reasoning": {"effort": "xhigh", "exclude": True}}
```

### Model-Specific Reasoning

| Model | Highest | Lowest |
|-------|---------|--------|
| GPT-5.2 | `effort: xhigh` | `effort: none` |
| Claude Opus 4.5 | `max_tokens: 128000` | `max_tokens: 1024` |
| Grok 4.1 Fast | `effort: high` | `effort: low` |
| Gemini 3 Flash | `effort: high` | `effort: minimal` |

All modes use `exclude: True` to hide reasoning traces from output.

### BFS Path Finding

The benchmark computes optimal paths using BFS with caching:

```python
from src.wikipedia.pathfinder import PathFinder

async with WikipediaAPI() as api:
    pf = PathFinder(api)
    shortest = await pf.compute_shortest_path("Dog", "Animal")
```

### Parallelization

Benchmark attempts run in parallel (default: 8 concurrent) to minimize runtime:

```python
orchestrator = BenchmarkOrchestrator(max_concurrent=8)
results = await orchestrator.run_all_benchmarks()
```

## Metrics

### Trimmed Set

For each model, the worst 3 attempts are dropped (failures count as 30 clicks). Statistics are computed on the remaining 12 attempts.

### Step Direction Classification

Each navigation step is classified as:
- **Forward** - Distance to target decreased
- **Neutral** - Distance unchanged
- **Backwards** - Distance increased

## Development

### Running Tests

```bash
# Sanity check (no API key needed)
python tests/test_sanity.py

# Integration test (API key needed)
python tests/test_integration.py
```

### Project Structure

```
src/
├── config.py              # Constants and settings
├── reasoning_config.py    # Reasoning mode abstraction
├── openrouter_client.py   # OpenRouter API client
├── wikipedia/
│   ├── api.py             # MediaWiki API client
│   ├── article.py         # Article fetching/markdown
│   ├── links.py           # Link extraction
│   ├── pathfinder.py      # BFS shortest path
│   └── sampler.py         # Random article sampling
├── game/
│   ├── engine.py          # Game loop
│   ├── prompts.py         # Prompt templates
│   └── parser.py          # Response parsing
├── benchmark/
│   ├── conditions.py      # Benchmark configurations
│   ├── metrics.py         # Statistics computation
│   ├── attempt.py         # Single attempt runner
│   └── orchestrator.py    # Parallel execution
└── output/
    ├── csv_writer.py      # CSV generation
    ├── graphs.py          # Visualization
    └── traces.py          # Human-readable traces
```

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

## Acknowledgments

Built with:
- [OpenRouter](https://openrouter.ai/) for unified LLM API access
- [Wikipedia MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page)
- [matplotlib](https://matplotlib.org/) and [seaborn](https://seaborn.pydata.org/) for visualizations
