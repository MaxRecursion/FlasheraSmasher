"""Daily random scheduling and main run loop."""
import json
import logging
import os
import random
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import claude_drafter, config, feed_scanner, notifier, session_log
from .twitter_client import TwitterClient, get_shared_client

log = logging.getLogger(__name__)

_shutdown = False


def _install_signal_handlers() -> None:
    def _handle(signum, _frame):
        global _shutdown
        log.info("Received signal %d, shutting down gracefully", signum)
        _shutdown = True

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


# ---------------------------------------------------------------------------
# replied_tweets.json IO
# ---------------------------------------------------------------------------
def _load_replied() -> list[dict[str, Any]]:
    path = config.REPLIED_TWEETS_FILE
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Could not read replied_tweets.json: %s", e)
        return []


def _save_replied_atomic(records: list[dict[str, Any]]) -> None:
    path: Path = config.REPLIED_TWEETS_FILE
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _record_reply(tweet: dict[str, Any], reply_text: str) -> None:
    records = _load_replied()
    records.append(
        {
            "tweet_id": tweet["id"],
            "author_username": tweet.get("author_username", ""),
            "original_text": tweet.get("text", ""),
            "reply_text": reply_text,
            "replied_at": datetime.now(ZoneInfo(config.TIMEZONE)).isoformat(),
            "score": tweet.get("score", 0),
        }
    )
    _save_replied_atomic(records)


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------
def _generate_daily_times(
    count: int, tz: ZoneInfo, now: datetime | None = None
) -> list[datetime]:
    """Generate `count` random datetimes today between 8AM-10PM IST,
    with at least 1 hour gap between them. Sorted chronologically."""
    if now is None:
        now = datetime.now(tz)
    day = now.date()
    start = datetime(day.year, day.month, day.day, config.WINDOW_START, tzinfo=tz)
    end = datetime(day.year, day.month, day.day, config.WINDOW_END, tzinfo=tz)

    window_seconds = int((end - start).total_seconds())
    min_gap = 3600  # 1 hour

    # Retry a few times to find a valid spread
    for _ in range(200):
        offsets = sorted(random.sample(range(window_seconds), count))
        ok = all(
            (offsets[i + 1] - offsets[i]) >= min_gap
            for i in range(len(offsets) - 1)
        )
        if ok:
            return [start + timedelta(seconds=o) for o in offsets]

    # Fallback: evenly spaced with small jitter
    step = window_seconds // (count + 1)
    return sorted(
        start + timedelta(seconds=step * (i + 1) + random.randint(-600, 600))
        for i in range(count)
    )


def _sleep_until(target: datetime) -> None:
    while not _shutdown:
        now = datetime.now(target.tzinfo)
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 30))


