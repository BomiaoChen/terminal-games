---
name: leaderboard
description: >
  Use this skill when the user types "/leaderboard", "show leaderboard",
  "top scores", "high scores", "best plays", "my scores", or
  "show my top plays". Prints the top 5 highest-scoring plays for the
  current user.
user-invocable: true
argument-hint: "[game-name]"
---

When this skill is invoked:

If the argument is `all` (e.g. `/leaderboard all`), run:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/leaderboard/leaderboard.py all
```

If a specific game name is provided (e.g. `/leaderboard 2048`), run:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/leaderboard/leaderboard.py <game-name>
```

Otherwise (no argument), run:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/leaderboard/leaderboard.py
```

Print the raw output to the user exactly as returned — do not reformat or summarize it.
