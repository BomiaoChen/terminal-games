"""
Persistent game state stored at ~/.claude/game_state.json.

Schema (schema_version=1):
{
  "schema_version": 1,
  "users": {
    "<user_id>": {
      "games": {
        "<game_name>": {
          "high_score": int,
          "total_play_count": int,
          "total_time_seconds": float,
          "last_played_at": "<ISO8601>",
          "sessions": [
            { "played_at": "<ISO8601>", "score": int, "duration_seconds": float }
          ]
        }
      }
    }
  }
}

Writes are atomic (temp file + rename) to prevent corruption on crash.
Sessions array is capped at MAX_SESSIONS_PER_GAME most-recent entries.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.user_identity import resolve_user_id

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = PLUGIN_ROOT / "game_state.json"
_LEGACY_PATH = Path("~/.claude/game_state.json").expanduser()
MAX_SESSIONS_PER_GAME = 100


class StateManager:
    def __init__(self, user_id: str | None = None):
        self._user_id = user_id or resolve_user_id()

    def record_session(self, game_name: str, score: int, duration_seconds: float = 0.0) -> None:
        """Record a completed game session and update aggregates atomically."""
        state = self._load()
        user_data = state.setdefault("users", {}).setdefault(self._user_id, {"games": {}})
        game_data = user_data.setdefault("games", {}).setdefault(game_name, {
            "high_score": 0,
            "total_play_count": 0,
            "total_time_seconds": 0.0,
            "last_played_at": None,
            "sessions": [],
        })

        now = datetime.now(timezone.utc).isoformat()
        game_data["high_score"] = max(game_data.get("high_score", 0), score)
        game_data["total_play_count"] = game_data.get("total_play_count", 0) + 1
        game_data["total_time_seconds"] = game_data.get("total_time_seconds", 0.0) + duration_seconds
        game_data["last_played_at"] = now

        sessions = game_data.setdefault("sessions", [])
        sessions.append({"played_at": now, "score": score, "duration_seconds": duration_seconds})
        # Cap to most recent MAX_SESSIONS_PER_GAME
        game_data["sessions"] = sessions[-MAX_SESSIONS_PER_GAME:]

        self._save(state)

    def get_stats(self, game_name: str) -> dict:
        """Return stats dict for this user + game. Empty dict if no data yet."""
        state = self._load()
        return (
            state
            .get("users", {})
            .get(self._user_id, {})
            .get("games", {})
            .get(game_name, {})
        )

    def get_all_users_high_scores(self, game_name: str) -> list[dict]:
        """Return [{user_id, high_score}] sorted by high_score desc — for leaderboard."""
        state = self._load()
        results = []
        for uid, udata in state.get("users", {}).items():
            game_data = udata.get("games", {}).get(game_name, {})
            if game_data:
                results.append({"user_id": uid, "high_score": game_data.get("high_score", 0)})
        return sorted(results, key=lambda x: x["high_score"], reverse=True)

    def get_top_sessions(self, game_name: str, n: int = 5) -> list[dict]:
        """Return top-n sessions across all users, sorted by score desc.
        Each entry: {user_id, score, played_at, duration_seconds}
        """
        state = self._load()
        all_sessions = []
        for uid, udata in state.get("users", {}).items():
            for session in udata.get("games", {}).get(game_name, {}).get("sessions", []):
                all_sessions.append({
                    "user_id": uid,
                    "score": session.get("score", 0),
                    "played_at": session.get("played_at", ""),
                    "duration_seconds": session.get("duration_seconds", 0),
                })
        return sorted(all_sessions, key=lambda s: s["score"], reverse=True)[:n]

    # ---- Internal ----

    def _load(self) -> dict:
        # Try the shared repo-scoped state file first
        try:
            data = json.loads(STATE_PATH.read_text())
            if data.get("schema_version") == 1:
                return data
        except Exception:
            pass

        # Migrate from legacy per-user ~/.claude/game_state.json if it exists
        try:
            legacy = json.loads(_LEGACY_PATH.read_text())
            if legacy.get("schema_version") == 1:
                self._save(legacy)  # persist to new location
                return legacy
        except Exception:
            pass

        return {"schema_version": 1, "users": {}}

    def _save(self, state: dict) -> None:
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(STATE_PATH)
