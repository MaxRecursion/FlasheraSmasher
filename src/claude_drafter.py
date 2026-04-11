"""Draft Marathi replies using the Anthropic Claude API."""
import logging
import time

import anthropic

from . import config

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 400
MAX_REPLY_CHARS = 280

SYSTEM_PROMPT = """तू एक पुण्याचा विनोदी ट्विटर वापरकर्ता आहेस. तुला मराठी ट्विट्सना
मजेशीर replies द्यायचे आहेत.

Rules:
- Reply MUST be in Marathi (Devanagari script)
- Keep it under 250 characters (leave room for Twitter)
- Be slightly humorous — Puneri wit style: sharp but friendly
- Stay relevant to the original tweet's topic
- Never be offensive, political, casteist, or religious
- Never mock the original author
- Maximum 1-2 emoji, only if natural
- No hashtags in replies
- Sound like a real person, not a bot
- If the tweet is about a serious/sad topic, be supportive
  instead of humorous
"""


def _extract_text(message) -> str:
    """Pull the first text block out of an Anthropic Message."""
    if not message or not getattr(message, "content", None):
        return ""
    parts: list[str] = []
    for block in message.content:
        txt = getattr(block, "text", None)
        if txt:
            parts.append(txt)
    return "".join(parts).strip()


def draft_reply(tweet_text: str, author_name: str) -> str:
    """Ask Claude to draft a Marathi reply; retry once if too long."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_prompt = (
        f"Original tweet by @{author_name}:\n{tweet_text}\n\nWrite a reply."
    )

    last_exc: Exception | None = None
    for attempt in range(1, 3):  # up to 2 API attempts
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            reply = _extract_text(message)

            if len(reply) > MAX_REPLY_CHARS:
                log.info(
                    "Draft reply is %d chars, retrying for shorter reply",
                    len(reply),
                )
                message = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": reply},
                        {
                            "role": "user",
                            "content": (
                                "तुझं उत्तर फार लांब आहे. कृपया 250 "
                                "characters च्या आत फक्त reply दे."
                            ),
                        },
                    ],
                )
                reply = _extract_text(message)
                if len(reply) > MAX_REPLY_CHARS:
                    reply = reply[:MAX_REPLY_CHARS]
            return reply
        except anthropic.APIError as e:
            last_exc = e
            log.warning(
                "Anthropic API error on attempt %d: %s", attempt, e
            )
            time.sleep(5)
    assert last_exc is not None
    raise last_exc
