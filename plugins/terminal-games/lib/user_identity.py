"""
Resolve a stable user identifier for progress tracking and future leaderboard use.

Resolution order:
  1. git config --global user.email  (preferred — matches AppFolio convention)
  2. $USER@$HOSTNAME                 (machine-scoped fallback)
  3. socket.gethostname()            (last resort)
"""

import os
import socket
import subprocess


def resolve_user_id() -> str:
    # 1. Git global email
    try:
        result = subprocess.run(
            ["git", "config", "--global", "user.email"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        email = result.stdout.strip()
        if email:
            return email
    except Exception:
        pass

    # 2. $USER@$HOSTNAME
    user = os.environ.get("USER", "")
    hostname = socket.gethostname()
    if user:
        return f"{user}@{hostname}"

    # 3. Hostname only
    return hostname
