"""
2048 — terminal implementation using Python curses.

Rules:
  - 4×4 grid of numbered tiles
  - Arrow keys slide all tiles in that direction
  - Matching tiles merge into their sum
  - A new tile (90% chance 2, 10% chance 4) spawns after each move
  - Reach 2048 to win; game over when no moves remain

Score = sum of all merged tile values (matches classic 2048 scoring).
"""

import curses
import os
import random
import sys
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from games.base import Game
from lib.game_config import load as load_config, save as save_config

SIZE = 4
WIN_TILE = 2048

# Color pair indices (1-3 reserved by base class)
_PAIR_EMPTY   = 4
_PAIR_2       = 5
_PAIR_4       = 6
_PAIR_8       = 7
_PAIR_16      = 8
_PAIR_32      = 9
_PAIR_64      = 10
_PAIR_128     = 11
_PAIR_256     = 12
_PAIR_512     = 13
_PAIR_1024    = 14
_PAIR_2048    = 15
_PAIR_HIGH    = 16

_TILE_COLORS = {
    0:    _PAIR_EMPTY,
    2:    _PAIR_2,
    4:    _PAIR_4,
    8:    _PAIR_8,
    16:   _PAIR_16,
    32:   _PAIR_32,
    64:   _PAIR_64,
    128:  _PAIR_128,
    256:  _PAIR_256,
    512:  _PAIR_512,
    1024: _PAIR_1024,
    2048: _PAIR_2048,
}


def _slide_row(row: list[int]) -> tuple[list[int], int]:
    """Slide and merge a single row to the left. Returns (new_row, points_earned)."""
    tiles = [x for x in row if x != 0]
    points = 0
    merged = []
    i = 0
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            val = tiles[i] * 2
            merged.append(val)
            points += val
            i += 2
        else:
            merged.append(tiles[i])
            i += 1
    merged += [0] * (SIZE - len(merged))
    return merged, points


def _move(board: list[list[int]], direction: str) -> tuple[list[list[int]], int, bool]:
    """Apply a move. direction in ('left','right','up','down').
    Returns (new_board, points, moved).
    """
    rotations = {"left": 0, "down": 1, "right": 2, "up": 3}
    r = rotations[direction]

    # Rotate board so we always slide left
    b = deepcopy(board)
    for _ in range(r):
        b = [list(row) for row in zip(*b[::-1])]

    total_points = 0
    moved = False
    for i, row in enumerate(b):
        new_row, pts = _slide_row(row)
        if new_row != row:
            moved = True
        b[i] = new_row
        total_points += pts

    # Rotate back
    for _ in range((4 - r) % 4):
        b = [list(row) for row in zip(*b[::-1])]

    return b, total_points, moved


def _spawn(board: list[list[int]]) -> list[list[int]]:
    """Place a 2 (90%) or 4 (10%) on a random empty cell."""
    empties = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == 0]
    if not empties:
        return board
    r, c = random.choice(empties)
    board[r][c] = 4 if random.random() < 0.1 else 2
    return board


def _can_move(board: list[list[int]]) -> bool:
    for d in ("left", "right", "up", "down"):
        _, _, moved = _move(board, d)
        if moved:
            return True
    return False


def _has_won(board: list[list[int]]) -> bool:
    return any(board[r][c] >= WIN_TILE for r in range(SIZE) for c in range(SIZE))


