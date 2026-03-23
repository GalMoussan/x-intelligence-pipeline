# x-intelligence-pipeline

A weekly AI intelligence pipeline with two layers:

- **Layer 1** — Scrapes 10 curated X accounts every Sunday, sends the corpus to Claude for analysis, and delivers an HTML newsletter via Gmail.
- **Layer 2** — A CrewAI posting agent (Content Strategist → Post Writer → Publisher) that reads the newsletter output and posts 3–5 native X posts across the week.

Runs automatically via GitHub Actions every Sunday at 7:00am UTC.

---

## Requirements

- Python 3.11+
- X Developer account (free tier)
- Anthropic API key
- Gmail account with an App Password

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/GalMoussan/x-intelligence-pipeline.git
cd x-intelligence-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. X Developer account

1. Go to [developer.twitter.com](https://developer.twitter.com) and create a free account.
2. Create a new Project + App.
3. Under **Keys and Tokens**, generate:
   - API Key & Secret
   - Access Token & Secret (set App permissions to **Read and Write**)
   - Bearer Token

### 3. Gmail App Password

1. Enable 2-Step Verification on your Google account.
2. Go to **Google Account → Security → App passwords**.
3. Create a new app password (name it anything, e.g. "x-pipeline").
4. Copy the 16-character password.

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

```env
# X / Twitter API
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
X_BEARER_TOKEN=your_bearer_token

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Gmail SMTP
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Newsletter delivery
NEWSLETTER_RECIPIENT=you@email.com
```

### 5. Initialise the database

```bash
python main.py --init-db
```

---

## Running locally

```bash
# Dry run — no email sent, no X posts made
python main.py --layer1 --dry-run
python main.py --layer2 --dry-run
python main.py --layer1 --layer2 --dry-run

# Full Layer 1 — scrape, analyze, send newsletter
python main.py --layer1

# Full Layer 2 — generate posts, human-review prompt, then post to X
python main.py --layer2

# Full pipeline
python main.py --layer1 --layer2

# Skip human-review gate (CI/automation)
python main.py --layer2 --no-review
```

---

## Deploy to GitHub Actions

### 1. Push the repo

```bash
git remote add origin https://github.com/GalMoussan/x-intelligence-pipeline.git
git push -u origin main
```

### 2. Add secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add each key from `.env.example`:

| Secret | Description |
|--------|-------------|
| `X_BEARER_TOKEN` | For reading tweets (Layer 1) |
| `X_API_KEY` | For posting tweets (Layer 2) |
| `X_API_SECRET` | For posting tweets (Layer 2) |
| `X_ACCESS_TOKEN` | For posting tweets (Layer 2) |
| `X_ACCESS_TOKEN_SECRET` | For posting tweets (Layer 2) |
| `ANTHROPIC_API_KEY` | Claude API |
| `GMAIL_ADDRESS` | Gmail sender address |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `NEWSLETTER_RECIPIENT` | Destination email for newsletter |

### 3. Trigger manually (first test)

Go to **Actions → Weekly AI Pipeline → Run workflow** to trigger a manual run before the Sunday cron kicks in.

Newsletter HTML and post logs are uploaded as workflow artifacts (retained 90 days).

---

## Architecture

```
Layer 1 (Sunday 7am)
  scraper.py     ← Tweepy, fetches last 7 days per account, stores to SQLite
  analyzer.py    ← Claude API, extracts insights, saves latest.json
  newsletter.py  ← Jinja2 HTML email builder
  sender.py      ← Gmail SMTP delivery

         ↓ data/newsletter/latest.json (handoff)

Layer 2 (same run)
  agents.py      ← CrewAI: Content Strategist, Post Writer, Publisher
  tasks.py       ← Task pipeline wired to crew
  poster.py      ← X API v2 POST /2/tweets, delay, logging
```

## Customising accounts

Edit `ACCOUNTS` in `config/settings.py`:

```python
ACCOUNTS = [
    "levelsio", "alliekmiller", "mattshumer_", "rowancheung",
    "vikas_ai_", "ai_logician", "jamesclift", "info_with_ai",
    "sama", "OfficialLoganK",
]
```

## Rate limits

- **X free tier**: ~800 reads/month. Weekly fetch of 10 accounts × ≤500 tweets = well within limits.
- **Posting**: capped at 5 posts/week with a 45-second delay between each.

---

## Data

| Path | Contents |
|------|----------|
| `data/raw/tweets.db` | SQLite — all fetched tweets + run audit log |
| `data/newsletter/latest.json` | Latest newsletter output (Layer 1 → Layer 2 handoff) |
| `data/newsletter/newsletter-DATE.md` | Dated Markdown copy for archiving |
| `data/newsletter/post_log.jsonl` | Append-only log of every X post attempt |

`data/` is gitignored — never committed.
