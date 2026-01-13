# Constants, model IDs, paths
import os
from pathlib import Path

# Models to benchmark
MODELS = [
    "openai/gpt-5.2",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4.1-fast",
    "google/gemini-3-flash-preview",
]

# Short display names for models (used in graphs, peer pressure)
MODEL_DISPLAY_NAMES = {
    "openai/gpt-5.2": "GPT-5.2",
    "anthropic/claude-opus-4.5": "Claude Opus 4.5",
    "x-ai/grok-4.1-fast": "Grok 4.1 Fast",
    "google/gemini-3-flash-preview": "Gemini 3 Flash",
}

# Game settings
MAX_CLICKS = 30
ATTEMPTS_PER_MODEL = 15
TRIMMED_DROP_COUNT = 3  # Drop worst 3 attempts for trimmed set

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# API settings
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Wikipedia settings
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"  # Include trailing slash

# Cutoff date for post-cutoff benchmark
CUTOFF_DATE = "2025-09-01"
