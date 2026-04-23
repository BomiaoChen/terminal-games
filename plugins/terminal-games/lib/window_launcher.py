"""
Launch the game in a Terminal.app window via AppleScript.
Used by both the UserPromptSubmit hook (auto-launch) and launch_game.py (manual).

Single-window guarantee: if a tab titled "Claude Game" is already running in
Terminal.app, it is brought to front instead of opening a new window.

On clean exit: the shell script captures its own TTY, spawns a detached
close_game_window.py (which calls os.setsid() to leave the session), then
exits. Terminal sees no running process and closes without a confirmation dialog.
"""

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
GAME_RUNNER = PLUGIN_ROOT / "skills" / "game" / "run_game.py"
CLOSE_HELPER = PLUGIN_ROOT / "lib" / "close_game_window.py"


def _window_settings_applescript(font_size: int, rows: int, cols: int) -> str:
    """Return AppleScript lines to apply window settings to the frontmost tab (variable t)."""
    lines = []
    if font_size > 0:
        lines.append(f"    set font size of t to {font_size}")
    if rows > 0:
        lines.append(f"    set number of rows of t to {rows}")
    if cols > 0:
        lines.append(f"    set number of columns of t to {cols}")
    return "\n".join(lines)


def _focus_running_game() -> bool:
    """If run_game.py is running, focus its exact Terminal tab. Returns True if found."""
    pid_result = subprocess.run(
        ["pgrep", "-f", "run_game.py"],
        capture_output=True, text=True,
    )
    if pid_result.returncode != 0:
        return False

    pid = pid_result.stdout.strip().splitlines()[0]

    # Get the short TTY name (e.g. "s010") for that PID
    tty_result = subprocess.run(
        ["ps", "-p", pid, "-o", "tty="],
        capture_output=True, text=True,
    )
    if tty_result.returncode != 0:
        return False

    tty_short = tty_result.stdout.strip()
    if not tty_short or tty_short == "??":
        return False

    tty_path = f"/dev/{tty_short}"

    applescript = f'''tell application "Terminal"
    repeat with w in windows
        repeat with t in tabs of w
            if tty of t is "{tty_path}" then
                set selected of t to true
                set index of w to 1
                activate
                return
            end if
        end repeat
    end repeat
end tell'''
    subprocess.run(["osascript", "-e", applescript], check=False)
    return True


def launch(game_name: str, session_id: str | None = None) -> None:
    # If a game is already running, focus its Terminal tab instead of opening a new one.
    if _focus_running_game():
        return

    # Load window settings from config
    try:
        sys.path.insert(0, str(PLUGIN_ROOT))
        from lib.game_config import load as load_config
        cfg = load_config()
        font_size = int(cfg.get("window_font_size", 0))
        rows = int(cfg.get("window_rows", 0))
        cols = int(cfg.get("window_cols", 0))
    except Exception:
        font_size, rows, cols = 0, 0, 0

    python = shlex.quote(sys.executable)
    close_helper = shlex.quote(str(CLOSE_HELPER))

    args = [sys.executable, str(GAME_RUNNER), game_name]
    if session_id:
        args.append(session_id)
    cmd = " ".join(shlex.quote(a) for a in args)

    script_content = (
        "#!/bin/sh\n"
        + cmd + "\n"
        + "_exit=$?\n"
        + "if [ $_exit -ne 0 ]; then\n"
        + '    echo "\\nGame exited with an error. Press Enter to close..."; read _\n'
        + "else\n"
        # Capture TTY before shell exits, spawn detached closer — no confirmation dialog.
        + "    MY_TTY=$(tty)\n"
        + f"    {python} {close_helper} \"$MY_TTY\" &\n"
        + "fi\n"
    )

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, prefix="claude_game_"
    )
    tmp.write(script_content)
    tmp.flush()
    tmp.close()
    os.chmod(tmp.name, 0o755)

    window_settings = _window_settings_applescript(font_size, rows, cols)
    applescript = (
        'tell application "Terminal"\n'
        f'    set t to do script "{tmp.name}"\n'
        + (window_settings + "\n" if window_settings else "")
        + '    set w to window of t\n'
        + '    set selected of t to true\n'
        + '    set index of w to 1\n'
        + '    activate\n'
        'end tell\n'
    )
    subprocess.run(["osascript", "-e", applescript], check=False)
