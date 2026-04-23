"""
Git data fetcher for the Git Archaeology game.
Reads commit history from a git repo (auto-detected from cwd or common ~/src repos).
"""

import os
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _configured_repo() -> str | None:
    """Return explicitly configured repo path from game_config, or None."""
    try:
        from lib.game_config import load as load_config
        path = load_config().get("git_archaeology_repo", "")
        if path:
            p = Path(path).expanduser()
            if p.exists() and (p / ".git").exists():
                return str(p)
    except Exception:
        pass
    return None


def _find_repo() -> str | None:
    """Return path to a usable git repo. Prefers config > cwd > most-recently-committed ~/src repo."""
    # Check explicit config first
    configured = _configured_repo()
    if configured:
        return configured

    # Try cwd first
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=os.getcwd()
    )
    if result.returncode == 0:
        return result.stdout.strip()

    # Fall back to the most recently committed-to git repo under ~/src
    src = Path("~/src").expanduser()
    if not src.exists():
        return None

    best_repo = None
    best_ts = 0
    for d in src.iterdir():
        if not (d / ".git").exists():
            continue
        try:
            r = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                capture_output=True, text=True, cwd=str(d), timeout=3
            )
            if r.returncode == 0 and r.stdout.strip():
                ts = int(r.stdout.strip())
                if ts > best_ts:
                    best_ts = ts
                    best_repo = str(d)
        except Exception:
            continue
    return best_repo


def _run_git(args: list[str], repo: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=repo, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        return ""


def _start_of_month() -> str:
    """Return ISO date string for the first day of the current month."""
    from datetime import date
    today = date.today()
    return str(today.replace(day=1))


def load_commits(repo: str) -> list[dict]:
    """Return commits since the start of the current month."""
    sep = "|||"
    fmt = f"%H{sep}%an{sep}%ae{sep}%ad{sep}%s{sep}%P"
    since = _start_of_month()
    raw = _run_git(
        ["log", f"--format={fmt}", "--date=short", f"--since={since}"],
        repo
    )
    commits = []
    for line in raw.splitlines():
        parts = line.split(sep)
        if len(parts) >= 5:
            commits.append({
                "hash":    parts[0][:8],
                "author":  parts[1],
                "email":   parts[2],
                "date":    parts[3],
                "subject": parts[4],
                "merge":   bool(parts[5].strip().split()) if len(parts) > 5 and " " in parts[5] else False,
            })
    return commits


def load_file_stats(repo: str) -> list[tuple[str, int]]:
    """Return [(filename, change_count)] for commits since start of month."""
    since = _start_of_month()
    raw = _run_git(
        ["log", f"--since={since}", "--name-only", "--format=", "--no-merges"],
        repo
    )
    counter: Counter = Counter()
    for line in raw.splitlines():
        line = line.strip()
        if line:
            counter[line] += 1
    return counter.most_common(20)


class GitData:
    def __init__(self):
        self.repo = _find_repo()
        self.repo_name = Path(self.repo).name if self.repo else "unknown"
        self.commits: list[dict] = []
        self.file_stats: list[tuple[str, int]] = []
        self.error: str = ""

    def load(self) -> bool:
        if not self.repo:
            self.error = "No git repository found. Open Claude Code inside a git repo."
            return False
        try:
            since = _start_of_month()
            self.commits = [c for c in load_commits(self.repo) if c["date"] >= since]
            self.file_stats = load_file_stats(self.repo)
            if not self.commits:
                self.error = f"No commits found since {_start_of_month()} — try a busier month!"
                return False
            return True
        except Exception as e:
            self.error = f"Git error: {e}"
            return False

    # ---- Question generators ----

    def q_guess_author(self) -> dict | None:
        """Show a commit subject, guess the author."""
        # Pick a non-merge commit with a meaningful message
        pool = [c for c in self.commits
                if not c["merge"] and len(c["subject"]) > 15]
        if len(pool) < 4:
            return None

        commit = random.choice(pool)
        correct = commit["author"]

        # Build 3 wrong authors from other commits
        other_authors = list({c["author"] for c in self.commits if c["author"] != correct})
        if len(other_authors) < 3:
            return None
        wrong = random.sample(other_authors, 3)

        options = [correct] + wrong
        random.shuffle(options)

        return {
            "type": "guess_author",
            "question": f'Who wrote this commit?\n\n  "{commit["subject"]}"',
            "options": options,
            "answer": correct,
            "detail": f"{commit['hash']} on {commit['date']}",
        }

    def q_top_contributor(self) -> dict | None:
        """Who made the most commits in the last N?"""
        non_merge = [c for c in self.commits if not c["merge"]]
        if len(non_merge) < 10:
            return None

        counter: Counter = Counter(c["author"] for c in non_merge)
        top4 = counter.most_common(4)
        if len(top4) < 4:
            return None

        correct = top4[0][0]
        options = [name for name, _ in top4]
        random.shuffle(options)

        return {
            "type": "top_contributor",
            "question": f"Who made the most commits\nthis month? ({len(non_merge)} total)",
            "options": options,
            "answer": correct,
            "detail": f"{counter[correct]} commits by {correct}",
        }

    def q_hottest_file(self) -> dict | None:
        """Which file was changed most recently?"""
        if len(self.file_stats) < 4:
            return None

        correct_file, correct_count = self.file_stats[0]
        wrong_files = [f for f, _ in self.file_stats[1:4]]

        # Shorten paths for display
        def shorten(p: str) -> str:
            parts = p.split("/")
            return "/".join(parts[-2:]) if len(parts) > 2 else p

        options = [shorten(correct_file)] + [shorten(f) for f in wrong_files]
        random.shuffle(options)
        correct_short = shorten(correct_file)

        return {
            "type": "hottest_file",
            "question": "Which file has been changed\nthe most in recent commits?",
            "options": options,
            "answer": correct_short,
            "detail": f"Changed {correct_count} times: {correct_file}",
        }

    def q_commit_date(self) -> dict | None:
        """When was this commit made? (month/year)"""
        pool = [c for c in self.commits if not c["merge"] and len(c["subject"]) > 15]
        if len(pool) < 4:
            return None

        commit = random.choice(pool)
        correct_date = commit["date"]  # YYYY-MM-DD

        # Generate 3 plausible wrong dates from other commits
        other_dates = list({c["date"] for c in self.commits if c["date"] != correct_date})
        if len(other_dates) < 3:
            return None
        wrong_dates = random.sample(other_dates, 3)

        options = [correct_date] + wrong_dates
        random.shuffle(options)

        return {
            "type": "commit_date",
            "question": f'When was this committed?\n\n  "{commit["subject"][:60]}"',
            "options": options,
            "answer": correct_date,
            "detail": f"by {commit['author']}",
        }

    def next_question(self) -> dict | None:
        """Pick a random question type, retrying up to 10 times."""
        generators = [
            self.q_guess_author,
            self.q_top_contributor,
            self.q_hottest_file,
            self.q_commit_date,
        ]
        for _ in range(10):
            q = random.choice(generators)()
            if q:
                return q
        return None
