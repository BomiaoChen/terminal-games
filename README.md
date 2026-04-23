# terminal-games — Claude Code Plugin

Play terminal games while waiting for Claude to finish processing your prompts.

## How It Works

1. Submit a prompt to Claude.
2. Type `/game` (or `play a game`) to launch a game in the terminal.
3. The game runs in the **alternate screen buffer** — Claude's response streams to the normal buffer in the background.
4. When Claude finishes, the game automatically shows **"Claude is ready! Press any key..."**
5. Press any key → terminal restores → Claude's response is visible.

Multiple Claude Code tabs work independently — each session tracks its own bridge signal.

## Requirements

- **macOS only** — the game window management uses Terminal.app and AppleScript.
- **Claude Code CLI** — the auto-pause/resume features rely on Claude Code's hook system and are not available in the web app.
- **Python 3.9+**

## Install

### For yourself (local path)

```bash
# Add the local marketplace (one-time)
claude plugin marketplace add ~/src/local-marketplace

# Install the plugin
claude plugin install terminal-games@local-marketplace
```

### Sharing with teammates (Git repo)

1. Push `local-marketplace/` to a shared Git repository.

2. Teammates run:
   ```bash
   claude marketplace add https://github.com/BomiaoChen/terminal-games.git
   claude plugin install terminal-games
   ```

3. To pick up future updates:
   ```bash
   claude marketplace sync
   claude plugin update terminal-games
   ```

### Sharing without Git

1. Zip and share the `local-marketplace/` folder.

2. Teammate extracts it, then runs:
   ```bash
   claude marketplace add /path/to/local-marketplace
   claude plugin install terminal-games
   ```

## Usage

```
/game               — launch the default game (Flappy Bird)
/game flappy-bird   — launch Flappy Bird explicitly
```

### Controls

| Key | Action |
|-----|--------|
| `SPACE` or `↑` | Flap |
| `P` | Pause / Resume |
| `Q` or `Esc` | Quit |
| `SPACE` (on death) | Restart |

Pause is built into the base class — all games get it automatically.

## Progress Tracking & Leaderboard

Scores are saved to `game_state.json` **inside the plugin repo** so all players
who share the repo contribute to the same leaderboard. The file is intentionally
committed — pull/push to sync scores with teammates.

Each player is identified by their git global email (`git config --global user.email`).
On first run after upgrading, any existing personal scores in `~/.claude/game_state.json`
are automatically migrated to the shared file.

Run `/leaderboard` to see the top 5 plays across all players.

## Adding a New Game

1. Create `games/<name>/game.py` — subclass `Game`, implement `run_frame` and `get_score`:

```python
from games.base import Game

class MyGame(Game):
    title = "My Game"

    def run_frame(self, stdscr, dt: float, key: int) -> bool:
        # Draw one frame. key is the current keypress (-1 if none).
        # Return False to quit. [P] pause is handled by the base class —
        # run_frame is never called while the game is paused.
        ...

    def get_score(self) -> int:
        return self._score
```

2. Create `games/<name>/__init__.py`:

```python
from games.registry import register
from games.myname.game import MyGame
register("my-game")(MyGame)
```

3. Add one import line to `games/__init__.py`:

```python
from . import myname  # noqa: F401
```

That's it — no other files need to change. `/game my-game` will work immediately.

## File Structure

```
local-marketplace/
└── plugins/
    └── terminal-games/
        ├── .claude-plugin/plugin.json   # Plugin manifest
        ├── hooks/
        │   ├── hooks.json               # Registers UserPromptSubmit + Stop hooks
        │   ├── user_prompt_submit_hook.py
        │   └── stop_hook.py
        ├── skills/
        │   ├── game/
        │   │   ├── SKILL.md             # /game skill definition
        │   │   └── launch_game.py       # Launcher with banner + score summary
        │   └── leaderboard/
        │       ├── SKILL.md             # /leaderboard skill definition
        │       └── leaderboard.py       # Top-5 plays output
        ├── games/
        │   ├── base.py                  # Abstract Game class
        │   ├── registry.py              # @register decorator
        │   └── flappy_bird/game.py      # Flappy Bird implementation
        └── lib/
            ├── bridge.py                # IPC bridge (session-scoped files)
            ├── state_manager.py         # Persistent progress storage
            └── user_identity.py         # User ID resolution
```
