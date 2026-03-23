"""Layer 1: X API scraper — fetch tweets from monitored accounts, store to SQLite."""

import json
from datetime import datetime, timezone, timedelta

import tweepy

from config import settings
from layer1 import db


def _get_client() -> tweepy.Client:
    """Return an authenticated Tweepy client using Bearer Token (read-only)."""
    return tweepy.Client(bearer_token=settings.X_BEARER_TOKEN, wait_on_rate_limit=True)


def _resolve_user_ids(client: tweepy.Client, usernames: list[str]) -> dict[str, str]:
    """Resolve a list of usernames to {username: user_id} via a single batch call."""
    response = client.get_users(usernames=usernames, user_fields=["id", "username"])
    if not response.data:
        return {}
    return {u.username.lower(): str(u.id) for u in response.data}


def _fetch_user_tweets(
    client: tweepy.Client,
    user_id: str,
    username: str,
    since: datetime,
    conn,
) -> list[dict]:
    """Fetch tweets for one user since `since`, persist to SQLite, return list of dicts."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    tweet_fields = ["created_at", "public_metrics", "text"]

    paginator = tweepy.Paginator(
        client.get_users_tweets,
        id=user_id,
        start_time=since,
        tweet_fields=tweet_fields,
        max_results=100,
        limit=5,  # max 5 pages = 500 tweets per account — well within free-tier limits
    )

    tweets = []
    for page in paginator:
        if not page.data:
            continue
        for tweet in page.data:
            row = {
                "id": str(tweet.id),
                "author_id": user_id,
                "username": username,
                "text": tweet.text,
                "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                "fetched_at": fetched_at,
                "metrics": json.dumps(tweet.public_metrics) if tweet.public_metrics else None,
            }
            conn.execute(
                """
                INSERT OR REPLACE INTO tweets
                    (id, author_id, username, text, created_at, fetched_at, metrics)
                VALUES
                    (:id, :author_id, :username, :text, :created_at, :fetched_at, :metrics)
                """,
                row,
            )
            tweets.append(row)

    conn.commit()
    return tweets


def fetch_tweets(
    accounts: list[str] | None = None,
    days: int = settings.TWEET_FETCH_DAYS,
    dry_run: bool = False,
) -> dict[str, list[dict]]:
    """
    Fetch the last `days` days of tweets for each account in `accounts`.
    Stores results to SQLite at settings.SQLITE_DB_PATH.
    Returns {username: [tweet_dict, ...]} for all accounts.

    In dry_run mode, skips the API call and returns an empty corpus.
    """
    if accounts is None:
        accounts = settings.ACCOUNTS

    if dry_run:
        print("[dry-run] Skipping X API fetch.")
        return {a: [] for a in accounts}

    settings.validate(["X_BEARER_TOKEN"])

    since = datetime.now(timezone.utc) - timedelta(days=days)
    client = _get_client()
    conn = db.init()
    run_id = db.log_run_start(conn, dry_run=False)

    try:
        print(f"Resolving user IDs for {len(accounts)} accounts…")
        user_map = _resolve_user_ids(client, accounts)
        missing = [a for a in accounts if a.lower() not in user_map]
        if missing:
            print(f"  Warning: could not resolve usernames: {missing}")

        corpus: dict[str, list[dict]] = {}
        for username in accounts:
            uid = user_map.get(username.lower())
            if not uid:
                corpus[username] = []
                continue
            print(f"  Fetching tweets for @{username}…")
            tweets = _fetch_user_tweets(client, uid, username, since, conn)
            corpus[username] = tweets
            print(f"    → {len(tweets)} tweets stored")

        total = sum(len(v) for v in corpus.values())
        db.log_run_finish(conn, run_id, accounts=len(accounts), tweets=total)
        print(f"Scrape complete. {total} tweets across {len(accounts)} accounts.")
        return corpus

    except Exception as e:
        db.log_run_finish(conn, run_id, accounts=0, tweets=0, error=str(e))
        raise

    finally:
        conn.close()
