"""Find and rank trending Marathi tweets."""
import json
import logging
from typing import Any

from . import config
from .twitter_client import TwitterClient

log = logging.getLogger(__name__)


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
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for t in tweets:
        if t["id"] in already_replied:
            continue
        if t["author_followers"] < min_followers:
            continue
        if t.get("likes", 0) < config.MIN_TWEET_LIKES:
            continue
        filtered.append(t)

    for t in filtered:
        t["score"] = _score(t)

    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered


def find_top_tweets(count: int = 5) -> list[dict[str, Any]]:
    """Return top `count` ranked Marathi tweets eligible for reply."""
    client = TwitterClient()
    raw = client.search_marathi_tweets(max_results=100)
    already_replied = _load_replied_ids()

    ranked = _filter_and_rank(
        raw, already_replied, config.MIN_AUTHOR_FOLLOWERS
    )
    log.info(
        "Filtered %d -> %d tweets at follower threshold %d",
        len(raw),
        len(ranked),
        config.MIN_AUTHOR_FOLLOWERS,
    )

    # Relax if not enough
    if len(ranked) < count:
        log.info("Relaxing follower threshold to 2000")
        ranked = _filter_and_rank(raw, already_replied, 2000)
        log.info("After relax: %d tweets", len(ranked))

    top = ranked[:count]
    return [
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
        for t in top
    ]
