"""Layer 1: Claude API analysis — extract insights from raw tweet corpus."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from config import settings

SYSTEM_PROMPT = """You are an elite AI monetization analyst. From the X posts below, extract:

1. Top 3–5 actionable insights or tools for making money with AI this week.
2. One "Focus of the Week" recommendation for someone building AI income streams.
3. 2–3 raw examples or quotes worth highlighting (cite the author handle).
4. Any emerging trends or warnings in the AI space.

Output in clean Markdown structured for a newsletter titled:
"Weekly AI Money Brief – Week of [DATE]"

Be direct, opinionated, and concrete. No fluff."""

DRY_RUN_MARKDOWN = """## Weekly AI Money Brief – Week of {week_date}

> **[DRY RUN — no API call made]**

### Top Insights
1. Placeholder insight one
2. Placeholder insight two

### Focus of the Week
Placeholder focus recommendation.

### Highlights
- @sama: "Placeholder quote"

### Trends & Warnings
Placeholder trends.
"""


def _build_user_message(corpus: dict[str, list[dict]], week_date: str) -> str:
    """Flatten corpus into a single prompt string for Claude."""
    lines = [f"Week of {week_date}\n"]
    for username, tweets in corpus.items():
        if not tweets:
            continue
        lines.append(f"\n--- @{username} ---")
        for t in tweets:
            text = t["text"].replace("\n", " ")
            lines.append(f"  [{t['created_at'][:10]}] {text}")
    return "\n".join(lines)


def _save_output(markdown: str, week_date: str) -> None:
    """Write latest.json and a dated markdown file to data/newsletter/."""
    out_dir = Path(settings.NEWSLETTER_OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "week_date": week_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markdown": markdown,
    }

    # Always overwrite latest.json (Layer 2 handoff file)
    latest_path = Path(settings.NEWSLETTER_LATEST_JSON)
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # Also save a dated copy for auditing
    safe_date = week_date.replace(" ", "-").replace(",", "")
    dated_path = out_dir / f"newsletter-{safe_date}.md"
    dated_path.write_text(markdown)

    print(f"  Output saved → {latest_path} and {dated_path}")


def analyze_tweets(
    corpus: dict[str, list[dict]],
    week_date: str,
    dry_run: bool = False,
) -> dict:
    """
    Send the tweet corpus to Claude and extract newsletter insights.

    Args:
        corpus:    Output from scraper.fetch_tweets() — {username: [tweet_dict]}
        week_date: Human-readable date string, e.g. "March 23, 2026"
        dry_run:   If True, skip the API call and return a placeholder result.

    Returns:
        {"week_date": str, "markdown": str, "generated_at": str}
    """
    if dry_run:
        print("[dry-run] Skipping Claude API call.")
        markdown = DRY_RUN_MARKDOWN.format(week_date=week_date)
        _save_output(markdown, week_date)
        return {
            "week_date": week_date,
            "markdown": markdown,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    settings.validate(["ANTHROPIC_API_KEY"])

    total_tweets = sum(len(v) for v in corpus.values())
    print(f"Sending {total_tweets} tweets to Claude ({settings.CLAUDE_MODEL})…")

    user_message = _build_user_message(corpus, week_date)
    system = SYSTEM_PROMPT.replace("[DATE]", week_date)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    markdown = message.content[0].text
    print(f"  Claude response: {len(markdown)} chars, stop_reason={message.stop_reason}")

    _save_output(markdown, week_date)

    return {
        "week_date": week_date,
        "markdown": markdown,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