# ---------------------------------------------------------------------------
# Per-slot work
# ---------------------------------------------------------------------------
def _process_one_slot(
    tw: TwitterClient,
    slot_number: int,
    attempted_ids: set[str],
    trigger: str = "scheduled",
) -> None:
    session = session_log.start(trigger=trigger, slot_number=slot_number)
    log.info("=== Processing slot #%d (session %s) ===", slot_number, session.id)

    try:
        candidates = feed_scanner.find_top_tweets(
            count=10, session=session, client=tw
        )
        if not candidates:
            msg = (
                f"No candidates found in slot #{slot_number} "
                f"(fetched={session.fetched_count})"
            )
            log.info(msg)
            session.finish("no_candidates", msg)
            # Give the user visibility even when nothing was draftable
            try:
                notifier.send_info(
                    "Marathi Responder",
                    f"Slot #{slot_number}: no candidates "
                    f"(fetched {session.fetched_count} tweets, all filtered out)",
                )
            except Exception:  # noqa: BLE001
                pass
            return

        tweet = next(
            (c for c in candidates if c["id"] not in attempted_ids), None
        )
        if tweet is None:
            log.info("All candidates already attempted today")
            session.finish("skipped", "All candidates already attempted today")
            return
        attempted_ids.add(tweet["id"])
        session.record_selected(tweet)

        author = tweet.get("author_username", "")
        log.info(
            "Selected tweet %s by @%s (score=%s, likes=%s)",
            tweet["id"],
            author,
            tweet.get("score"),
            tweet.get("likes"),
        )

        draft = claude_drafter.draft_reply(
            tweet["text"],
            author or tweet.get("author_name", ""),
            session=session,
        )
        log.info("Drafted reply: %s", draft)

        response = notifier.send_for_approval(tweet, draft, slot_number)
        session.record_approval(response)

        redo_count = 0
        while response == "redo" and redo_count < 2:
            redo_count += 1
            log.info("Redo requested (%d/2), re-drafting", redo_count)
            draft = claude_drafter.draft_reply(
                tweet["text"],
                author or tweet.get("author_name", ""),
                session=session,
                is_redo=True,
            )
            log.info("New draft: %s", draft)
            response = notifier.send_for_approval(tweet, draft, slot_number)
            session.record_approval(response)

        if response == "ok":
            log.info("Approved — posting reply")
            result = tw.post_reply(tweet["id"], draft)
            posted_id = str(result.get("id", ""))
            log.info("Posted reply id=%s", posted_id)
            _record_reply(tweet, draft)
            session.record_posted(posted_id)
            session.finish("posted", f"Posted reply id={posted_id}")
        elif response == "skip":
            log.info("User skipped slot #%d", slot_number)
            session.finish("skipped", f"User skipped slot #{slot_number}")
        elif response == "timeout":
            log.info("Approval timed out for slot #%d", slot_number)
            session.finish("timeout", f"Approval timed out for slot #{slot_number}")
        else:
            log.info("Response %r — not posting", response)
            session.finish("skipped", f"Response {response!r} — not posting")
    except Exception as e:  # noqa: BLE001
        log.exception("Slot #%d failed: %s", slot_number, e)
        session.finish("error", str(e))
        raise


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def process_one_slot_now() -> None:
    """Run one reply slot on demand (used by the webui control panel).

    Runs through the full pipeline once: search → rank → draft → ntfy
    approval → post (only if user approves). Safe to call while the
    main daily loop is also running — the replied_tweets.json writer
    is atomic and the ntfy approval loop gates any posting.

    Uses the process-wide shared TwitterClient so the search-result
    cache persists across repeated UI clicks and costs no extra X
    reads within the cache TTL.
    """
    tw = get_shared_client()
    _process_one_slot(tw, slot_number=0, attempted_ids=set(), trigger="manual")


def run_daily_schedule() -> None:
    """Run forever: each day, schedule N slots at random times and process."""
    _install_signal_handlers()
    tz = ZoneInfo(config.TIMEZONE)
    tw = get_shared_client()

    while not _shutdown:
        now = datetime.now(tz)
        times = _generate_daily_times(config.DAILY_REPLY_COUNT, tz, now)
        log.info(
            "Scheduled %d slots for %s: %s",
            len(times),
            now.date().isoformat(),
            ", ".join(t.strftime("%H:%M") for t in times),
        )

        attempted_ids: set[str] = set()
        for i, slot_time in enumerate(times, start=1):
            if _shutdown:
                return
            if slot_time <= datetime.now(tz):
                log.info(
                    "Slot #%d at %s already passed — skipping",
                    i,
                    slot_time.strftime("%H:%M"),
                )
                continue
            log.info(
                "Sleeping until slot #%d at %s", i, slot_time.strftime("%H:%M")
            )
            _sleep_until(slot_time)
            if _shutdown:
                return
            try:
                _process_one_slot(tw, i, attempted_ids)
            except Exception as e:  # noqa: BLE001 — never crash loop
                log.exception("Error in slot #%d: %s", i, e)
            time.sleep(30)  # gentle pacing between slots

        # Sleep until next midnight IST
        now = datetime.now(tz)
        tomorrow = (now + timedelta(days=1)).date()
        next_midnight = datetime(
            tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, tzinfo=tz
        )
        log.info(
            "Day complete. Sleeping until %s",
            next_midnight.isoformat(),
        )
        _sleep_until(next_midnight)
