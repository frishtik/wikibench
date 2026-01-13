import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config import MAX_CLICKS, WIKIPEDIA_BASE_URL
from src.openrouter_client import chat_completion
from src.reasoning_config import ReasoningMode
from src.wikipedia.api import WikipediaAPI
from src.wikipedia.article import fetch_article_markdown
from src.wikipedia.links import extract_links_from_markdown, title_from_url
from src.game.prompts import get_system_prompt, get_user_prompt
from src.game.parser import parse_response

@dataclass
class GameStep:
    step_index: int
    current_page_title: str
    current_page_url: str
    chosen_link_markdown: str
    chosen_target_title: str
    chosen_target_url: str
    timestamp_utc: str

@dataclass
class GameResult:
    start_title: str
    target_title: str
    solved: bool
    total_clicks: int
    steps: list[GameStep] = field(default_factory=list)
    path: list[str] = field(default_factory=list)  # Titles visited

class WikiGameEngine:
    def __init__(self, api: WikipediaAPI):
        self.api = api

    async def play(
        self,
        model_id: str,
        start_title: str,
        target_title: str,
        reasoning_mode: ReasoningMode,
        system_prompt_prefix: str = "",
        max_retries: int = 3,
    ) -> GameResult:
        """Play a single game from start to target.

        Args:
            model_id: OpenRouter model ID
            start_title: Starting Wikipedia article title
            target_title: Target article to reach
            reasoning_mode: HIGH or LOW reasoning
            system_prompt_prefix: Optional prefix (for tips/peer pressure)
            max_retries: Max retries for invalid responses

        Returns:
            GameResult with all steps and outcome
        """
        current_title = start_title
        current_url = f"{WIKIPEDIA_BASE_URL}{start_title.replace(' ', '_')}"
        path = [start_title]
        steps = []

        base_system_prompt = get_system_prompt(target_title)
        system_prompt = system_prompt_prefix + base_system_prompt

        for click_num in range(MAX_CLICKS):
            # Fetch current article markdown
            try:
                _, article_markdown = await fetch_article_markdown(self.api, current_title)
            except Exception:
                # Failed to fetch article, game over
                break

            if not article_markdown:
                break

            # Extract valid links from article
            valid_links = extract_links_from_markdown(article_markdown)
            valid_urls = {link[1] for link in valid_links}  # Set of URLs

            # Build user prompt
            user_prompt = get_user_prompt(current_title, article_markdown)

            # Build messages for API call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Call model with retries
            chosen_link = None
            for retry in range(max_retries):
                response = await chat_completion(
                    model_id=model_id,
                    messages=messages,
                    reasoning_mode=reasoning_mode,
                )

                if response is None:
                    continue

                parsed = parse_response(response)
                if parsed is None:
                    continue

                link_text, link_url = parsed

                # Validate link exists in article
                if link_url in valid_urls:
                    chosen_link = (link_text, link_url)
                    break

                # Try URL normalization - sometimes models add/remove trailing slashes
                normalized_url = link_url.rstrip('/')
                for valid_url in valid_urls:
                    if valid_url.rstrip('/') == normalized_url:
                        chosen_link = (link_text, valid_url)
                        break

                if chosen_link:
                    break

            if chosen_link is None:
                # Failed to get valid response after retries
                break

            link_text, link_url = chosen_link
            next_title = title_from_url(link_url)

            # Record step
            step = GameStep(
                step_index=click_num,
                current_page_title=current_title,
                current_page_url=current_url,
                chosen_link_markdown=f"[{link_text}]({link_url})",
                chosen_target_title=next_title,
                chosen_target_url=link_url,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )
            steps.append(step)

            # Move to next page
            current_title = next_title
            current_url = link_url
            path.append(current_title)

            # Check if reached target
            if self._titles_match(current_title, target_title):
                return GameResult(
                    start_title=start_title,
                    target_title=target_title,
                    solved=True,
                    total_clicks=click_num + 1,
                    steps=steps,
                    path=path,
                )

        # Did not reach target within MAX_CLICKS
        return GameResult(
            start_title=start_title,
            target_title=target_title,
            solved=False,
            total_clicks=len(steps),
            steps=steps,
            path=path,
        )

    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two Wikipedia titles refer to the same article.

        Handles differences in spacing, underscores, and case.
        """
        def normalize(title: str) -> str:
            return title.lower().replace('_', ' ').strip()

        return normalize(title1) == normalize(title2)
