#!/usr/bin/env python3
"""
UserPromptSubmit hook:
  1. Resets the IPC bridge to "waiting" for the current session.
  2. If auto_launch is enabled and the prompt is long enough,
     opens the game in a new Terminal.app window immediately.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.bridge import write_waiting
from lib.game_config import load as load_config
from lib.window_launcher import launch


def main():
    try:
        payload = json.load(sys.stdin)
        session_id = payload.get("session_id", "unknown")
        prompt = payload.get("prompt", "")

        write_waiting(session_id)

        cfg = load_config()
        if cfg.get("auto_launch") and len(prompt) >= cfg.get("min_prompt_length", 20):
            launch(cfg.get("default_game", "flappy-bird"), session_id)

    except Exception:
        pass  # Never fail Claude's prompt flow

    print("{}")


if __name__ == "__main__":
    main()
