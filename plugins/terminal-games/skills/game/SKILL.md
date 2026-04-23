---
name: game
description: >
  Use this skill when the user types "/game", "play a game", "launch game",
  "start flappy bird", "play while waiting", "terminal game",
  "/game on", "/game off", "enable auto-launch", "disable auto-launch",
  "/game default", "set default game", "/game window", "change window size",
  "bigger font", "set font size", or "resize game window".
  Launches an interactive terminal game in a new window while Claude works.
  Claude signals completion via a bridge file; the game shows "Claude is ready!"
  when done. Auto-launch mode opens the game automatically on every long prompt.
user-invocable: true
argument-hint: "[game-name | on | off | default <game-name> | window [font=N] [rows=N] [cols=N]]"
---

When this skill is invoked:

**`/game on`** — enable auto-launch mode:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py on
```
Tell the user: "Auto-launch enabled. Flappy Bird will open automatically whenever you submit a prompt of 20+ characters."

**`/game off`** — disable auto-launch mode:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py off
```
Tell the user: "Auto-launch disabled. Use /game to launch manually."

**`/game default <name>`** — set the default game (e.g. `/game default 2048`):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py default <name>
```
Tell the user: "Default game set to: <name>. Use /game to launch it."

**`/game default`** (no name) — show current default and available games:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py default
```
Print the raw output to the user.

**`/game window`** — show current window settings:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py window
```
Print the raw output to the user.

**`/game window font=<N> rows=<N> cols=<N>`** — set window size/font (any subset of options):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py window font=<N> rows=<N> cols=<N>
```
Print the raw output to the user. Use `font=0 rows=0 cols=0` to reset to Terminal defaults.

**`/game` or `/game <name>`** — launch the game now:
1. Tell the user the game name and controls, then run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py [name]
   ```
2. Do not add any further commentary after the Bash tool returns.
