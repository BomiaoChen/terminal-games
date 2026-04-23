#!/usr/bin/env python3
"""
Stop hook: writes "done" to the session-scoped bridge file so any running
game knows Claude has finished. Always outputs {"decision": "approve"} —
never blocks Claude's stop.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.bridge import read_bridge, write_done, write_denied

LOG = os.path.expanduser("~/.claude/game_stop_debug.log")


def main():
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id", "unknown")
        current = read_bridge(session_id)
        bridge_status = current.get("status", "missing")
        if bridge_status == "needs_input":
            write_denied(session_id)
            verdict = "denied"
        else:
            write_done(session_id)
            verdict = "done"
        with open(LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now().isoformat()} session={session_id} bridge_was={bridge_status} wrote={verdict}\n")
    except Exception as e:
        with open(LOG, "a") as f:
            f.write(f"ERROR: {e}\n")

    print(json.dumps({"decision": "approve"}))

if __name__ == "__main__":
    main()
