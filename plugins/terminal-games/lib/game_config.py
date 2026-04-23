"""
Game config stored at ~/.claude/game_config.json.

Schema:
  {
    "auto_launch": false,        -- launch game automatically on every long prompt
    "min_prompt_length": 20,     -- minimum prompt length to trigger auto-launch
    "default_game": "flappy-bird" -- game launched when no name is specified
  }
"""

import json
from pathlib import Path

CONFIG_PATH = Path("~/.claude/game_config.json").expanduser()

_DEFAULTS = {
    "auto_launch": False,
    "min_prompt_length": 20,
    "default_game": "flappy-bird",
}


def load() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text())
        return {**_DEFAULTS, **data}
    except Exception:
        return dict(_DEFAULTS)


def save(config: dict) -> None:
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2))
    tmp.rename(CONFIG_PATH)


def set_auto_launch(enabled: bool) -> None:
    cfg = load()
    cfg["auto_launch"] = enabled
    save(cfg)


def set_default_game(game_name: str) -> None:
    cfg = load()
    cfg["default_game"] = game_name
    save(cfg)
