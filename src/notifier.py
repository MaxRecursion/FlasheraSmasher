"""ntfy.sh push notifications + response polling."""
import json
import logging
import time
from typing import Any

import requests

from . import config

log = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 15
POLL_TIMEOUT_SEC = 30 * 60  # 30 minutes
VALID_RESPONSES = {"ok", "skip", "redo"}


def _topic_url() -> str:
    return f"{config.NTFY_BASE_URL}/{config.NTFY_TOPIC}"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _build_body(tweet_data: dict[str, Any], draft_reply: str) -> str:
    tweet_text = _truncate(tweet_data.get("text", ""), 150)
    return (
        f"Tweet: {tweet_text}\n\n"
        f"Draft reply: {draft_reply}\n\n"
        "👍 Reply OK to approve\n"
        "❌ Reply SKIP to skip\n"
        "🔄 Reply REDO for new draft"
    )


def send_for_approval(
    tweet_data: dict[str, Any],
    draft_reply: str,
    number_today: int,
) -> str:
    """Send an approval notification to ntfy and poll for response.

    Returns one of: "ok", "skip", "redo", "timeout".
    """
    body = _build_body(tweet_data, draft_reply)
    title = f"🐦 Reply #{number_today}: @{tweet_data.get('author_username', '')}"
    headers = {
        "Title": title,
        "Click": tweet_data.get("url", ""),
        "Priority": "4",
        "Tags": "bird",
    }

    sent_at = int(time.time())
    try:
        resp = requests.post(
            _topic_url(),
            data=body.encode("utf-8"),
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("Failed to send ntfy notification: %s", e)
        return "timeout"

    log.info("Sent approval notification: %s", title)
    return _poll_for_response(sent_at, body)


def _poll_for_response(since: int, sent_body: str) -> str:
    """Poll ntfy for an approval reply. Returns ok/skip/redo/timeout."""
    deadline = since + POLL_TIMEOUT_SEC
    url = f"{_topic_url()}/json"

    sent_body_stripped = sent_body.strip()

    while time.time() < deadline:
        try:
            r = requests.get(
                url,
                params={"poll": "1", "since": str(since)},
                timeout=20,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            log.warning("ntfy poll failed: %s", e)
            time.sleep(POLL_INTERVAL_SEC)
            continue

        # Response is NDJSON: one JSON object per line
        for line in r.text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("event") != "message":
                continue
            message_text = (msg.get("message") or "").strip()
            if not message_text:
                continue
            # Ignore the bot's own outgoing notification
            if message_text == sent_body_stripped:
                continue
            # Treat the first word / full message as the command
            normalized = message_text.lower().strip()
            # Accept exact match or command as first token
            first = normalized.split()[0] if normalized else ""
            if first in VALID_RESPONSES:
                log.info("Got user response: %s", first)
                return first
            if normalized in VALID_RESPONSES:
                log.info("Got user response: %s", normalized)
                return normalized

        time.sleep(POLL_INTERVAL_SEC)

    log.info("Polling timed out after %d seconds", POLL_TIMEOUT_SEC)
    return "timeout"


def send_info(title: str, body: str) -> None:
    """Fire-and-forget info notification (no polling)."""
    try:
        requests.post(
            _topic_url(),
            data=body.encode("utf-8"),
            headers={"Title": title, "Priority": "3"},
            timeout=20,
        )
    except requests.RequestException as e:
        log.warning("send_info failed: %s", e)
