"""
Game config stored at ~/.claude/game_config.json.

Schema:
  {
    "auto_launch": false,          -- launch game automatically on every long prompt
    "min_prompt_length": 20,       -- minimum prompt length to trigger auto-launch
    "default_game": "flappy-bird", -- game launched when no name is specified
    "git_archaeology_repo": "",    -- path to repo used by Git Archaeology (empty = auto-detect)
    "slack_bot_token": "",         -- Slack bot OAuth token (xoxb-...)
    "slack_digest_channels": [],   -- list of channel IDs to watch
    "slack_digest_last_read": {},  -- { "<channel_id>": "<ISO8601>" } per-channel cursor
    "window_font_size": 0,         -- Terminal font size (0 = use Terminal default)
    "window_rows": 0,              -- Terminal window rows (0 = use Terminal default)
    "window_cols": 0               -- Terminal window columns (0 = use Terminal default)
  }
"""

import json
from pathlib import Path

CONFIG_PATH = Path("~/.claude/game_config.json").expanduser()

_DEFAULTS = {
    "auto_launch": False,
    "min_prompt_length": 20,
    "default_game": "flappy-bird",
    "git_archaeology_repo": "",
    "slack_bot_token": "",
    "slack_digest_channels": [],
    "slack_digest_last_read": {},
    "window_font_size": 0,
    "window_rows": 0,
    "window_cols": 0,
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


def set_git_archaeology_repo(path: str) -> None:
    cfg = load()
    cfg["git_archaeology_repo"] = path
    save(cfg)


def set_window_settings(font_size: int | None, rows: int | None, cols: int | None) -> None:
    cfg = load()
    if font_size is not None:
        cfg["window_font_size"] = font_size
    if rows is not None:
        cfg["window_rows"] = rows
    if cols is not None:
        cfg["window_cols"] = cols
    save(cfg)
