# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A long-running Python bot (macOS, launchd-managed) that drafts Marathi replies to trending Marathi tweets and pushes them to the user's phone via ntfy.sh for manual approval. **Nothing is ever auto-posted** — every reply requires an explicit `OK` from the user over ntfy. All scheduling is in `Asia/Kolkata`.

## Commands

Setup / development:
```bash
./setup.sh                        # create venv and install requirements.txt
./venv/bin/python health_check.py # end-to-end check: env, X search, X auth, Anthropic, ntfy, data file, launchd
./venv/bin/python -m src.main     # run the bot in the foreground (same entry launchd uses)
```

Launchd service (macOS):
```bash
./install_service.sh                                           # copies plist to ~/Library/LaunchAgents and loads it
launchctl unload ~/Library/LaunchAgents/com.akshay.marathi-responder.plist   # stop
tail -f ~/Library/Logs/marathi-responder-stdout.log            # service stdout
tail -f logs/$(date +%F).log                                   # per-day rotated app log
```

There is no test suite. `health_check.py` is the closest thing — it makes real calls to X, Anthropic, and ntfy, so it consumes API quota and will send a real notification.

## Architecture

Entry point is [src/main.py](src/main.py), which is launched as `python -m src.main` (the plist depends on this module form — package-relative imports in [src/main.py](src/main.py) will break if invoked as a script). `main()` validates env, sets up logging, prints a startup banner (including `get_me()` to confirm OAuth 1.0a works at boot), then hands off to `scheduler.run_daily_schedule()` which runs forever.

**Daily loop** ([src/scheduler.py](src/scheduler.py)): each day at midnight IST, `_generate_daily_times` picks `DAILY_REPLY_COUNT` random datetimes within `WINDOW_START`–`WINDOW_END` IST with a minimum 1-hour gap (falls back to evenly-spaced jitter if the random-sample retries fail). The loop sleeps until each slot via `_sleep_until` (which wakes every 30s so SIGTERM/SIGINT shutdown is responsive), then runs `_process_one_slot`. Per-slot errors are caught so the daemon never crashes out of the loop.

**Per-slot pipeline**:
1. [src/feed_scanner.py](src/feed_scanner.py) `find_top_tweets` calls the X search, filters out already-replied tweets (by loading [data/replied_tweets.json](data/replied_tweets.json)), applies `MIN_AUTHOR_FOLLOWERS` and `MIN_TWEET_LIKES` thresholds, scores with `likes*2 + retweets*3 + quotes*5`, and returns the top N. If the strict threshold yields too few, it relaxes `MIN_AUTHOR_FOLLOWERS` to 2000 and retries.
2. [src/claude_drafter.py](src/claude_drafter.py) `draft_reply` asks Claude (model pinned at top of file) to produce a Puneri-wit Marathi reply with the system prompt's hard rules (Devanagari, ≤250 chars, no hashtags, 1–2 emoji max, supportive if topic is sad). If the returned reply is >280 chars it does a follow-up turn asking for a shorter version, then truncates as a last resort.
3. [src/notifier.py](src/notifier.py) `send_for_approval` POSTs the draft to ntfy with `Click` set to the tweet URL, then `_poll_for_response` long-polls `GET {topic}/json?poll=1&since=...` and parses NDJSON messages. It skips its own outgoing message (matches `sent_body_stripped`) and accepts `OK`/`SKIP`/`REDO` case-insensitively as the first token of the reply. Timeout is 30 minutes; polling wakes every 15s.
4. The scheduler handles `REDO` by re-drafting (max 2 redos per slot). On `OK` it calls `TwitterClient.post_reply` and appends to `replied_tweets.json` via `_save_replied_atomic` (write-to-tmp + `os.replace` — this is the only writer, don't introduce a second one).

**X API client** ([src/twitter_client.py](src/twitter_client.py)): two tweepy `Client`s in one object — `read_client` uses **Bearer Token** for `search_recent_tweets`/`get_user`, `write_client` uses **OAuth 1.0a** (all 4 consumer+access keys) for `get_me` and `create_tweet`. Do not collapse these: the pay-per-use plan requires the bearer token for reads, and posting requires user context. Every call goes through `_call`, which handles `TooManyRequests` by sleeping until `x-rate-limit-reset` + 5s (min 15s), and retries other `TweepyException`s with linear backoff, `MAX_RETRIES=3`.

**Search query** ([src/twitter_client.py:17](src/twitter_client.py#L17)): the query is `मराठी OR पुणे OR ... lang:mr -is:retweet -is:reply`. Two constraints learned the hard way and documented in the README — (1) `lang:mr` alone is rejected by the search endpoint, so Marathi keyword OR-clauses are required alongside it; (2) `min_faves:` is not on the pay-per-use plan, so like filtering must happen in Python after the fetch. Preserve both behaviors if you touch the query.

**Config** ([src/config.py](src/config.py)): all paths derive from `PROJECT_ROOT = parent.parent of this file` so the app works regardless of cwd (launchd sets `WorkingDirectory` anyway). `validate_env()` exits with a listed-missing-vars message before logging is even configured. `DATA_DIR` and `LOGS_DIR` are created on import. The required env vars are the 5 X keys + `ANTHROPIC_API_KEY` + `NTFY_TOPIC`; `MIN_AUTHOR_FOLLOWERS`, `MIN_TWEET_LIKES`, `DAILY_REPLY_COUNT` are optional with defaults. `MY_USER_ID`/`MY_USERNAME` are hardcoded — they identify the account being posted from.

**Logging** ([src/main.py](src/main.py) `_setup_logging`): INFO to stdout (captured by launchd into `~/Library/Logs/marathi-responder-stdout.log`), DEBUG to a per-day rotating file in `logs/YYYY-MM-DD.log` with a 30-day backup. Existing handlers are cleared on setup so launchd restarts don't duplicate output.

## Hard constraints (from README — don't regress)

- Official X API v2 only. No scraping, no cookies, no unofficial endpoints.
- **Never auto-post.** Every reply must go through the ntfy approval loop. Don't add a "dry run" or "debug" path that bypasses it.
- Marathi replies must be Devanagari and ≤280 chars (the drafter targets 250 to leave headroom).
- All scheduling stays in `Asia/Kolkata` — use `ZoneInfo(config.TIMEZONE)`, never naive datetimes.
- Python must run inside the project-local `venv/` (the plist hardcodes `venv/bin/python3`).
