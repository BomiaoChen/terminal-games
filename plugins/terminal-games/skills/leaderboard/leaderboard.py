#!/usr/bin/env python3
"""
Print the top-5 highest-scoring plays across all players.
Usage: leaderboard.py [game-name]   (omit game-name to show all games)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
from lib.user_identity import resolve_user_id
from lib.state_manager import StateManager

TOP_N = 5


def _short_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso[:16]


def _display_name(user_id: str, current_user_id: str) -> str:
    """Strip domain from email, append (you) for the current user."""
    name = user_id.split("@")[0] if "@" in user_id else user_id
    if user_id == current_user_id:
        name += " (you)"
    return name


def _print_game_leaderboard(game_name: str, sm: StateManager, current_user: str) -> None:
    top = sm.get_top_sessions(game_name, n=TOP_N)
    title = game_name.replace("-", " ").title()

    if not top:
        print(f"\n  {title} — No plays recorded yet. Go play!")
        return

    print(f"\n  {title} — Top {TOP_N} Plays  ")
    print(f"  {'Rank':<6}{'Score':>7}   {'Player':<22}{'Date':<17}{'Duration':>9}")
    print(f"  {'─'*6}{'─'*7}   {'─'*22}{'─'*17}{'─'*9}")
    for i, s in enumerate(top, 1):
        score = s.get("score", 0)
        name = _display_name(s.get("user_id", ""), current_user)
        date = _short_date(s.get("played_at", ""))
        dur = s.get("duration_seconds", 0)
        mins, secs = divmod(int(dur), 60)
        dur_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
        print(f"  #{i:<5}{score:>7}   {name:<22}{date:<17}{dur_str:>9}")

    stats = sm.get_stats(game_name)
    if stats:
        high = stats.get("high_score", 0)
        total = stats.get("total_play_count", 0)
        print(f"\n  Your best: {high}  |  Your total plays: {total}")


def main():
    sm = StateManager()
    current_user = resolve_user_id()

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and arg != "all":
        _print_game_leaderboard(arg, sm, current_user)
    else:
        # Show all games that have recorded sessions
        import games  # noqa: F401
        from games.registry import list_games
        game_names = list_games()
        for game_name in game_names:
            _print_game_leaderboard(game_name, sm, current_user)
    print()


if __name__ == "__main__":
    main()
