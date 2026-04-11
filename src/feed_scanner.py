"""Find and rank trending Marathi tweets.

This module never calls the X API more than once per invocation. The
progressive relaxation ladder below re-filters the *same* raw fetch
with looser thresholds until at least one unreplied candidate survives
— so relaxation costs zero extra API reads.
"""
import json
import logging
from typing import Any

from . import config, session_log
from .twitter_client import TwitterClient

log = logging.getLogger(__name__)


# Relaxation ladder: each row is (min_followers, min_likes, label).
# Processed in order; the first level with ≥1 unreplied candidate wins.
# Level 3 (0, 0) is the "guarantee" step: any unreplied tweet counts,
# so as long as the raw fetch returned *anything* new we always have
# a candidate to draft for.
def _relaxation_ladder() -> list[tuple[int, int, str]]:
    return [
        (config.MIN_AUTHOR_FOLLOWERS, config.MIN_TWEET_LIKES, "strict"),
        (2000, 20, "relaxed"),
        (500, 5, "loose"),
        (0, 0, "any"),
    ]


def _score(tweet: dict[str, Any]) -> int:
    return (
        tweet.get("likes", 0) * 2
        + tweet.get("retweets", 0) * 3
        + tweet.get("quotes", 0) * 5
    )


def _load_replied_ids() -> set[str]:
    path = config.REPLIED_TWEETS_FILE
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            records = json.load(f)
        return {str(r.get("tweet_id")) for r in records if r.get("tweet_id")}
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Could not load replied_tweets.json: %s", e)
        return set()


def _build_url(username: str, tweet_id: str) -> str:
    return f"https://x.com/{username or 'i'}/status/{tweet_id}"


def _filter_and_rank(
    tweets: list[dict[str, Any]],
    already_replied: set[str],
    min_followers: int,
    min_likes: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {
        "raw": len(tweets),
        "already_replied": 0,
        "below_followers": 0,
        "below_likes": 0,
        "kept": 0,
    }
    filtered: list[dict[str, Any]] = []
    for t in tweets:
        if t["id"] in already_replied:
            stats["already_replied"] += 1
            continue
        if t["author_followers"] < min_followers:
            stats["below_followers"] += 1
            continue
        if t.get("likes", 0) < min_likes:
            stats["below_likes"] += 1
            continue
        filtered.append(t)

    for t in filtered:
        t["score"] = _score(t)

    filtered.sort(key=lambda x: x["score"], reverse=True)
    stats["kept"] = len(filtered)
    return filtered, stats


def find_top_tweets(
    count: int = 5,
    session: "session_log.Session | None" = None,
    client: TwitterClient | None = None,
) -> list[dict[str, Any]]:
    """Return top ``count`` ranked Marathi tweets eligible for reply.

    Uses a single X API call and then the relaxation ladder so the
    caller is guaranteed at least one candidate whenever the raw fetch
    has anything unreplied.
    """
    client = client or TwitterClient()
    raw = client.search_marathi_tweets()
    already_replied = _load_replied_ids()

    if session is not None:
        session.record_fetched(raw)

    if not raw:
        log.info("No tweets returned from X search — nothing to rank")
        if session is not None:
            session.record_filter_stats({"raw": 0})
        return []

    ladder = _relaxation_ladder()
    ranked: list[dict[str, Any]] = []
    chosen_level = 0
    chosen_label = "strict"
    last_stats: dict[str, int] = {}

    for level, (min_f, min_l, label) in enumerate(ladder):
        ranked_try, stats = _filter_and_rank(raw, already_replied, min_f, min_l)
        last_stats = stats
        if ranked_try:
            ranked = ranked_try
            chosen_level = level
            chosen_label = label
            if level == 0:
                log.info(
                    "Strict thresholds (followers≥%d, likes≥%d) → %d candidates",
                    min_f, min_l, len(ranked_try),
                )
            else:
                log.warning(
                    "Relaxed to level %d (%s, followers≥%d, likes≥%d) → %d candidates",
                    level, label, min_f, min_l, len(ranked_try),
                )
            break

    if session is not None:
        session.record_filter_stats(last_stats)
        session.record_relaxation(chosen_level, chosen_label, len(ranked))

    top = [
        {
            "id": t["id"],
            "text": t["text"],
            "author_name": t["author_name"],
            "author_username": t["author_username"],
            "author_followers": t["author_followers"],
            "likes": t["likes"],
            "retweets": t["retweets"],
            "score": t["score"],
            "url": _build_url(t["author_username"], t["id"]),
        }
        for t in ranked[:count]
    ]

    if session is not None:
        session.record_candidates(top)

    return top
