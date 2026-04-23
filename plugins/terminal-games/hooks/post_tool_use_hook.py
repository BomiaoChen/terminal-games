#!/usr/bin/env python3
"""
PostToolUse hook: signals the game that Claude resumed after a tool completed.
Resets the bridge from "needs_input" back to "waiting".
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.bridge import write_resuming


LOG = os.path.expanduser("~/.claude/game_posttool_debug.log")


def main():
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id", "unknown")
        tool_name = payload.get("tool_name", "unknown")
        # "denied" or similar appears in tool_response when user rejects
        tool_response = str(payload.get("tool_response", ""))[:80]
        write_resuming(session_id)
        with open(LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now().isoformat()} session={session_id} tool={tool_name} response={tool_response!r}\n")
    except Exception as e:
        with open(LOG, "a") as f:
            f.write(f"ERROR: {e}\n")

    print("{}")


if __name__ == "__main__":
    main()