class Twenty48(Game):
    title = "2048"
    controls_hint = "[←→↑↓] Move   [P] Pause   [R] Restart   [Q] Quit"

    # ---- Setup ----

    def _setup_colors(self) -> None:
        super()._setup_colors()
        if not curses.has_colors():
            return
        # tile background colors (foreground=black for readability on light tiles,
        # white on dark tiles)
        def p(pair, fg, bg):
            try:
                curses.init_pair(pair, fg, bg)
            except Exception:
                pass

        p(_PAIR_EMPTY, curses.COLOR_WHITE,   -1)
        p(_PAIR_2,     curses.COLOR_BLACK,    curses.COLOR_WHITE)
        p(_PAIR_4,     curses.COLOR_BLACK,    curses.COLOR_YELLOW)
        p(_PAIR_8,     curses.COLOR_WHITE,    curses.COLOR_RED)
        p(_PAIR_16,    curses.COLOR_WHITE,    curses.COLOR_RED)
        p(_PAIR_32,    curses.COLOR_WHITE,    curses.COLOR_RED)
        p(_PAIR_64,    curses.COLOR_WHITE,    curses.COLOR_RED)
        p(_PAIR_128,   curses.COLOR_BLACK,    curses.COLOR_YELLOW)
        p(_PAIR_256,   curses.COLOR_BLACK,    curses.COLOR_YELLOW)
        p(_PAIR_512,   curses.COLOR_BLACK,    curses.COLOR_YELLOW)
        p(_PAIR_1024,  curses.COLOR_BLACK,    curses.COLOR_YELLOW)
        p(_PAIR_2048,  curses.COLOR_BLACK,    curses.COLOR_GREEN)
        p(_PAIR_HIGH,  curses.COLOR_BLACK,    curses.COLOR_CYAN)

    def init(self, stdscr) -> None:
        self._won_shown = False
        if not self._restore():
            self._new_game()

    def _restore(self) -> bool:
        """Load saved board from game_config. Returns True if a valid state was found."""
        try:
            cfg = load_config()
            saved = cfg.get("2048_state")
            if not saved:
                return False
            board = saved["board"]
            # Validate shape
            if len(board) != SIZE or any(len(r) != SIZE for r in board):
                return False
            self._board = board
            self._score = saved.get("score", 0)
            self._game_over = False
            return True
        except Exception:
            return False

    def _save_state(self) -> None:
        """Persist current board to game_config after each move."""
        try:
            cfg = load_config()
            cfg["2048_state"] = {"board": self._board, "score": self._score}
            save_config(cfg)
        except Exception:
            pass

    def _clear_state(self) -> None:
        """Remove saved board (game over or explicit restart)."""
        try:
            cfg = load_config()
            cfg.pop("2048_state", None)
            save_config(cfg)
        except Exception:
            pass

    def _new_game(self) -> None:
        self._board: list[list[int]] = [[0] * SIZE for _ in range(SIZE)]
        self._score: int = 0
        self._board = _spawn(self._board)
        self._board = _spawn(self._board)
        self._game_over = False
        self._clear_state()

    # ---- Frame loop ----

    def run_frame(self, stdscr, dt: float, key: int) -> bool:
        if key in (ord("q"), ord("Q"), 27):
            return False

        if self._game_over:
            if key in (ord("r"), ord("R"), ord(" ")):
                self._new_game()
                self._won_shown = False
            self._render(stdscr)
            return True

        direction = None
        if key in (curses.KEY_LEFT,  ord("a"), ord("A"), ord("h")):
            direction = "left"
        elif key in (curses.KEY_RIGHT, ord("d"), ord("D"), ord("l")):
            direction = "right"
        elif key in (curses.KEY_UP,   ord("w"), ord("W"), ord("k")):
            direction = "up"
        elif key in (curses.KEY_DOWN, ord("s"), ord("S"), ord("j")):
            direction = "down"

        if direction:
            new_board, pts, moved = _move(self._board, direction)
            if moved:
                self._board = _spawn(new_board)
                self._score += pts
                if not _can_move(self._board):
                    self._game_over = True
                    self._clear_state()
                else:
                    self._save_state()

        self._render(stdscr)
        return True

    # ---- Rendering ----

    # Each tile is CELL_W chars wide, CELL_H rows tall (including border)
    _CELL_W = 7
    _CELL_H = 3

    def _render(self, stdscr) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        board_w = SIZE * self._CELL_W + 1
        board_h = SIZE * self._CELL_H + 1
        start_x = max(0, (w - board_w) // 2)
        start_y = max(1, (h - board_h - 4) // 2)  # leave room for header/footer

        self._render_header(stdscr, start_y, w)
        self._render_board(stdscr, start_y + 2, start_x)
        self._render_footer(stdscr, h, w)

        if self._game_over:
            self._render_game_over(stdscr, h, w)
        elif _has_won(self._board) and not self._won_shown:
            self._render_win(stdscr, h, w)

    def _render_header(self, stdscr, y: int, w: int) -> None:
        title = f" 2048 "
        score = f" Score: {self._score} "
        score_attr = curses.color_pair(3) if curses.has_colors() else curses.A_BOLD
        try:
            stdscr.addstr(y, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
            stdscr.addstr(y, max(0, w - len(score) - 1), score, score_attr)
        except curses.error:
            pass

    def _render_board(self, stdscr, start_y: int, start_x: int) -> None:
        cw, ch = self._CELL_W, self._CELL_H
        for r in range(SIZE):
            for c in range(SIZE):
                val = self._board[r][c]
                cy = start_y + r * ch
                cx = start_x + c * cw

                pair = _TILE_COLORS.get(val, _PAIR_HIGH)
                attr = curses.color_pair(pair) if curses.has_colors() else curses.A_NORMAL

                # Draw cell border + fill
                label = str(val) if val else "·"
                # Top border row
                self._draw_cell(stdscr, cy, cx, cw, ch, label, attr)

    def _draw_cell(self, stdscr, y: int, x: int, w: int, h: int, label: str, attr) -> None:
        """Draw a single tile box."""
        # Top border
        try:
            stdscr.addstr(y, x, "+" + "-" * (w - 2) + "+")
        except curses.error:
            pass

        # Middle rows (only 1 content row for CELL_H=3)
        for row in range(1, h - 1):
            content = label.center(w - 2)
            try:
                stdscr.addstr(y + row, x, "|", curses.A_DIM)
                stdscr.addstr(y + row, x + 1, content, attr | curses.A_BOLD)
                stdscr.addstr(y + row, x + w - 1, "|", curses.A_DIM)
            except curses.error:
                pass

        # Bottom border (shared with next row's top)
        try:
            stdscr.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+")
        except curses.error:
            pass

    def _render_footer(self, stdscr, h: int, w: int) -> None:
        hint = " [←→↑↓] Move  [P] Pause  [R] Restart  [Q] Quit "
        try:
            stdscr.addstr(h - 1, 0, hint[:w - 1])
        except curses.error:
            pass

    def _render_game_over(self, stdscr, h: int, w: int) -> None:
        lines = [
            f"  GAME OVER  —  Score: {self._score}  ",
            "  [R] New Game   [Q] Quit  ",
        ]
        for i, line in enumerate(lines):
            y = h // 2 + i
            x = max(0, (w - len(line)) // 2)
            try:
                stdscr.addstr(y, x, line, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
        stdscr.refresh()

    def _render_win(self, stdscr, h: int, w: int) -> None:
        self._won_shown = True
        lines = [
            "  You reached 2048!  ",
            "  Keep going or [Q] to quit  ",
        ]
        for i, line in enumerate(lines):
            y = h // 2 + i
            x = max(0, (w - len(line)) // 2)
            try:
                stdscr.addstr(y, x, line, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
        stdscr.refresh()

    def teardown(self, stdscr) -> None:
        # Persist board if the game is still in progress (quit mid-game or
        # Claude finished). Don't save if game_over — board was already cleared.
        if not self._game_over:
            self._save_state()

    # ---- Score ----

    def get_score(self) -> int:
        return self._score
