"""Load configuration from environment variables. Fails fast if required secrets are missing."""

import os
from dotenv import load_dotenv

load_dotenv()

# X / Twitter API
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Gmail SMTP
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Newsletter
NEWSLETTER_RECIPIENT = os.getenv("NEWSLETTER_RECIPIENT")

# Accounts to monitor (edit here to change the tracked list)
ACCOUNTS = [
    "levelsio", "alliekmiller", "mattshumer_", "rowancheung",
    "vikas_ai_", "ai_logician", "jamesclift", "info_with_ai",
    "sama", "OfficialLoganK",
]

# Constants
CLAUDE_MODEL = "claude-sonnet-4-20250514"
TWEET_FETCH_DAYS = 7
POST_DELAY_SECONDS = 45  # seconds between X posts (30–60 range)
MAX_POSTS_PER_WEEK = 5
SQLITE_DB_PATH = "data/raw/tweets.db"
NEWSLETTER_OUTPUT_DIR = "data/newsletter"
NEWSLETTER_LATEST_JSON = "data/newsletter/latest.json"
TEMPLATES_DIR = "templates"

# Required secrets per layer — validated at runtime, not import time
LAYER1_REQUIRED = ["X_BEARER_TOKEN", "ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "NEWSLETTER_RECIPIENT"]
LAYER2_REQUIRED = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET", "ANTHROPIC_API_KEY"]


def validate(keys: list[str]) -> None:
    """Raise EnvironmentError listing any missing secrets."""
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
