"""
Flappy Bird — terminal implementation using Python curses.

Physics (all units in terminal character cells):
  GRAVITY       = 25.0 chars/sec²   downward acceleration
  FLAP_VELOCITY = -10.0 chars/sec   upward velocity on Space/Up
  PIPE_SPEED    = 12.0 chars/sec    horizontal scroll
  PIPE_GAP      = 7 chars           vertical open gap between top/bottom pipe
  PIPE_INTERVAL = 20 chars          horizontal distance between pipe pairs
  FPS_CAP       = 30                from base class

Controls:  Space or Up arrow = flap.  Q or Esc = quit.
On death:  Space to restart,  Q/Esc to quit.
"""

import curses
import os
import random
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from games.base import Game

# Physics constants
GRAVITY = 25.0
FLAP_VELOCITY = -10.0
PIPE_SPEED = 12.0
PIPE_GAP = 7
PIPE_INTERVAL = 20

# Bird fixed column
BIRD_COL = 10

# Characters
BIRD_CHAR = ">"
PIPE_CHAR = "|"
GAP_CHAR = " "


@dataclass
class Pipe:
    x: float          # fractional column position
    gap_top: int      # row where the gap starts (inclusive)

    @property
    def gap_bottom(self) -> int:
        return self.gap_top + PIPE_GAP - 1


class FlappyBird(Game):
    title = "Flappy Bird"
    controls_hint = "[SPACE] Flap   [P] Pause   [Q] Quit"

    # ---- Game state ----

    def init(self, stdscr) -> None:
        self._reset(stdscr)

    def _reset(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        self._height = h
        self._width = w
        self._bird_y: float = h / 2
        self._bird_vy: float = 0.0
        self._pipes: list[Pipe] = []
        self._score: int = 0
        self._alive: bool = True
        self._game_over_shown: bool = False
        # Seed initial pipe off-screen to the right
        self._spawn_pipe(w + PIPE_INTERVAL)

    def _spawn_pipe(self, x: float) -> None:
        h = self._height
        # Gap can start anywhere from row 1 to (h - PIPE_GAP - 1)
        gap_top = random.randint(1, max(1, h - PIPE_GAP - 2))
        self._pipes.append(Pipe(x=float(x), gap_top=gap_top))

    # ---- Frame loop ----

    def run_frame(self, stdscr, dt: float, key: int) -> bool:
        # Handle terminal resize
        h, w = stdscr.getmaxyx()
        if h != self._height or w != self._width:
            self._height, self._width = h, w
            self._bird_y = min(self._bird_y, h - 2)

        if self._alive:
            return self._frame_alive(stdscr, dt, key)
        else:
            return self._frame_dead(stdscr, key)

    def _frame_alive(self, stdscr, dt: float, key: int) -> bool:
        # Input
        if key in (ord(" "), ord("w"), curses.KEY_UP):
            self._bird_vy = FLAP_VELOCITY
        elif key in (ord("q"), ord("Q"), 27):  # 27 = Esc
            return False

        # Physics
        self._bird_vy += GRAVITY * dt
        self._bird_y += self._bird_vy * dt

        # Move pipes
        for pipe in self._pipes:
            pipe.x -= PIPE_SPEED * dt

        # Remove pipes scrolled off-screen left, spawn new ones
        self._pipes = [p for p in self._pipes if p.x > -2]
        if not self._pipes or self._pipes[-1].x < self._width - PIPE_INTERVAL:
            self._spawn_pipe(self._width + 2)

        # Score: increment when bird passes a pipe center
        for pipe in self._pipes:
            if int(pipe.x) == BIRD_COL:
                self._score += 1

        # Collision detection
        bird_row = int(self._bird_y)
        if bird_row < 0 or bird_row >= self._height - 1:
            self._alive = False
        else:
            for pipe in self._pipes:
                pipe_col = int(pipe.x)
                if abs(pipe_col - BIRD_COL) <= 1:
                    if not (pipe.gap_top <= bird_row <= pipe.gap_bottom):
                        self._alive = False
                        break

        self._render(stdscr)
        return True

    def _frame_dead(self, stdscr, key: int) -> bool:
        if key in (ord(" "), ord("w"), curses.KEY_UP):
            self._reset(stdscr)
            return True
        elif key in (ord("q"), ord("Q"), 27):
            return False
        self._render_game_over(stdscr)
        return True

    # ---- Rendering ----

    def _render(self, stdscr) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        # Draw pipes
        pipe_attr = curses.color_pair(2) if curses.has_colors() else curses.A_NORMAL
        for pipe in self._pipes:
            col = int(pipe.x)
            if col < 0 or col >= w:
                continue
            for row in range(h - 1):
                if not (pipe.gap_top <= row <= pipe.gap_bottom):
                    try:
                        stdscr.addch(row, col, PIPE_CHAR, pipe_attr)
                    except curses.error:
                        pass

        # Draw bird
        bird_row = int(self._bird_y)
        bird_attr = curses.color_pair(1) if curses.has_colors() else curses.A_BOLD
        try:
            stdscr.addch(bird_row, BIRD_COL, BIRD_CHAR, bird_attr)
        except curses.error:
            pass

        # Draw score (top-right)
        score_attr = curses.color_pair(3) if curses.has_colors() else curses.A_NORMAL
        score_str = f" Score: {self._score} "
        try:
            stdscr.addstr(0, max(0, w - len(score_str) - 1), score_str, score_attr)
        except curses.error:
            pass

        # Draw controls hint (bottom)
        hint = " [SPACE] Flap  [P] Pause  [Q] Quit "
        try:
            stdscr.addstr(h - 1, 0, hint[:w - 1])
        except curses.error:
            pass

    def _render_game_over(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        lines = [
            f"  GAME OVER  —  Score: {self._score}  ",
            "  [SPACE] Restart   [Q] Quit  ",
        ]
        for i, line in enumerate(lines):
            y = h // 2 - 1 + i
            x = max(0, (w - len(line)) // 2)
            try:
                stdscr.addstr(y, x, line, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
        stdscr.refresh()

    # ---- Score ----

    def get_score(self) -> int:
        return self._score
