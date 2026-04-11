"""Local control panel for marathi-tweet-responder.

Serves a small Flask app on http://127.0.0.1:8765 with endpoints to:

- inspect launchd service status + recent replies
- run the health check on demand
- trigger one reply slot on demand (routes through the normal ntfy
  approval flow — nothing auto-posts)
- stream a live activity log that captures logs from the rest of the
  src.* package via a custom logging handler

Run with:
    ./venv/bin/python -m src.webui
"""
import json
import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, send_from_directory

from . import claude_drafter, config, notifier, scheduler, session_log
from .twitter_client import get_shared_client

log = logging.getLogger(__name__)

PLIST_LABEL = "com.akshay.marathi-responder"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
WEBUI_DIR = Path(__file__).parent / "webui_static"

HOST = "127.0.0.1"
PORT = 8765

app = Flask(
    __name__,
    static_folder=str(WEBUI_DIR),
    static_url_path="/static",
)

# ---------------------------------------------------------------------------
# Activity tracker (shared between requests via a lock)
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_activity: dict[str, Any] = {
    "task": None,          # "run_now" | "health_check" | None
    "status": "idle",      # "idle" | "running" | "done" | "error"
    "message": "",
    "started_at": None,
    "finished_at": None,
    "events": [],          # list of {ts, level, text}
    "last_health": {},
}


def _now_iso() -> str:
    return datetime.now(ZoneInfo(config.TIMEZONE)).isoformat()


def _log_event(level: str, text: str) -> None:
    entry = {
        "ts": datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S"),
        "level": level,
        "text": text,
    }
    with _state_lock:
        _activity["events"].append(entry)
        if len(_activity["events"]) > 200:
            _activity["events"] = _activity["events"][-200:]


def _set_task(task: str | None, status: str, message: str = "") -> None:
    with _state_lock:
        _activity["task"] = task
        _activity["status"] = status
        _activity["message"] = message
        if status == "running":
            _activity["started_at"] = _now_iso()
            _activity["finished_at"] = None
        else:
            _activity["finished_at"] = _now_iso()


class _ActivityLogHandler(logging.Handler):
    """Pipe log records from src.* into the UI activity stream."""

    def emit(self, record: logging.LogRecord) -> None:
        name = record.name or ""
        if not (name.startswith("src.") or name == "__main__"):
            return
        if name.endswith(".webui"):
            return  # avoid echoing our own log lines
        level = "error" if record.levelno >= logging.ERROR else (
            "warn" if record.levelno >= logging.WARNING else "info"
        )
        msg = record.getMessage()
        short = name.split(".")[-1]
        _log_event(level, f"{short}: {msg[:240]}")


# ---------------------------------------------------------------------------
# launchd helpers
# ---------------------------------------------------------------------------
def _launchctl_list() -> dict[str, Any]:
    try:
        out = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as e:  # noqa: BLE001
        return {"loaded": False, "pid": None, "exit": None, "error": str(e)}
    matched = [ln for ln in out.stdout.splitlines() if PLIST_LABEL in ln]
    if not matched:
        return {"loaded": False, "pid": None, "exit": None}
    parts = matched[0].split()
    pid_raw = parts[0] if parts else "-"
    exit_raw = parts[1] if len(parts) > 1 else "-"
    return {
        "loaded": True,
        "pid": int(pid_raw) if pid_raw.isdigit() else None,
        "exit": None if exit_raw == "-" else exit_raw,
    }


def _launchctl_control(action: str) -> tuple[bool, str]:
    if not PLIST_PATH.exists():
        return False, f"Plist not installed at {PLIST_PATH}"
    try:
        if action == "load":
            subprocess.run(
                ["launchctl", "load", str(PLIST_PATH)],
                check=True, capture_output=True, text=True, timeout=10,
            )
        elif action == "unload":
            subprocess.run(
                ["launchctl", "unload", str(PLIST_PATH)],
                check=True, capture_output=True, text=True, timeout=10,
            )
        elif action == "restart":
            subprocess.run(
                ["launchctl", "unload", str(PLIST_PATH)],
                capture_output=True, text=True, timeout=10,
            )
            subprocess.run(
                ["launchctl", "load", str(PLIST_PATH)],
                check=True, capture_output=True, text=True, timeout=10,
            )
        else:
            return False, f"Unknown action: {action}"
    except subprocess.CalledProcessError as e:
        return False, (e.stderr or e.stdout or str(e)).strip()
    except subprocess.TimeoutExpired:
        return False, "launchctl timed out"
    return True, f"{action} ok"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def _read_replied() -> list[dict[str, Any]]:
    path = config.REPLIED_TWEETS_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


