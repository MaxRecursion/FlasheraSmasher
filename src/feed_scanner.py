"""Find and rank trending Marathi tweets.

This module never calls the X API more than once per invocation. The
progressive relaxation ladder below re-filters the *same* raw fetch
with looser thresholds until at least one unreplied candidate survives
— so relaxation costs zero extra API reads.
"""
import json
import logging
import re
from typing import Any

from . import config, session_log
from .twitter_client import TwitterClient

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hindi language guard
# ---------------------------------------------------------------------------
# Twitter's lang:mr filter is unreliable — it regularly passes through Hindi
# tweets because many Marathi search keywords also appear in Hindi text.
# We guard against this by scanning candidate tweets for Hindi-specific
# function words that do not exist in Marathi.  Any tweet containing at
# least one of these markers is almost certainly Hindi and is discarded.
#
# The key discriminators:
#   है  / हैं  — Hindi 3rd-person present copula  (Marathi: आहे / आहेत)
#   नहीं       — Hindi negation                   (Marathi: नाही)
#   था / थे / थी — Hindi past-tense copula        (Marathi: होता / होते / होती)
#   मैं / मुझे  — Hindi 1st-person pronouns       (Marathi: मी / मला)
#   हूं / हूँ   — Hindi "I am"                   (Marathi: आहे)
#   लेकिन      — Hindi "but"                      (Marathi: पण / परंतु)
#   क्योंकि    — Hindi "because"                  (Marathi: कारण / म्हणून)
#   इसलिए      — Hindi "therefore"                (Marathi: म्हणून)
_HINDI_MARKERS: frozenset[str] = frozenset({
    "है", "हैं", "नहीं",
    "था", "थे", "थी",
    "मैं", "मुझे", "हूं", "हूँ",
    "लेकिन", "क्योंकि", "इसलिए",
    "उनका", "उनके", "उनकी", "उन्हें", "उनसे", "उन्होंने",
    "कीजिए", "दीजिए",
})

# Split on whitespace, Devanagari danda/double-danda, and common punctuation
_TOKEN_SPLIT_RE = re.compile(r'[\s\u0964\u0965,।॥!?@#&*()\[\]{}<>]+')


def _is_hindi(text: str) -> bool:
    """Return True if *text* appears to be Hindi rather than Marathi.

    Tokenises the text and checks for Hindi-specific function words that
    do not appear in Marathi.  A single match is sufficient to classify
    the tweet as Hindi — false positives on genuine Marathi are
    extremely unlikely given the chosen marker set.
    """
    if not text:
        return False
    tokens = set(_TOKEN_SPLIT_RE.split(text))
    tokens.discard("")
    return bool(tokens & _HINDI_MARKERS)


# Relaxation ladder: each row is (min_followers, min_likes, label).
# Processed in order; the first level with ≥1 unseen candidate wins.
# With the lowered default floor (100 followers, 0 likes) the ladder
# collapses to two steps — strict config thresholds, then an absolute
# zero-floor safety net so a raw fetch that returned anything new is
# guaranteed to produce a candidate list.
def _relaxation_ladder() -> list[tuple[int, int, str]]:
    return [
        (config.MIN_AUTHOR_FOLLOWERS, config.MIN_TWEET_LIKES, "strict"),
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


def _load_seen_ids() -> set[str]:
    """Return every tweet id the bot has already *attempted* — posted,
    skipped, timed out, or rejected by the Pune/Marathi classifier.

    This is distinct from ``replied_tweets.json`` (successful posts
    only); the two sets are unioned by ``find_top_tweets`` so the same
    candidate never surfaces twice across runs, slots, or restarts.
    """
    path = config.SEEN_TWEETS_FILE
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            records = json.load(f)
        return {str(r.get("tweet_id")) for r in records if r.get("tweet_id")}
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Could not load seen_tweets.json: %s", e)
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
        "hindi_skipped": 0,
        "below_followers": 0,
        "below_likes": 0,
        "kept": 0,
    }
    filtered: list[dict[str, Any]] = []
    for t in tweets:
        if t["id"] in already_replied:
            stats["already_replied"] += 1
            continue
        if _is_hindi(t.get("text", "")):
            stats["hindi_skipped"] += 1
            log.debug(
                "Skipping Hindi tweet %s by @%s",
                t.get("id"), t.get("author_username", "?"),
            )
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
    # Union of successfully-replied + every previously attempted tweet
    # (skipped, timed out, classifier-rejected). Ensures the same
    # candidate isn't re-surfaced after a SKIP.
    already_replied = _load_replied_ids() | _load_seen_ids()

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
