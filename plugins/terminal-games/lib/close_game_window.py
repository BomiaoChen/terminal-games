#!/usr/bin/env python3
"""
Close the Terminal.app window that owns a specific TTY path.

Usage: close_game_window.py <tty_path>

Called from the game shell script with the TTY captured before the shell exits.
Calls os.setsid() immediately to detach from the controlling terminal so
Terminal.app sees no running process in the tab and closes without a
confirmation dialog.
"""
import os
import sys
import time
import subprocess


def main() -> None:
    tty = sys.argv[1] if len(sys.argv) > 1 else None
    if not tty:
        return

    # Detach from the controlling terminal so Terminal.app no longer counts
    # this process as "running" in the tab — prevents the confirmation dialog.
    try:
        os.setsid()
    except OSError:
        pass  # already a session leader, ignore

    time.sleep(0.3)  # give the parent shell time to exit first

    script = f'''tell application "Terminal"
    repeat with w in windows
        repeat with t in tabs of w
            if tty of t is "{tty}" then
                close w
                return
            end if
        end repeat
    end repeat
end tell'''
    subprocess.run(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
