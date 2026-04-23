#!/usr/bin/env python3
"""
PreToolUse hook: signals the game that Claude needs user attention.

Fires before every tool execution. The game applies a 1-second debounce
so fast auto-approved tools don't cause a visible pause — only tools that
genuinely wait for user input (AskUserQuestion, approval dialogs) will
trigger an auto-pause.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.bridge import write_needs_input


LOG = os.path.expanduser("~/.claude/game_pretool_debug.log")


def main():
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id", "unknown")
        tool_name = payload.get("tool_name", "unknown")
        write_needs_input(session_id)
        with open(LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now().isoformat()} session={session_id} tool={tool_name}\n")
    except Exception as e:
        with open(LOG, "a") as f:
            f.write(f"ERROR: {e}\n")

    print("{}")


if __name__ == "__main__":
    main()
