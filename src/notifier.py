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


def _ascii_header(value: str) -> str:
    """HTTP header values must be latin-1 encodable (RFC 7230 + what
    ``requests``/``urllib3`` actually enforce).  Any codepoint above
    0xFF — e.g. an emoji in a tweet author's display name — crashes
    the request before it even leaves the process.  Strip anything
    non-ASCII here so the notification still goes out with a slightly
    degraded title instead of the whole slot failing."""
    return value.encode("ascii", "ignore").decode("ascii").strip() or "Marathi Responder"


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
    raw_title = f"Marathi Reply #{number_today}: @{tweet_data.get('author_username', '')}"
    # Tappable action buttons shown inside the ntfy notification itself.
    # Each button does an HTTP POST back to the same topic with body
    # "OK"/"SKIP"/"REDO"; our own ``_poll_for_response`` picks those up
    # as the user's command. iOS users just long-press / expand the
    # notification and tap — no need to open the ntfy app or type a reply.
    topic = _topic_url()
    # headers.Priority=min (1) makes the echo notification from the
    # button POST silent — otherwise tapping "Approve" would create a
    # bare "OK" push on the phone.
    actions = (
        f"http, Approve, {topic}, method=POST, body=OK, "
        f"headers.Priority=min, clear=true; "
        f"http, Skip, {topic}, method=POST, body=SKIP, "
        f"headers.Priority=min, clear=true; "
        f"http, Redo, {topic}, method=POST, body=REDO, "
        f"headers.Priority=min, clear=true"
    )
    headers = {
        "Title": _ascii_header(raw_title),
        "Click": _ascii_header(tweet_data.get("url", "")),
        "Priority": "4",
        "Tags": "bird",
        "Actions": actions,
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

    log.info("Sent approval notification: %s", raw_title)
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
            headers={"Title": _ascii_header(title), "Priority": "3"},
            timeout=20,
        )
    except requests.RequestException as e:
        log.warning("send_info failed: %s", e)
