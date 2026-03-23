"""x-intelligence-pipeline — CLI entrypoint.

Usage:
    python main.py --layer1              # scrape → analyze → email
    python main.py --layer2              # read latest.json → post to X
    python main.py --layer1 --layer2     # full pipeline
    python main.py --layer1 --dry-run    # fetch + analyze, no email sent
    python main.py --layer2 --dry-run    # generate posts, no X posting
    python main.py --init-db             # initialise / migrate SQLite schema
"""

import argparse
import sys
from datetime import datetime, timezone


def _week_date() -> str:
    """Return a human-readable week date string, e.g. 'March 23, 2026'."""
    return datetime.now(timezone.utc).strftime("%B %-d, %Y")


def run_layer1(dry_run: bool) -> bool:
    """Execute the full Layer 1 pipeline. Returns True on success."""
    from layer1 import scraper, analyzer, newsletter, sender
    from config import settings

    week_date = _week_date()
    print(f"\n=== Layer 1 — Week of {week_date} ===")

    # Step 1: scrape
    print("\n[1/4] Scraping tweets…")
    corpus = scraper.fetch_tweets(dry_run=dry_run)

    # Step 2: analyze
    print("\n[2/4] Analyzing with Claude…")
    analysis = analyzer.analyze_tweets(corpus=corpus, week_date=week_date, dry_run=dry_run)

    # Step 3: build newsletter HTML
    print("\n[3/4] Building newsletter HTML…")
    html = newsletter.build_newsletter(analysis=analysis, corpus=corpus)

    # Step 4: send
    subject = f"Weekly AI Money Brief – Week of {week_date}"
    print(f"\n[4/4] Sending newsletter → {settings.NEWSLETTER_RECIPIENT or '(dry-run)'}…")
    success = sender.send_newsletter(
        html_content=html,
        subject=subject,
        dry_run=dry_run,
    )

    if success:
        print("\nLayer 1 complete ✓")
    else:
        print("\nLayer 1 finished with send errors.", file=sys.stderr)

    return success


def run_layer2(dry_run: bool, no_review: bool = False) -> bool:
    """Execute the full Layer 2 pipeline. Returns True on success."""
    import json
    from pathlib import Path
    from layer2 import agents, tasks, poster
    from config import settings

    print("\n=== Layer 2 — CrewAI Posting Agent ===")

    # ── Handoff: read latest.json written by Layer 1 ──────────────────
    latest = Path(settings.NEWSLETTER_LATEST_JSON)
    if not latest.exists():
        print(f"Error: handoff file not found at {latest}. Run --layer1 first.", file=sys.stderr)
        return False

    newsletter_data = json.loads(latest.read_text())
    print(f"  Loaded newsletter: Week of {newsletter_data.get('week_date', 'unknown')}")

    if dry_run:
        # Skip the LLM crew entirely in dry-run — use placeholder posts
        print("[dry-run] Skipping CrewAI agents.")
        placeholder_posts = [
            "AI tools for building income streams are multiplying fast. Here are the ones worth your time this week.",
            "Focus of the week: pick one AI workflow and automate it end-to-end before Sunday.",
        ]
        poster.post_tweets(posts=placeholder_posts, dry_run=True, human_review=False)
        print("\nLayer 2 complete ✓  (dry-run)")
        return True

    # ── Step 1: build crew + wire tasks ───────────────────────────────
    print("\n[1/3] Building CrewAI crew…")
    crew = agents.create_crew()
    tasks.create_tasks(crew, newsletter_data)

    # ── Step 2: run the agent pipeline ────────────────────────────────
    print("\n[2/3] Running agents (Strategist → Writer → Publisher)…")
    result = crew.kickoff()

    # Extract the Publisher's final output (last task result)
    raw_output = str(result.raw) if hasattr(result, "raw") else str(result)
    print(f"  Crew output ({len(raw_output)} chars): {raw_output[:120]}…")

    approved_posts = poster._parse_posts_from_crew_output(raw_output)
    if not approved_posts:
        print("Warning: could not parse posts from crew output. Check crew verbose logs.", file=sys.stderr)
        return False
    print(f"  Parsed {len(approved_posts)} approved post(s).")

    # ── Step 3: human review + post ───────────────────────────────────
    print("\n[3/3] Posting to X…")
    posted_ids = poster.post_tweets(
        posts=approved_posts,
        dry_run=False,
        human_review=not no_review,
    )

    print(f"\nLayer 2 complete ✓  ({len(posted_ids)} post(s) published)")
    return True


def init_db() -> None:
    """Initialise or migrate the SQLite database."""
    from layer1 import db
    print("Initialising database…")
    conn = db.init()
    version = db.get_schema_version(conn)
    conn.close()
    print(f"Done. Schema version: {version}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="x-intelligence-pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--layer1", action="store_true", help="Run Layer 1 (scrape → analyze → email)")
    parser.add_argument("--layer2", action="store_true", help="Run Layer 2 (CrewAI posting agent)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending email or posting")
    parser.add_argument("--no-review", action="store_true", help="Skip human review gate (for CI/cron)")
    parser.add_argument("--init-db", action="store_true", help="Initialise / migrate SQLite schema and exit")
    args = parser.parse_args()

    if args.init_db:
        init_db()
        return

    if not args.layer1 and not args.layer2:
        parser.print_help()
        sys.exit(0)

    if args.dry_run:
        print("** DRY RUN MODE — no email or X posts will be sent **")

    success = True

    if args.layer1:
        success = run_layer1(dry_run=args.dry_run) and success

    if args.layer2:
        success = run_layer2(dry_run=args.dry_run, no_review=args.no_review) and success

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
