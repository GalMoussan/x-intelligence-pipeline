# x-intelligence-pipeline

## Project Purpose
Weekly AI intelligence pipeline: scrapes 10 X accounts → Claude analysis → HTML newsletter email → autonomous X posting agent.

## Stack
- Python 3.11+, Tweepy, Anthropic SDK, CrewAI, smtplib, SQLite
- Scheduling: GitHub Actions (Sunday 7am UTC)
- Config: .env only

## Session Start Protocol
1. Read TASK_BOARD.md first
2. State which tasks are DONE vs IN_PROGRESS vs TODO
3. Never start a task already marked DONE
4. Work one task at a time, mark complete before moving on

## Architecture
- Layer 1: scraper.py → analyzer.py → newsletter.py → sender.py
- Layer 2: agents.py (CrewAI) → poster.py
- Handoff file: data/newsletter/latest.json (Layer 1 output → Layer 2 input)

## Key Constraints
- X API free tier: max ~800 reads/month → weekly fetch only, never daily
- Posting: 3–5 tweets/week max, 30–60s delay between posts
- All secrets in .env, never committed
- Always use dry-run flag when testing: python main.py --dry-run

## Accounts List
Edit in config/settings.py → ACCOUNTS list

## Testing
- python main.py --layer1 --dry-run   # fetch + analyze, no email sent
- python main.py --layer2 --dry-run   # generate posts, no X posting
- python main.py --layer1             # full Layer 1 run
- python main.py --layer2             # full Layer 2 run
