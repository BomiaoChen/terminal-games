#!/usr/bin/env python3
"""
run_game.py — executed inside a new Terminal.app window where a real PTY exists.

Usage:
  python3 run_game.py <game-name> [session-id]
"""

import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PLUGIN_ROOT)

import games  # noqa: F401
from games.registry import get
from lib.state_manager import StateManager


def main():
    if len(sys.argv) < 2:
        print("Usage: run_game.py <game-name> [session-id]", file=sys.stderr)
        sys.exit(1)

    game_name = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        game_cls = get(game_name)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Show banner
    try:
        stats = StateManager().get_stats(game_name)
        if stats:
            print(f"\n  {game_cls.title}  —  Personal best: {stats['high_score']}  |  Plays: {stats['total_play_count']}")
        else:
            print(f"\n  {game_cls.title}  —  First time playing!")
        controls = getattr(game_cls, "controls_hint", "[SPACE] Flap   [P] Pause   [Q] Quit")
        print(f"  Controls: {controls}\n")
    except Exception:
        pass

    game = game_cls()
    game.run(session_id=session_id)


if __name__ == "__main__":
    main()
