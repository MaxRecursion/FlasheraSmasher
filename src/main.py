"""Entry point for the Marathi tweet responder bot."""
import json
import logging
import logging.handlers
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, scheduler
from .twitter_client import TwitterClient

VERSION = "0.1.0"


def _setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Clear any existing handlers (useful under launchd restarts)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    today = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d")
    log_path = config.LOGS_DIR / f"{today}.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def _count_replied() -> int:
    if not config.REPLIED_TWEETS_FILE.exists():
        return 0
    try:
        with config.REPLIED_TWEETS_FILE.open("r", encoding="utf-8") as f:
            return len(json.load(f))
    except (OSError, json.JSONDecodeError):
        return 0


def _startup_banner() -> None:
    log = logging.getLogger(__name__)
    log.info("=" * 60)
    log.info(" marathi-tweet-responder v%s", VERSION)
    log.info("=" * 60)
    try:
        tw = TwitterClient()
        me = tw.get_me()
        log.info("Authenticated as @%s (id=%s)", me["username"], me["id"])
    except Exception as e:  # noqa: BLE001
        log.error("get_me() failed at startup: %s", e)
    log.info("Previously replied tweets: %d", _count_replied())
    log.info(
        "Daily replies: %d | Window: %02d:00–%02d:00 %s",
        config.DAILY_REPLY_COUNT,
        config.WINDOW_START,
        config.WINDOW_END,
        config.TIMEZONE,
    )
    log.info("=" * 60)


def main() -> int:
    config.validate_env()
    _setup_logging()
    _startup_banner()
    scheduler.run_daily_schedule()
    return 0


if __name__ == "__main__":
    sys.exit(main())
