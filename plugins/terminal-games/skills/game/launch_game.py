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
from lib.game_config import set_auto_launch, set_default_game, set_git_archaeology_repo, set_window_settings, load as load_config
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
        controls = getattr(game_cls, "controls_hint", "[SPACE] Flap   [Q] Quit")
        print(f"  Controls: {controls}\n")
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

    # Set git archaeology repo: /game repo <path>
    if arg == "repo":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else None
        if not repo_path:
            cfg = load_config()
            current = cfg.get("git_archaeology_repo", "") or "(auto-detect)"
            print(f"\n  Git Archaeology repo: {current}")
            print(f"  Usage: /game repo <path-to-repo>\n")
            return
        from pathlib import Path
        p = Path(repo_path).expanduser()
        if not (p / ".git").exists():
            print(f"  Not a git repository: {repo_path}", file=sys.stderr)
            sys.exit(1)
        set_git_archaeology_repo(str(p))
        print(f"\n  Git Archaeology repo set to: {p}\n")
        return

    # Configure window: /game window [font=N] [rows=N] [cols=N]
    if arg == "window":
        extra_args = sys.argv[2:]
        if not extra_args:
            cfg = load_config()
            fs = cfg.get("window_font_size", 0)
            rows = cfg.get("window_rows", 0)
            cols = cfg.get("window_cols", 0)
            print(f"\n  Game window settings:")
            print(f"    font size : {fs if fs else '(Terminal default)'}")
            print(f"    rows      : {rows if rows else '(Terminal default)'}")
            print(f"    cols      : {cols if cols else '(Terminal default)'}")
            print(f"\n  Usage: /game window font=<N> rows=<N> cols=<N>")
            print(f"  Example: /game window font=18 rows=40 cols=120")
            print(f"  Reset:   /game window font=0 rows=0 cols=0\n")
            return
        font_size = rows = cols = None
        for part in extra_args:
            if "=" in part:
                k, v = part.split("=", 1)
                try:
                    val = int(v)
                except ValueError:
                    print(f"  Invalid value: {part!r} (must be an integer)", file=sys.stderr)
                    sys.exit(1)
                if k in ("font", "font_size", "fontsize"):
                    font_size = val
                elif k == "rows":
                    rows = val
                elif k in ("cols", "columns"):
                    cols = val
                else:
                    print(f"  Unknown option: {k!r}. Use font, rows, or cols.", file=sys.stderr)
                    sys.exit(1)
        set_window_settings(font_size, rows, cols)
        cfg = load_config()
        fs = cfg.get("window_font_size", 0)
        r = cfg.get("window_rows", 0)
        c = cfg.get("window_cols", 0)
        print(f"\n  Window settings saved:")
        print(f"    font size : {fs if fs else '(Terminal default)'}")
        print(f"    rows      : {r if r else '(Terminal default)'}")
        print(f"    cols      : {c if c else '(Terminal default)'}\n")
        return

    # Set default game: /game default <name>
    if arg == "default":
        new_default = sys.argv[2] if len(sys.argv) > 2 else None
        if not new_default:
            cfg = load_config()
            print(f"\n  Current default game: {cfg['default_game']}")
            print(f"  Available: {', '.join(list_games())}")
            print(f"  Usage: /game default <game-name>\n")
            return
        available = list_games()
        if new_default not in available:
            print(f"  Unknown game: {new_default!r}. Available: {', '.join(available)}", file=sys.stderr)
            sys.exit(1)
        set_default_game(new_default)
        print(f"\n  Default game set to: {new_default}\n")
        return

    # Game launch
    cfg = load_config()
    game_name = arg or cfg.get("default_game", "flappy-bird")
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
