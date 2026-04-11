# marathi-tweet-responder

A 24/7 Python bot for macOS that drafts witty Marathi replies to trending
Marathi tweets. Drafts are produced by the Anthropic Claude API and sent
to your phone via ntfy.sh for manual approval — nothing is auto-posted.

## How it works

1. Each day at midnight IST, 5 random times between 08:00 and 22:00 IST are
   generated (minimum 1-hour gap between slots).
2. At each slot, the bot searches for trending Marathi tweets via the X API
   v2 (Bearer Token auth), filters by author followers and engagement, and
   picks the top-scored candidate.
3. Claude drafts a Marathi reply in Puneri-wit style.
4. A push notification is sent to your ntfy topic with the draft and the
   tweet URL.
5. You reply `OK`, `SKIP`, or `REDO` on ntfy. The bot posts the reply via
   X API v2 (OAuth 1.0a) only if you approve.

## Hard constraints

- Official X API v2 only — no scraping, no cookies.
- Never auto-posts; always waits for your ntfy approval.
- Marathi replies under 280 chars, Devanagari script.
- All scheduling in `Asia/Kolkata`.
- Python runs inside a project-local venv.

## Setup

```bash
cd ~/Projects/marathi-tweet-responder
./setup.sh                 # creates venv and installs deps
cp .env.example .env       # then edit .env and fill in credentials
./venv/bin/python health_check.py
```

## Running as a launchd service

```bash
./install_service.sh
launchctl list | grep marathi
tail -f ~/Library/Logs/marathi-responder-stdout.log
```

Uninstall:

```bash
launchctl unload ~/Library/LaunchAgents/com.akshay.marathi-responder.plist
rm ~/Library/LaunchAgents/com.akshay.marathi-responder.plist
```

## Project layout

```
marathi-tweet-responder/
├── venv/
├── src/
│   ├── main.py
│   ├── twitter_client.py
│   ├── claude_drafter.py
│   ├── feed_scanner.py
│   ├── notifier.py
│   ├── scheduler.py
│   └── config.py
├── data/replied_tweets.json
├── logs/
├── .env.example
├── requirements.txt
├── setup.sh
├── install_service.sh
├── com.akshay.marathi-responder.plist
├── health_check.py
└── README.md
```

## ntfy control words

Reply to the notification with one of:

- `OK` — post the draft to X
- `SKIP` — skip this slot
- `REDO` — ask Claude for a new draft (max 2 redos per slot)

## Notes / constraints discovered during testing

- `lang:mr` alone is rejected by the X search endpoint; the bot includes
  Marathi keyword OR-clauses alongside `lang:mr`.
- `min_faves:` is not available on the pay-per-use plan; filtering by
  likes happens in Python after fetching results.
- Search uses Bearer Token; posting uses OAuth 1.0a (all 4 consumer +
  access keys).
