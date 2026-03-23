"""Layer 2: X API posting with human-review gate, inter-post delay, and tweet ID logging."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import tweepy

from config import settings

POST_LOG_PATH = "data/newsletter/post_log.jsonl"


def _get_client() -> tweepy.Client:
    """Return an OAuth 1.0a Tweepy client with write access."""
    return tweepy.Client(
        consumer_key=settings.X_API_KEY,
        consumer_secret=settings.X_API_SECRET,
        access_token=settings.X_ACCESS_TOKEN,
        access_token_secret=settings.X_ACCESS_TOKEN_SECRET,
    )


def _log_post(post: str, tweet_id: str, dry_run: bool) -> None:
    """Append a JSON line to the post log for auditing."""
    Path(POST_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "tweet_id": tweet_id,
        "text": post,
        "dry_run": dry_run,
    }
    with open(POST_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _human_review(posts: list[str]) -> list[str]:
    """
    Interactive gate: show each post and ask approve / skip / quit.
    Returns the subset of posts the user approved.
    """
    print("\n── Human Review ─────────────────────────────────────")
    print(f"  {len(posts)} post(s) queued for review.")
    print("  Commands: [a]pprove  [s]kip  [q]uit\n")

    approved = []
    for i, post in enumerate(posts, 1):
        char_count = len(post)
        print(f"  [{i}/{len(posts)}] ({char_count} chars)")
        print(f"  ┌{'─' * 60}")
        for line in post.splitlines():
            print(f"  │ {line}")
        print(f"  └{'─' * 60}")

        while True:
            choice = input("  → ").strip().lower()
            if choice in ("a", "approve", ""):
                approved.append(post)
                print("  ✓ Approved\n")
                break
            elif choice in ("s", "skip"):
                print("  ✗ Skipped\n")
                break
            elif choice in ("q", "quit"):
                print("  Quitting review. Approved so far will be posted.")
                return approved
            else:
                print("  Enter a / s / q")

    print("── Review complete ──────────────────────────────────\n")
    return approved


def _parse_posts_from_crew_output(raw_output: str) -> list[str]:
    """
    Extract the JSON array of posts from the Publisher agent's output.
    Handles output wrapped in markdown code fences.
    """
    text = raw_output.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        posts = json.loads(text)
        if isinstance(posts, list):
            return [str(p).strip() for p in posts if str(p).strip()]
    except json.JSONDecodeError:
        pass

    # Fallback: extract anything that looks like a JSON array
    import re
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            posts = json.loads(match.group())
            if isinstance(posts, list):
                return [str(p).strip() for p in posts if str(p).strip()]
        except json.JSONDecodeError:
            pass

    return []


def post_tweets(
    posts: list[str],
    dry_run: bool = False,
    human_review: bool = True,
) -> list[str]:
    """
    Gate → review → post each approved tweet with a delay between posts.

    Args:
        posts:        List of post strings (from Publisher agent output or parsed JSON).
        dry_run:      If True, log and print without calling the X API.
        human_review: If True, prompt for approval before each post.

    Returns:
        List of tweet IDs for all successfully posted tweets.
    """
    if not posts:
        print("No posts to publish.")
        return []

    # Enforce hard limit
    capped = posts[:settings.MAX_POSTS_PER_WEEK]
    if len(capped) < len(posts):
        print(f"  Capped to {settings.MAX_POSTS_PER_WEEK} posts (MAX_POSTS_PER_WEEK).")

    # Validate length
    oversized = [p for p in capped if len(p) > 280]
    if oversized:
        print(f"  Warning: {len(oversized)} post(s) exceed 280 chars and will be skipped.")
        capped = [p for p in capped if len(p) <= 280]

    if not capped:
        print("No valid posts remain after validation.")
        return []

    # Human review gate
    to_post = _human_review(capped) if human_review and not dry_run else capped

    if not to_post:
        print("No posts approved.")
        return []

    if not dry_run:
        settings.validate(["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"])
        client = _get_client()

    posted_ids: list[str] = []

    for i, post in enumerate(to_post, 1):
        if dry_run:
            fake_id = f"dry-run-{i}"
            print(f"[dry-run] Would post ({len(post)} chars): {post[:80]}{'…' if len(post) > 80 else ''}")
            _log_post(post, fake_id, dry_run=True)
            posted_ids.append(fake_id)
        else:
            try:
                response = client.create_tweet(text=post)
                tweet_id = str(response.data["id"])
                print(f"  Posted tweet {i}/{len(to_post)} — id={tweet_id}")
                _log_post(post, tweet_id, dry_run=False)
                posted_ids.append(tweet_id)
            except tweepy.TweepyException as e:
                print(f"  Failed to post tweet {i}: {e}")
                _log_post(post, "ERROR", dry_run=False)

        # Delay between posts (skip after last one)
        if i < len(to_post):
            delay = settings.POST_DELAY_SECONDS
            print(f"  Waiting {delay}s before next post…")
            time.sleep(delay)

    print(f"\nPosted {len(posted_ids)}/{len(to_post)} tweet(s).")
    return posted_ids
