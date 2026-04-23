#!/usr/bin/env python3
"""
Game launcher — invoked by the /game skill.

Usage:
  python3 launch_game.py [game-name|on|off]

  on   — enable auto-launch on every prompt >= 20 chars
  off  — disable auto-launch
"""

import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PLUGIN_ROOT)

import games  # noqa: F401
from games.registry import get, list_games
from lib.bridge import get_active_session_id
from lib.game_config import set_auto_launch, load as load_config
from lib.state_manager import StateManager
from lib.window_launcher import launch


def _print_banner(game_name: str, game_cls) -> None:
    try:
        stats = StateManager().get_stats(game_name)
        if stats:
            high = stats.get("high_score", 0)
            plays = stats.get("total_play_count", 0)
            print(f"\n  {game_cls.title}  —  Personal best: {high}  |  Plays: {plays}")
        else:
            print(f"\n  {game_cls.title}  —  First time playing!")
        print("  Controls: [SPACE] Flap   [Q] Quit\n")
    except Exception:
        pass


def _print_score_summary(game) -> None:
    try:
        score = game.get_score()
        stats = StateManager().get_stats(game._registry_name)
        high = stats.get("high_score", 0)
        if score == high and score > 0:
            print(f"\n  Score: {score}  ** New personal best! **\n")
        else:
            print(f"\n  Score: {score}  (Best: {high})\n")
    except Exception:
        pass


def _has_tty() -> bool:
    return os.isatty(sys.stdin.fileno())


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    # Toggle commands
    if arg == "on":
        set_auto_launch(True)
        cfg = load_config()
        print(f"\n  Auto-launch enabled. Game will open automatically for prompts >= {cfg['min_prompt_length']} characters.\n")
        return
    if arg == "off":
        set_auto_launch(False)
        print("\n  Auto-launch disabled. Use /game to launch manually.\n")
        return

    # Game launch
    game_name = arg or "flappy-bird"
    available = list_games()

    if not available:
        print("No games are registered.", file=sys.stderr)
        sys.exit(1)

    try:
        game_cls = get(game_name)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    session_id = get_active_session_id()
    _print_banner(game_name, game_cls)

    if _has_tty():
        game = game_cls()
        game.run(session_id=session_id)
        _print_score_summary(game)
    else:
        launch(game_name, session_id)
        print("  Game launched in a new terminal window.")
        print('  It will show "Claude is ready!" when I finish.\n')


if __name__ == "__main__":
    main()