# ---------------------------------------------------------------------------
# Routes: static + status
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(str(WEBUI_DIR), "index.html")


@app.route("/api/status")
def api_status():
    lc = _launchctl_list()
    replied = _read_replied()
    last = replied[-1] if replied else None
    with _state_lock:
        activity_snap = {
            "task": _activity["task"],
            "status": _activity["status"],
            "message": _activity["message"],
            "started_at": _activity["started_at"],
            "finished_at": _activity["finished_at"],
        }
    return jsonify({
        "service": {
            "label": PLIST_LABEL,
            "plist_installed": PLIST_PATH.exists(),
            **lc,
        },
        "replied_count": len(replied),
        "last_reply": last,
        "config": {
            "timezone": config.TIMEZONE,
            "daily_reply_count": config.DAILY_REPLY_COUNT,
            "window": f"{config.WINDOW_START:02d}:00–{config.WINDOW_END:02d}:00",
            "min_author_followers": config.MIN_AUTHOR_FOLLOWERS,
            "min_tweet_likes": config.MIN_TWEET_LIKES,
            "my_username": config.MY_USERNAME,
        },
        "activity": activity_snap,
        "now": _now_iso(),
    })


@app.route("/api/events")
def api_events():
    with _state_lock:
        return jsonify({"events": list(_activity["events"][-120:])})


@app.route("/api/replied")
def api_replied():
    replied = _read_replied()
    return jsonify({
        "count": len(replied),
        "items": list(reversed(replied[-20:])),
    })


# ---------------------------------------------------------------------------
# Sessions — persistent per-slot timelines
# ---------------------------------------------------------------------------
@app.route("/api/sessions")
def api_sessions():
    """Return the most recent session summaries (newest first)."""
    return jsonify({"sessions": session_log.list_recent(limit=25)})


@app.route("/api/sessions/<session_id>")
def api_session_detail(session_id: str):
    """Return the full record for one session — fetched tweets,
    filter stats, Claude calls, events timeline, outcome."""
    data = session_log.load(session_id)
    if data is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(data)


# ---------------------------------------------------------------------------
# Service control
# ---------------------------------------------------------------------------
@app.route("/api/service/<action>", methods=["POST"])
def api_service_control(action: str):
    mapping = {"start": "load", "stop": "unload", "restart": "restart"}
    if action not in mapping:
        return jsonify({"ok": False, "error": "unknown action"}), 400
    cmd = mapping[action]
    _log_event("info", f"launchctl {cmd} requested from UI")
    ok, msg = _launchctl_control(cmd)
    _log_event("info" if ok else "error", f"launchctl {cmd}: {msg}")
    try:
        notifier.send_info(
            "Marathi Responder",
            f"Service {action}: {'ok' if ok else 'failed'} — {msg}",
        )
    except Exception:  # noqa: BLE001
        pass
    return jsonify({"ok": ok, "message": msg, "service": _launchctl_list()})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def _run_health_checks() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    def run(name: str, fn) -> None:
        t0 = time.time()
        try:
            detail = fn() or "ok"
            results[name] = {
                "ok": True,
                "detail": detail,
                "ms": int((time.time() - t0) * 1000),
            }
            _log_event("info", f"health: {name} ok")
        except Exception as e:  # noqa: BLE001
            results[name] = {
                "ok": False,
                "detail": str(e),
                "ms": int((time.time() - t0) * 1000),
            }
            _log_event("error", f"health: {name} failed: {e}")

    run("env", lambda: (config.validate_env() or "env vars present"))

    def _x_search() -> str:
        # Reuse the shared client + its cache so hammering "Health
        # Check" does not burn X credits on every click
        tw = get_shared_client()
        t = tw.search_marathi_tweets(max_results=10)
        if not t:
            raise RuntimeError("no tweets returned")
        return f"{len(t)} tweets; sample @{t[0]['author_username']}"

    def _x_auth() -> str:
        me = get_shared_client().get_me()
        return f"@{me['username']} (id={me['id']})"

    def _anthropic() -> str:
        r = claude_drafter.draft_reply("आज पुण्यात पाऊस पडतोय.", "TestUser")
        return f"draft: {r[:60]}"

    def _ntfy() -> str:
        notifier.send_info("marathi-responder", "Health check ping from UI ✅")
        return "ntfy ping sent"

    def _data() -> str:
        path = config.REPLIED_TWEETS_FILE
        if not path.exists():
            return "no replied_tweets.json yet"
        recs = json.loads(path.read_text(encoding="utf-8"))
        return f"{len(recs)} records"

    def _launchd() -> str:
        lc = _launchctl_list()
        if not lc.get("loaded"):
            raise RuntimeError("service not loaded")
        return f"pid={lc.get('pid')}, last_exit={lc.get('exit')}"

    run("x_search", _x_search)
    run("x_auth", _x_auth)
    run("anthropic", _anthropic)
    run("ntfy", _ntfy)
    run("data_file", _data)
    run("launchd", _launchd)
    return results


