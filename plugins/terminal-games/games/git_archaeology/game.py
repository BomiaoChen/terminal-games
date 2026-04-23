"""
Git Archaeology — trivia game from your own git history.

Question types:
  - Guess the author of a commit message
  - Who made the most commits?
  - Which file was changed most?
  - When was this commit made?

Controls:
  1 / 2 / 3 / 4   Select answer
  ↑ / ↓            Navigate options
  Enter            Confirm selection
  N                Skip to next question
  Q                Quit
"""

import curses
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from games.base import Game
from games.git_archaeology.git_data import GitData

_PAIR_HEADER   = 4
_PAIR_CORRECT  = 5
_PAIR_WRONG    = 6
_PAIR_SELECTED = 7
_PAIR_DIM      = 8
_PAIR_ACCENT   = 9


class GitArchaeology(Game):
    title = "Git Archaeology"
    controls_hint = "[1-4] Answer  [↑↓] Navigate  [Enter] Confirm  [N] Skip  [Q] Quit"

    # ---- Setup ----

    def _setup_colors(self) -> None:
        super()._setup_colors()
        if not curses.has_colors():
            return
        def p(pair, fg, bg):
            try:
                curses.init_pair(pair, fg, bg)
            except Exception:
                pass
        p(_PAIR_HEADER,   curses.COLOR_BLACK,  curses.COLOR_CYAN)
        p(_PAIR_CORRECT,  curses.COLOR_BLACK,  curses.COLOR_GREEN)
        p(_PAIR_WRONG,    curses.COLOR_WHITE,  curses.COLOR_RED)
        p(_PAIR_SELECTED, curses.COLOR_BLACK,  curses.COLOR_YELLOW)
        p(_PAIR_DIM,      curses.COLOR_WHITE,  -1)
        p(_PAIR_ACCENT,   curses.COLOR_YELLOW, -1)

    def init(self, stdscr) -> None:
        self._data = GitData()
        self._score = 0
        self._total = 0
        self._streak = 0
        self._best_streak = 0
        self._selected = 0       # currently highlighted option index
        self._state = "loading"  # loading | question | revealed | error
        self._question: dict | None = None
        self._feedback = ""

        stdscr.nodelay(False)  # block on input — no animation needed

        # Load git data
        h, w = stdscr.getmaxyx()
        self._draw_header(stdscr, w)
        try:
            stdscr.addstr(h // 2, max(0, (w - 30) // 2), "  Loading git history…  ", curses.A_BOLD)
        except curses.error:
            pass
        stdscr.refresh()

        if self._data.load():
            self._next_question()
        else:
            self._state = "error"

        self._render(stdscr)

    def _next_question(self) -> None:
        q = self._data.next_question()
        if q:
            self._question = q
            self._selected = 0
            self._state = "question"
            self._feedback = ""
        else:
            self._state = "error"
            self._data.error = "Not enough git data to generate questions."

    # ---- Frame loop ----

    def run_frame(self, stdscr, dt: float, key: int) -> bool:
        if key in (ord("q"), ord("Q")):
            return False

        if self._state == "error":
            self._render(stdscr)
            return True

        if self._state == "question":
            self._handle_question_input(key)
        elif self._state == "revealed":
            if key in (ord("n"), ord("N"), ord(" "), curses.KEY_ENTER, ord("\n"), ord("\r")):
                self._next_question()

        self._render(stdscr)
        return True

    def _handle_question_input(self, key: int) -> None:
        q = self._question
        if not q:
            return
        n = len(q["options"])

        # Number keys 1-4
        if ord("1") <= key <= ord("4"):
            idx = key - ord("1")
            if idx < n:
                self._selected = idx
                self._confirm()
        elif key == curses.KEY_UP and self._selected > 0:
            self._selected -= 1
        elif key == curses.KEY_DOWN and self._selected < n - 1:
            self._selected += 1
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            self._confirm()
        elif key in (ord("n"), ord("N")):
            self._next_question()

    def _confirm(self) -> None:
        q = self._question
        if not q:
            return
        chosen = q["options"][self._selected]
        self._total += 1
        if chosen == q["answer"]:
            self._score += 1
            self._streak += 1
            self._best_streak = max(self._best_streak, self._streak)
            bonus = f" STREAK x{self._streak}!" if self._streak > 2 else ""
            self._feedback = f"Correct!{bonus}"
        else:
            self._streak = 0
            self._feedback = f"Wrong — it was: {q['answer']}"
        self._state = "revealed"

    # ---- Rendering ----

    def _render(self, stdscr) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        self._draw_header(stdscr, w)

        if self._state == "error":
            err = self._data.error
            try:
                stdscr.addstr(h // 2, max(0, (w - len(err)) // 2), err[:w - 1],
                              curses.color_pair(_PAIR_WRONG) if curses.has_colors() else curses.A_BOLD)
                hint = "[Q] Quit"
                stdscr.addstr(h - 1, 0, f" {hint}")
            except curses.error:
                pass
            stdscr.refresh()
            return

        if self._state in ("question", "revealed") and self._question:
            self._render_question(stdscr, h, w)

        stdscr.refresh()

    def _draw_header(self, stdscr, w: int) -> None:
        repo = self._data.repo_name if self._data.repo_name else "?"
        score_str = f" {self._score}/{self._total}"
        streak_str = f" 🔥{self._streak}" if self._streak > 1 else ""
        title = f" Git Archaeology — {repo}{streak_str}"
        attr = curses.color_pair(_PAIR_HEADER) if curses.has_colors() else curses.A_REVERSE
        try:
            line = title.ljust(w - len(score_str) - 1)[:w - len(score_str) - 1]
            stdscr.addstr(0, 0, line, attr)
            stdscr.addstr(0, w - len(score_str) - 1, score_str, attr | curses.A_BOLD)
        except curses.error:
            pass

    def _render_question(self, stdscr, h: int, w: int) -> None:
        q = self._question
        if not q:
            return

        # Question type label
        type_labels = {
            "guess_author":    "GUESS THE AUTHOR",
            "top_contributor": "TOP CONTRIBUTOR",
            "hottest_file":    "HOT FILE",
            "commit_date":     "COMMIT DATE",
        }
        label = type_labels.get(q["type"], "QUESTION")
        accent = curses.color_pair(_PAIR_ACCENT) if curses.has_colors() else curses.A_BOLD
        try:
            stdscr.addstr(2, 2, f"[ {label} ]", accent | curses.A_BOLD)
        except curses.error:
            pass

        # Question text (wrapped)
        row = 4
        for line in q["question"].split("\n"):
            for wrapped in textwrap.wrap(line, w - 4) or [line]:
                try:
                    stdscr.addstr(row, 2, wrapped[:w - 3], curses.A_BOLD)
                except curses.error:
                    pass
                row += 1
        row += 1

        # Options
        for i, opt in enumerate(q["options"]):
            prefix = f"  {i + 1}.  "
            text = f"{prefix}{opt}"

            if self._state == "revealed":
                if opt == q["answer"]:
                    attr = curses.color_pair(_PAIR_CORRECT) if curses.has_colors() else curses.A_BOLD
                elif i == self._selected and opt != q["answer"]:
                    attr = curses.color_pair(_PAIR_WRONG) if curses.has_colors() else curses.A_DIM
                else:
                    attr = curses.color_pair(_PAIR_DIM) if curses.has_colors() else curses.A_NORMAL
            else:
                if i == self._selected:
                    attr = curses.color_pair(_PAIR_SELECTED) if curses.has_colors() else curses.A_REVERSE
                else:
                    attr = curses.A_NORMAL

            try:
                stdscr.addstr(row, 0, text[:w - 1], attr)
            except curses.error:
                pass
            row += 1

        row += 1

        # Feedback / detail
        if self._state == "revealed":
            fb_attr = (curses.color_pair(_PAIR_CORRECT) if "Correct" in self._feedback
                       else curses.color_pair(_PAIR_WRONG)) if curses.has_colors() else curses.A_BOLD
            try:
                stdscr.addstr(row, 2, self._feedback[:w - 3], fb_attr | curses.A_BOLD)
            except curses.error:
                pass
            row += 1
            detail = q.get("detail", "")
            if detail:
                dim = curses.color_pair(_PAIR_DIM) if curses.has_colors() else curses.A_DIM
                try:
                    stdscr.addstr(row, 2, detail[:w - 3], dim)
                except curses.error:
                    pass
            row += 2
            try:
                stdscr.addstr(row, 2, "Press [N] or [Space] for next question…")
            except curses.error:
                pass

        # Footer
        hint = "[1-4] Answer  [↑↓] Navigate  [Enter] Confirm  [N] Skip  [Q] Quit"
        try:
            stdscr.addstr(h - 1, 0, f" {hint}"[:w - 1])
        except curses.error:
            pass

    def get_score(self) -> int:
        return self._score
