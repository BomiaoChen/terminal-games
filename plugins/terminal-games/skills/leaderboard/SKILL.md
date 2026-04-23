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

Run:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/leaderboard/leaderboard.py flappy-bird
```

Print the raw output to the user exactly as returned — do not reformat or summarize it.
