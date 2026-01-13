"""Reasoning configuration for different models.

Provides a clean abstraction for reasoning modes across OpenRouter models.
Based on: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
"""
from enum import Enum
from typing import Any


class ReasoningMode(Enum):
    """Reasoning intensity levels for benchmark runs."""
    HIGHEST = "highest"
    LOWEST = "lowest"


# Model-specific reasoning configurations using OpenRouter's normalized format
# The "reasoning" object format: {"effort": str} or {"max_tokens": int}, plus "exclude": bool
MODEL_REASONING_CONFIG: dict[str, dict[str, dict[str, Any]]] = {
    "openai/gpt-5.2": {
        "highest": {"reasoning": {"effort": "xhigh", "exclude": True}},
        "lowest": {"reasoning": {"effort": "none", "exclude": True}},
    },
    "anthropic/claude-opus-4.5": {
        # Anthropic uses max_tokens budget (min 1024, max 128000)
        # Using 16384 for highest as it's practical for this task while still being high
        "highest": {"reasoning": {"max_tokens": 16384, "exclude": True}},
        "lowest": {"reasoning": {"max_tokens": 1024, "exclude": True}},
    },
    "x-ai/grok-4.1-fast": {
        "highest": {"reasoning": {"effort": "high", "exclude": True}},
        "lowest": {"reasoning": {"effort": "low", "exclude": True}},
    },
    "google/gemini-3-flash-preview": {
        "highest": {"reasoning": {"effort": "high", "exclude": True}},
        "lowest": {"reasoning": {"effort": "minimal", "exclude": True}},
    },
}


def get_reasoning_params(model_id: str, mode: ReasoningMode) -> dict[str, Any]:
    """Get the reasoning parameters for a specific model and mode.

    Args:
        model_id: The full model identifier (e.g., "openai/gpt-5.2")
        mode: The reasoning intensity level (HIGHEST or LOWEST)

    Returns:
        Dictionary with "reasoning" key containing model-specific params

    Raises:
        ValueError: If model_id is not found in configuration
    """
    if model_id not in MODEL_REASONING_CONFIG:
        raise ValueError(
            f"Unknown model: {model_id}. "
            f"Available models: {list(MODEL_REASONING_CONFIG.keys())}"
        )

    return MODEL_REASONING_CONFIG[model_id][mode.value]


def get_anthropic_reasoning_budget(model_id: str, mode: ReasoningMode) -> int | None:
    """Get the reasoning token budget for Anthropic models.

    Returns None for non-Anthropic models.
    Used to adjust max_tokens in API calls.
    """
    if not model_id.startswith("anthropic/"):
        return None

    params = get_reasoning_params(model_id, mode)
    return params.get("reasoning", {}).get("max_tokens")
