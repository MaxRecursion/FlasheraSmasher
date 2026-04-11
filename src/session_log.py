"""Persistent session log for reply-slot runs.

Each invocation of ``_process_one_slot`` (scheduled or manual via webui)
creates a ``Session`` which is persisted as its own JSON file under
``data/sessions/<id>.json``. One file per session means the launchd
daemon and the webui process never collide on concurrent writes and
the UI never has to merge partial state from separate writers.

Each session captures the entire story of one run:

- how many tweets were pulled from the X API search
- a light-weight preview of every fetched tweet (id, author, engagement)
- the filter breakdown (how many dropped for each reason)
- which relaxation level ended up being used (strict → any)
- the tweet that was finally selected
- every Claude call made (draft / shorten / redo) with the exact
  system + user prompts sent and the full response that came back
- the ntfy approval response
- the posted tweet id (if any) and the final outcome
- a free-form event timeline

The webui reads these files for the Sessions panel so the user can see
exactly what happened on any run without digging through log files.
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import config

log = logging.getLogger(__name__)

SESSIONS_DIR = config.DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Cap on retained session files — oldest are pruned on each new session.
MAX_SESSIONS = 200

_SAFE_ID = re.compile(r"[^A-Za-z0-9_\-]")


def _now_iso() -> str:
    return datetime.now(ZoneInfo(config.TIMEZONE)).isoformat()


def _now_clock() -> str:
    return datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S")


def _new_id() -> str:
    stamp = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


class Session:
    """In-memory session that persists every update to a single JSON file."""

    def __init__(self, trigger: str, slot_number: int) -> None:
        self.id = _new_id()
        self.trigger = trigger                 # "scheduled" | "manual"
        self.slot_number = slot_number
        self.started_at = _now_iso()
        self.ended_at: str | None = None
        self.status = "running"                # running | posted | skipped | timeout | error | no_candidates
        self.outcome = ""

        # Fetch stage
        self.fetched_count = 0
        self.fetched_tweets: list[dict[str, Any]] = []

        # Filter stage
        self.filter_stats: dict[str, int] = {}
        self.relaxation_level = 0
        self.relaxation_label = "strict"
        self.candidates_after_filter = 0
        self.candidate_previews: list[dict[str, Any]] = []

        # Selection
        self.selected_tweet: dict[str, Any] | None = None

        # Claude
        self.claude_calls: list[dict[str, Any]] = []

        # Approval / post
        self.approval_response: str | None = None
        self.posted_tweet_id: str | None = None

        # Timeline
        self.events: list[dict[str, Any]] = []

        self.event("info", f"Session started (trigger={trigger}, slot={slot_number})")

    # ------------------------------------------------------------------
    # Mutators — each one persists to disk
    # ------------------------------------------------------------------
    def event(self, level: str, text: str) -> None:
        self.events.append({"ts": _now_clock(), "level": level, "text": text})
        self._save()

    def record_fetched(self, tweets: list[dict[str, Any]]) -> None:
        self.fetched_count = len(tweets)
        self.fetched_tweets = [
            {
                "id": t.get("id"),
                "author_username": t.get("author_username", ""),
                "author_followers": t.get("author_followers", 0),
                "likes": t.get("likes", 0),
                "retweets": t.get("retweets", 0),
                "text_preview": (t.get("text") or "")[:200],
            }
            for t in tweets[:60]  # cap on persisted previews
        ]
        self.event("info", f"Pulled {self.fetched_count} tweets from X search")

    def record_filter_stats(self, stats: dict[str, int]) -> None:
        self.filter_stats = dict(stats)
        breakdown = ", ".join(f"{k}={v}" for k, v in stats.items() if v)
        if breakdown:
            self.event("info", f"Filter breakdown — {breakdown}")

    def record_relaxation(self, level: int, label: str, survivors: int) -> None:
        self.relaxation_level = level
        self.relaxation_label = label
        self.candidates_after_filter = survivors
        self.event(
            "warn" if level > 0 else "info",
            f"Relaxation={label} (level {level}) → {survivors} eligible candidates",
        )

    def record_candidates(self, candidates: list[dict[str, Any]]) -> None:
        self.candidate_previews = [
            {
                "id": c.get("id"),
                "author_username": c.get("author_username", ""),
                "author_followers": c.get("author_followers", 0),
                "likes": c.get("likes", 0),
                "retweets": c.get("retweets", 0),
                "score": c.get("score", 0),
                "text_preview": (c.get("text") or "")[:200],
            }
            for c in candidates[:10]
        ]
        self._save()

    def record_selected(self, tweet: dict[str, Any]) -> None:
        self.selected_tweet = {
            "id": tweet.get("id"),
            "author_username": tweet.get("author_username", ""),
            "author_name": tweet.get("author_name", ""),
            "text": tweet.get("text", ""),
            "likes": tweet.get("likes", 0),
            "retweets": tweet.get("retweets", 0),
            "score": tweet.get("score", 0),
            "url": tweet.get("url", ""),
        }
        self.event(
            "info",
            f"Selected tweet {tweet.get('id')} by @{tweet.get('author_username','?')} "
            f"(likes={tweet.get('likes',0)}, score={tweet.get('score',0)})",
        )

    def record_claude_call(
        self,
        attempt: int,
        kind: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response: str,
    ) -> None:
        self.claude_calls.append({
            "attempt": attempt,
            "kind": kind,               # "draft" | "redo" | "shorten"
            "model": model,
            "ts": _now_clock(),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response": response,
            "response_chars": len(response),
        })
        preview = response.replace("\n", " ")[:100]
        self.event("info", f"Claude {kind} #{attempt} → {len(response)} chars: {preview}")

    def record_approval(self, response: str) -> None:
        self.approval_response = response
        self.event("info", f"ntfy approval response: {response}")

    def record_posted(self, tweet_id: str) -> None:
        self.posted_tweet_id = tweet_id
        self.event("info", f"Posted reply id={tweet_id}")

    def finish(self, status: str, message: str = "") -> None:
        self.status = status
        if message:
            self.outcome = message
        self.ended_at = _now_iso()
        tail = f"{status}" + (f" — {message}" if message else "")
        self.events.append({"ts": _now_clock(), "level": "info", "text": f"Session ended: {tail}"})
        self._save()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger": self.trigger,
            "slot_number": self.slot_number,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "outcome": self.outcome,
            "fetched_count": self.fetched_count,
            "fetched_tweets": self.fetched_tweets,
            "filter_stats": self.filter_stats,
            "relaxation_level": self.relaxation_level,
            "relaxation_label": self.relaxation_label,
            "candidates_after_filter": self.candidates_after_filter,
            "candidate_previews": self.candidate_previews,
            "selected_tweet": self.selected_tweet,
            "claude_calls": self.claude_calls,
            "approval_response": self.approval_response,
            "posted_tweet_id": self.posted_tweet_id,
            "events": self.events,
        }

    def _path(self) -> Path:
        return SESSIONS_DIR / f"{self.id}.json"

    def _save(self) -> None:
        try:
            path = self._path()
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except OSError as e:
            log.warning("Failed to save session %s: %s", self.id, e)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
def start(trigger: str, slot_number: int) -> Session:
    """Create a new Session and prune old files."""
    _prune_old_sessions()
    return Session(trigger=trigger, slot_number=slot_number)


def _prune_old_sessions() -> None:
    try:
        files = sorted(SESSIONS_DIR.glob("*.json"))
    except OSError:
        return
    excess = len(files) - MAX_SESSIONS
    if excess <= 0:
        return
    for f in files[:excess]:
        try:
            f.unlink()
        except OSError:
            pass


def list_recent(limit: int = 25) -> list[dict[str, Any]]:
    """Return the most recent N sessions, newest first.

    Returns a summary dict for each session so large response bodies
    don't get pulled into the list view — the full record (incl. claude
    prompts and fetched tweets) is loaded via :func:`load`.
    """
    try:
        files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for f in files[:limit]:
        try:
            with f.open("r", encoding="utf-8") as h:
                data = json.load(h)
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "id": data.get("id"),
            "trigger": data.get("trigger"),
            "slot_number": data.get("slot_number"),
            "started_at": data.get("started_at"),
            "ended_at": data.get("ended_at"),
            "status": data.get("status"),
            "outcome": data.get("outcome"),
            "fetched_count": data.get("fetched_count", 0),
            "candidates_after_filter": data.get("candidates_after_filter", 0),
            "relaxation_label": data.get("relaxation_label", ""),
            "claude_calls_count": len(data.get("claude_calls") or []),
            "approval_response": data.get("approval_response"),
            "posted_tweet_id": data.get("posted_tweet_id"),
            "selected_author": (data.get("selected_tweet") or {}).get("author_username"),
        })
    return out


def load(session_id: str) -> dict[str, Any] | None:
    """Load a single session's full record by id."""
    safe = _SAFE_ID.sub("", session_id or "")
    if not safe:
        return None
    path = SESSIONS_DIR / f"{safe}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
