"""Configuration loading and validation."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
REPLIED_TWEETS_FILE = DATA_DIR / "replied_tweets.json"
ENV_FILE = PROJECT_ROOT / ".env"

# Create required directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env
load_dotenv(ENV_FILE)

# Time window constants
TIMEZONE = "Asia/Kolkata"
WINDOW_START = 8   # 8 AM IST
WINDOW_END = 22    # 10 PM IST

# Required env vars
REQUIRED_VARS = [
    "X_CONSUMER_KEY",
    "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_SECRET",
    "X_BEARER_TOKEN",
    "ANTHROPIC_API_KEY",
    "NTFY_TOPIC",
]


def _get(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key, default)
    return val


def validate_env() -> None:
    """Exit with clear error if any required env var is missing."""
    missing = [k for k in REQUIRED_VARS if not os.getenv(k)]
    if missing:
        sys.stderr.write(
            "❌ Missing required environment variables:\n"
            + "\n".join(f"  - {k}" for k in missing)
            + f"\n\nPlease set them in {ENV_FILE}\n"
        )
        sys.exit(1)


# X API credentials
X_CONSUMER_KEY = _get("X_CONSUMER_KEY")
X_CONSUMER_SECRET = _get("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = _get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = _get("X_ACCESS_SECRET")
X_BEARER_TOKEN = _get("X_BEARER_TOKEN")

# Anthropic
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")

# ntfy
NTFY_TOPIC = _get("NTFY_TOPIC")
NTFY_BASE_URL = "https://ntfy.sh"

# Bot settings
MIN_AUTHOR_FOLLOWERS = int(_get("MIN_AUTHOR_FOLLOWERS", "5000") or "5000")
MIN_TWEET_LIKES = int(_get("MIN_TWEET_LIKES", "50") or "50")
DAILY_REPLY_COUNT = int(_get("DAILY_REPLY_COUNT", "5") or "5")

# X API cost controls
# search_recent_tweets max_results per call. X bills pay-per-use per tweet
# returned, so this is the single biggest cost lever. Must be 10..100.
SEARCH_MAX_RESULTS = int(_get("SEARCH_MAX_RESULTS", "30") or "30")
# In-memory cache TTL (seconds) for the most recent search result on a
# TwitterClient instance. Reused when the same process calls search again
# within the window (e.g. repeated "Run Now" clicks in the webui).
SEARCH_CACHE_TTL = int(_get("SEARCH_CACHE_TTL", "600") or "600")

# My Twitter identity (for reference / filtering)
MY_USER_ID = "221373022"
MY_USERNAME = "MaxRecursion"
