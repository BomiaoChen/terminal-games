"""
IPC bridge between Claude Code hooks and the game process.

Each Claude Code session writes to its own file:
  ~/.claude/game_bridge_<session_id>.json

The "active session" pointer lives at:
  ~/.claude/game_active_session.txt

Schema:
  { "status": "waiting|needs_input|done", "timestamp": "<ISO8601>" }

Status lifecycle:
  UserPromptSubmit → "waiting"
  PreToolUse       → "needs_input"   (Claude needs user attention)
  PostToolUse      → "waiting"       (tool finished, Claude resumed)
  Stop             → "done"          (if bridge was "waiting" — Claude finished normally)
  Stop             → "denied"        (if bridge was still "needs_input" — tool was denied)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR = Path("~/.claude").expanduser()


def _bridge_path(session_id: str) -> Path:
    return CLAUDE_DIR / f"game_bridge_{session_id}.json"


def _active_session_path() -> Path:
    return CLAUDE_DIR / "game_active_session.txt"


def write_waiting(session_id: str) -> None:
    """Called by UserPromptSubmit hook: reset bridge to 'waiting'."""
    data = {
        "status": "waiting",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(_bridge_path(session_id), data)
    _active_session_path().write_text(session_id)
    _cleanup_stale_bridges(current_session_id=session_id)


def write_needs_input(session_id: str) -> None:
    """Called by PreToolUse hook: signal the game that Claude needs user attention."""
    data = {
        "status": "needs_input",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(_bridge_path(session_id), data)


def write_resuming(session_id: str) -> None:
    """Called by PostToolUse hook: Claude resumed after tool completion."""
    data = {
        "status": "waiting",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(_bridge_path(session_id), data)


def write_done(session_id: str) -> None:
    """Called by Stop hook: signal the game that Claude is done."""
    data = {
        "status": "done",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(_bridge_path(session_id), data)


def write_denied(session_id: str) -> None:
    """Called by Stop hook when bridge was still 'needs_input': tool was denied."""
    data = {
        "status": "denied",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(_bridge_path(session_id), data)


def read_bridge(session_id: str) -> dict:
    """Read current bridge state for a session. Returns {} on missing/corrupt."""
    try:
        return json.loads(_bridge_path(session_id).read_text())
    except Exception:
        return {}


def get_active_session_id() -> str | None:
    """Return the session_id of the most recently active Claude session."""
    try:
        return _active_session_path().read_text().strip() or None
    except Exception:
        return None


def _atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically using a temp file + rename."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(path)


def _cleanup_stale_bridges(current_session_id: str, max_age_seconds: int = 86400) -> None:
    """Delete game_bridge_*.json files older than max_age_seconds."""
    now = datetime.now(timezone.utc).timestamp()
    for f in CLAUDE_DIR.glob("game_bridge_*.json"):
        # Never delete the current session's file
        if f.name == f"game_bridge_{current_session_id}.json":
            continue
        try:
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink()
        except Exception:
            pass
