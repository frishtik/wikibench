"""OpenRouter API client for chat completions.

Provides async HTTP client with retry logic and rate limiting support.
"""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from src.reasoning_config import ReasoningMode, get_reasoning_params, get_anthropic_reasoning_budget

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors."""

    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Raised when rate limited by OpenRouter API."""

    pass


class OpenRouterAPIError(OpenRouterError):
    """Raised for non-retryable API errors."""

    pass


def _should_retry_exception(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry."""
    if isinstance(exception, OpenRouterRateLimitError):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout)):
        return True
    return False


@retry(
    retry=retry_if_exception_type((OpenRouterRateLimitError, httpx.ConnectError, httpx.ReadTimeout)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def chat_completion(
    model_id: str,
    messages: list[dict],
    reasoning_mode: ReasoningMode,
    max_tokens: int = 4096,
) -> str:
    """Send chat completion request to OpenRouter.

    Args:
        model_id: The model identifier (e.g., "anthropic/claude-opus-4.5").
        messages: List of message dicts with "role" and "content" keys.
        reasoning_mode: The reasoning mode to use for the request.
        max_tokens: Maximum tokens for the response.

    Returns:
        The assistant's response text.

    Raises:
        OpenRouterRateLimitError: When rate limited (triggers retry).
        OpenRouterAPIError: For non-retryable API errors after retries exhausted.
        OpenRouterError: For other API-related errors.
    """
    reasoning_params = get_reasoning_params(model_id, reasoning_mode)

    # Handle Anthropic's special requirement: max_tokens must be higher than reasoning budget
    effective_max_tokens = max_tokens
    reasoning_budget = get_anthropic_reasoning_budget(model_id, reasoning_mode)
    if reasoning_budget is not None:
        # Ensure request max_tokens exceeds reasoning budget
        if effective_max_tokens <= reasoning_budget:
            effective_max_tokens = reasoning_budget + max_tokens
            logger.debug(
                f"Adjusted max_tokens from {max_tokens} to {effective_max_tokens} "
                f"to exceed reasoning budget of {reasoning_budget}"
            )

    payload: dict[str, Any] = {
        "model": model_id,
        "messages": messages,
        "max_tokens": effective_max_tokens,
    }

    # Merge reasoning parameters into payload
    if reasoning_params:
        payload.update(reasoning_params)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/wikibench",
        "X-Title": "WikiBench",
    }

    endpoint = f"{OPENROUTER_BASE_URL}/chat/completions"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(endpoint, json=payload, headers=headers)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                logger.warning(f"Rate limited by OpenRouter. Retry-After: {retry_after}")
                raise OpenRouterRateLimitError(
                    f"Rate limited by OpenRouter API. Retry-After: {retry_after}"
                )

            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise OpenRouterRateLimitError(
                    f"Rate limited by OpenRouter API: {e.response.text}"
                ) from e
            elif e.response.status_code in (500, 502, 503, 504):
                logger.warning(f"Server error from OpenRouter: {e.response.status_code}")
                raise
            else:
                logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
                raise OpenRouterAPIError(
                    f"OpenRouter API error: {e.response.status_code} - {e.response.text}"
                ) from e

    data = response.json()

    if "error" in data:
        error_msg = data["error"].get("message", str(data["error"]))
        logger.error(f"OpenRouter returned error: {error_msg}")
        raise OpenRouterAPIError(f"OpenRouter API returned error: {error_msg}")

    try:
        choices = data.get("choices", [])
        if not choices:
            raise OpenRouterError("No choices returned in API response")

        message = choices[0].get("message", {})
        content = message.get("content")

        if content is None:
            raise OpenRouterError("No content in response message")

        return content

    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse OpenRouter response: {data}")
        raise OpenRouterError(f"Failed to parse API response: {e}") from e
