# TASK_BOARD — x-intelligence-pipeline

_Last updated: 2026-03-23_

---

## ✅ DONE

- [x] **T01** — Scaffold project structure (all folders + empty files)

---

## 🔄 IN PROGRESS
_(empty at project start)_

---

## 📋 TODO

### LAYER 1 — Scraper + Newsletter

- [ ] **T01** — Scaffold project structure (all folders + empty files)
- [x] **T02** — config/settings.py: load all env vars, ACCOUNTS list, constants
- [x] **T03** — .env.example with all required keys documented
- [x] **T04** — layer1/scraper.py: Tweepy OAuth2, username→userID lookup, fetch last 7 days of tweets per account, store to SQLite
- [x] **T05** — layer1/analyzer.py: send raw tweet corpus to Claude API, extract insights using the analyst system prompt, return structured Markdown + JSON
- [x] **T06** — layer1/newsletter.py: render Jinja2 HTML template with Claude output + top source posts + links
- [x] **T07** — layer1/sender.py: Gmail SMTP delivery with error handling and retry
- [x] **T08** — templates/newsletter.html: responsive inline-CSS HTML email template
- [x] **T09** — data/raw/ SQLite schema init + migration script
- [x] **T10** — main.py: CLI entrypoint with --layer1, --layer2, --dry-run flags
- [x] **T11** — Layer 1 end-to-end dry-run test + fix

### LAYER 2 — CrewAI Posting Agent

- [x] **T12** — layer2/agents.py: define Content Strategist, Post Writer, Publisher agents
- [x] **T13** — layer2/tasks.py: define tasks for each agent, reads from data/newsletter/latest.json
- [x] **T14** — layer2/poster.py: X API POST /2/tweets with delay, human-review flag, tweet ID logging
- [x] **T15** — Wire Layer 1 → Layer 2 handoff via data/newsletter/latest.json
- [x] **T16** — Layer 2 end-to-end dry-run test + fix

### INFRA

- [x] **T17** — .github/workflows/weekly_pipeline.yml: Sunday 7am UTC cron, runs both layers
- [x] **T18** — README.md: full setup guide (X Developer account, .env, Gmail app password, deploy to GitHub Actions)
- [x] **T19** — .gitignore: exclude .env, data/, __pycache__, *.db
- [ ] **T20** — Final: full pipeline smoke test, commit, push to github.com/squanchy667/x-intelligence-pipeline

---

## 🚫 BLOCKED
_(empty at project start)_

---

## Notes
- Start with T01 → T02 → T03 before writing any functional code
- Layer 2 only begins after T11 is marked DONE
- Never skip the dry-run flags during development
