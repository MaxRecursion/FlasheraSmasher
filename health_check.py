#!/usr/bin/env python3
"""Standalone health check for marathi-tweet-responder.

Run from project root:
    ./venv/bin/python health_check.py

Verifies X search/auth, Anthropic, ntfy, data file, and launchd service.
Exits 0 if all pass, 1 if any fail.
"""
import json
import subprocess
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import config  # noqa: E402
from src.claude_drafter import draft_reply  # noqa: E402
from src.notifier import send_info  # noqa: E402
from src.twitter_client import TwitterClient  # noqa: E402


def _check(name: str, fn):
    print(f"→ {name} ...", flush=True)
    try:
        fn()
        print(f"  ✅ {name}")
        return True
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ {name}: {e}")
        traceback.print_exc(limit=1)
        return False


def check_env():
    config.validate_env()


def check_x_search():
    tw = TwitterClient()
    tweets = tw.search_marathi_tweets(max_results=10)
    if not tweets:
        raise RuntimeError("No tweets returned")
    t = tweets[0]
    print(
        f"    sample: @{t['author_username']} (followers={t['author_followers']}): "
        f"{t['text'][:80]}"
    )


def check_x_auth():
    tw = TwitterClient()
    me = tw.get_me()
    print(f"    authenticated as @{me['username']} (id={me['id']})")


def check_anthropic():
    reply = draft_reply(
        "आज पुण्यात खूप पाऊस पडतोय. सगळीकडे पाणीच पाणी!",
        "TestUser",
    )
    print(f"    draft reply: {reply}")


def check_ntfy():
    send_info("marathi-responder health check", "Health check passed ✅")


def check_data_file():
    path = config.REPLIED_TWEETS_FILE
    if not path.exists():
        print("    replied_tweets.json does not exist yet (ok)")
        return
    with path.open("r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"    {len(records)} replied tweets on record")
    for r in records[-3:]:
        print(
            f"      - {r.get('replied_at', '?')} @{r.get('author_username', '?')}"
        )


def check_launchd():
    try:
        out = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"launchctl failed: {e}") from e
    matched = [
        line for line in out.stdout.splitlines() if "marathi" in line.lower()
    ]
    if not matched:
        raise RuntimeError("no marathi service in launchctl list")
    for line in matched:
        print(f"    {line}")


def main() -> int:
    print("marathi-tweet-responder health check\n")
    results = {
        ".env loaded": _check(".env loaded", check_env),
        "X search (bearer)": _check("X search (bearer)", check_x_search),
        "X auth (OAuth 1.0a)": _check("X auth (OAuth 1.0a)", check_x_auth),
        "Anthropic draft": _check("Anthropic draft", check_anthropic),
        "ntfy notification": _check("ntfy notification", check_ntfy),
        "replied_tweets.json": _check("replied_tweets.json", check_data_file),
        "launchd service": _check("launchd service", check_launchd),
    }
    print("\nSummary:")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}")
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"\n❌ {len(failed)} check(s) failed: {', '.join(failed)}")
        return 1
    print("\n✅ All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
