---
name: game
description: >
  Use this skill when the user types "/game", "play a game", "launch game",
  "start flappy bird", "play while waiting", "terminal game",
  "/game on", "/game off", "enable auto-launch", or "disable auto-launch".
  Launches an interactive terminal game in a new window while Claude works.
  Claude signals completion via a bridge file; the game shows "Claude is ready!"
  when done. Auto-launch mode opens the game automatically on every long prompt.
user-invocable: true
argument-hint: "[game-name | on | off]"
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

**`/game` or `/game flappy-bird`** — launch the game now:
1. Tell the user: "Launching Flappy Bird in a new window. Controls: [SPACE] to flap, [Q] to quit. I'll signal the game when I'm done."
2. Run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/game/launch_game.py flappy-bird
   ```
3. Do not add any further commentary after the Bash tool returns.
