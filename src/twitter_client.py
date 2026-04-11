"""X API v2 client wrapper using tweepy.

Two auth modes:
  - Bearer Token: for reading/searching tweets
  - OAuth 1.0a:   for posting replies (user context)
"""
import logging
import time
from typing import Any

import tweepy

from . import config

log = logging.getLogger(__name__)

SEARCH_QUERY = (
    "मराठी OR पुणे OR महाराष्ट्र OR मुंबई OR भारत OR सरकार OR लोक "
    "OR नमस्कार OR आज OR भाऊ lang:mr -is:retweet -is:reply"
)

TWEET_FIELDS = ["id", "text", "author_id", "created_at", "public_metrics"]
USER_FIELDS = ["id", "name", "username", "public_metrics", "verified"]
EXPANSIONS = ["author_id"]

MAX_RETRIES = 3


class TwitterClient:
    def __init__(self) -> None:
        # Bearer client — used for search / reads
        self.read_client = tweepy.Client(
            bearer_token=config.X_BEARER_TOKEN,
            wait_on_rate_limit=False,
        )
        # OAuth 1.0a user-context client — used for posting
        self.write_client = tweepy.Client(
            consumer_key=config.X_CONSUMER_KEY,
            consumer_secret=config.X_CONSUMER_SECRET,
            access_token=config.X_ACCESS_TOKEN,
            access_token_secret=config.X_ACCESS_SECRET,
            wait_on_rate_limit=False,
        )

    # ------------------------------------------------------------------
    # Rate-limit-aware invoker
    # ------------------------------------------------------------------
    def _call(self, fn, *args, **kwargs):
        """Invoke a tweepy method with rate-limit + retry handling."""
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except tweepy.TooManyRequests as e:
                last_exc = e
                reset = None
                try:
                    reset = int(e.response.headers.get("x-rate-limit-reset", "0"))
                except Exception:
                    reset = 0
                sleep_for = max(reset - int(time.time()), 15) + 5
                log.warning(
                    "Rate limited on attempt %d/%d. Sleeping %ds until reset.",
                    attempt,
                    MAX_RETRIES,
                    sleep_for,
                )
                time.sleep(sleep_for)
            except tweepy.TweepyException as e:
                last_exc = e
                log.warning(
                    "Tweepy error on attempt %d/%d: %s", attempt, MAX_RETRIES, e
                )
                time.sleep(5 * attempt)
        assert last_exc is not None
        raise last_exc

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    def get_me(self) -> dict[str, Any]:
        """Return OAuth-authenticated user info."""
        resp = self._call(self.write_client.get_me, user_fields=USER_FIELDS)
        if resp.data is None:
            raise RuntimeError("get_me() returned no data")
        u = resp.data
        return {
            "id": str(u.id),
            "name": u.name,
            "username": u.username,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search_marathi_tweets(self, max_results: int = 100) -> list[dict[str, Any]]:
        """Search recent Marathi tweets using bearer token.

        Returns a list of dicts with tweet + author info merged in.
        """
        # X search_recent_tweets: max_results per page is 10..100
        per_page = min(max(max_results, 10), 100)
        resp = self._call(
            self.read_client.search_recent_tweets,
            query=SEARCH_QUERY,
            max_results=per_page,
            tweet_fields=TWEET_FIELDS,
            user_fields=USER_FIELDS,
            expansions=EXPANSIONS,
        )

        if not resp or resp.data is None:
            log.info("search_recent_tweets returned no tweets")
            return []

        # Build author lookup from includes
        authors: dict[str, Any] = {}
        includes = getattr(resp, "includes", None) or {}
        for u in includes.get("users", []) or []:
            authors[str(u.id)] = u

        results: list[dict[str, Any]] = []
        for t in resp.data:
            author = authors.get(str(t.author_id))
            metrics = t.public_metrics or {}
            author_followers = 0
            author_name = ""
            author_username = ""
            if author is not None:
                author_name = getattr(author, "name", "") or ""
                author_username = getattr(author, "username", "") or ""
                ametrics = getattr(author, "public_metrics", None) or {}
                author_followers = int(ametrics.get("followers_count", 0) or 0)

            results.append(
                {
                    "id": str(t.id),
                    "text": t.text or "",
                    "author_id": str(t.author_id),
                    "author_name": author_name,
                    "author_username": author_username,
                    "author_followers": author_followers,
                    "created_at": str(getattr(t, "created_at", "") or ""),
                    "likes": int(metrics.get("like_count", 0) or 0),
                    "retweets": int(metrics.get("retweet_count", 0) or 0),
                    "replies": int(metrics.get("reply_count", 0) or 0),
                    "quotes": int(metrics.get("quote_count", 0) or 0),
                }
            )
        log.info("Fetched %d Marathi tweets from search", len(results))
        return results

    # ------------------------------------------------------------------
    # Author follower lookup
    # ------------------------------------------------------------------
    def get_author_followers(self, author_id: str) -> int:
        resp = self._call(
            self.read_client.get_user,
            id=author_id,
            user_fields=["public_metrics"],
        )
        if resp is None or resp.data is None:
            return 0
        metrics = getattr(resp.data, "public_metrics", None) or {}
        return int(metrics.get("followers_count", 0) or 0)

    # ------------------------------------------------------------------
    # Post reply
    # ------------------------------------------------------------------
    def post_reply(self, tweet_id: str, reply_text: str) -> dict[str, Any]:
        """Post a reply to a tweet using OAuth 1.0a user context."""
        resp = self._call(
            self.write_client.create_tweet,
            text=reply_text,
            in_reply_to_tweet_id=tweet_id,
        )
        if resp is None or resp.data is None:
            raise RuntimeError("create_tweet returned no data")
        data = resp.data
        return {
            "id": str(data.get("id")),
            "text": data.get("text", ""),
        }