@app.route("/api/health-check", methods=["POST"])
def api_health_check():
    with _state_lock:
        if _activity["status"] == "running":
            return jsonify({"ok": False, "error": f"busy: {_activity['task']}"}), 409

    def runner() -> None:
        _set_task("health_check", "running", "Running health checks…")
        _log_event("info", "Health check started")
        try:
            notifier.send_info("Marathi Responder", "Health check started from UI")
        except Exception:  # noqa: BLE001
            pass
        try:
            res = _run_health_checks()
        except Exception as e:  # noqa: BLE001
            _set_task("health_check", "error", str(e))
            _log_event("error", f"Health check crashed: {e}")
            return
        failed = [k for k, v in res.items() if not v["ok"]]
        with _state_lock:
            _activity["last_health"] = res
        if failed:
            _set_task("health_check", "error", f"{len(failed)} check(s) failed")
            try:
                notifier.send_info(
                    "Marathi Responder",
                    f"Health check: {len(failed)} failed — {', '.join(failed)}",
                )
            except Exception:  # noqa: BLE001
                pass
        else:
            _set_task("health_check", "done", "All checks passed")
            try:
                notifier.send_info("Marathi Responder", "Health check: all passed ✅")
            except Exception:  # noqa: BLE001
                pass

    threading.Thread(target=runner, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/health-check/result")
def api_health_check_result():
    with _state_lock:
        return jsonify(_activity.get("last_health") or {})


# ---------------------------------------------------------------------------
# On-demand slot
# ---------------------------------------------------------------------------
@app.route("/api/run-now", methods=["POST"])
def api_run_now():
    with _state_lock:
        if _activity["status"] == "running":
            return jsonify({"ok": False, "error": f"busy: {_activity['task']}"}), 409

    def runner() -> None:
        _set_task("run_now", "running", "Searching for candidate tweet…")
        _log_event("info", "On-demand slot triggered from UI")
        try:
            notifier.send_info("Marathi Responder", "On-demand reply slot started from UI")
        except Exception:  # noqa: BLE001
            pass
        try:
            scheduler.process_one_slot_now()
        except Exception as e:  # noqa: BLE001
            log.exception("run_now failed")
            _set_task("run_now", "error", str(e))
            _log_event("error", f"run_now crashed: {e}")
            try:
                notifier.send_info("Marathi Responder", f"On-demand slot failed: {e}")
            except Exception:  # noqa: BLE001
                pass
            return
        _set_task("run_now", "done", "Slot complete")
        _log_event("info", "On-demand slot complete")
        try:
            notifier.send_info("Marathi Responder", "On-demand slot finished")
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=runner, daemon=True).start()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> int:
    config.validate_env()

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root.addHandler(sh)
    root.addHandler(_ActivityLogHandler())

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    _log_event("info", f"Control panel starting on http://{HOST}:{PORT}")
    try:
        notifier.send_info(
            "Marathi Responder",
            f"Control panel started — http://{HOST}:{PORT}",
        )
    except Exception:  # noqa: BLE001
        pass

    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
