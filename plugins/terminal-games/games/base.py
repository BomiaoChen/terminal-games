"""
Abstract base class for all terminal games.

Subclasses must implement:
  - title: str           (display name shown at launch)
  - run_frame(stdscr, dt: float, key: int) -> bool  (return False to quit)

Optionally override:
  - init(stdscr)         called once after curses init
  - teardown(stdscr)     called after the frame loop ends
  - get_score() -> int   return final score for persistence

The base class provides:
  - curses.wrapper lifecycle (alternate screen buffer, terminal restore on crash)
  - Background thread polling the IPC bridge file every 500ms
  - "Claude is ready!" overlay when the Stop hook signals completion
  - Automatic score recording via StateManager on exit
  - [P] key pause/resume — dt is frozen while paused
  - Auto-pause when Claude needs user attention (approval dialog, AskUserQuestion);
    overlay changes to "Claude responded" once Claude resumes; user presses [P] to
    continue playing
  - Auto-close when a tool is denied (PostToolUse never fires within 30s, or
    Stop hook detects denial directly)
"""

import curses
import os
import sys
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.bridge import read_bridge
from lib.state_manager import StateManager

_POLL_INTERVAL = 0.5     # seconds between bridge file reads
_NEEDS_INPUT_DEBOUNCE = 1.0  # needs_input must persist this long before auto-pausing
_NEEDS_INPUT_TIMEOUT = 30.0  # close game if needs_input persists this long —
                              # indicates a denied tool where Stop didn't fire
_FPS_CAP = 30


class Game(ABC):
    title: str = "Untitled Game"
    _registry_name: str = "unknown"   # set by @register decorator

    def run(self, bridge_path: Path | None = None, session_id: str | None = None) -> None:
        """Entry point called by launch_game.py."""
        self._session_id = session_id
        self._started_at = datetime.now(timezone.utc)
        self._done_event = threading.Event()
        self._needs_input_event = threading.Event()
        self._denied_event = threading.Event()
        self._start_time = time.monotonic()

        self._poll_thread = threading.Thread(
            target=self._poll_bridge, daemon=True
        )
        self._poll_thread.start()
        curses.wrapper(self._curses_main)

    # ---- Bridge polling ----

    def _poll_bridge(self) -> None:
        if not self._session_id:
            return
        _needs_input_since: float | None = None
        while not self._done_event.is_set():
            try:
                data = read_bridge(self._session_id)
                status = data.get("status")

                if status == "done":
                    ts_str = data.get("timestamp", "")
                    if ts_str:
                        signal_time = datetime.fromisoformat(ts_str)
                        if signal_time > self._started_at:
                            self._needs_input_event.clear()
                            self._done_event.set()
                            return

                elif status == "needs_input":
                    if _needs_input_since is None:
                        _needs_input_since = time.monotonic()
                    else:
                        elapsed = time.monotonic() - _needs_input_since
                        if elapsed >= _NEEDS_INPUT_DEBOUNCE:
                            self._needs_input_event.set()
                        if elapsed >= _NEEDS_INPUT_TIMEOUT:
                            # Tool was denied and Stop didn't fire (interrupted response).
                            self._needs_input_event.clear()
                            self._denied_event.set()
                            return

                elif status == "denied":
                    # Stop hook confirmed denial directly.
                    self._needs_input_event.clear()
                    self._denied_event.set()
                    return

                else:  # "waiting" — PostToolUse or UserPromptSubmit cleared it
                    _needs_input_since = None
                    self._needs_input_event.clear()

            except Exception:
                pass
            time.sleep(_POLL_INTERVAL)

    # ---- Curses lifecycle ----

    def _curses_main(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            self._setup_colors()

        self.init(stdscr)

        self._paused = False
        self._auto_paused = False  # True while paused due to bridge signal
        prev = time.monotonic()

        while True:
            now = time.monotonic()
            dt = now - prev
            prev = now

            if self._denied_event.is_set():
                break  # tool was denied — close silently

            if self._done_event.is_set():
                self._paused = False
                self._auto_paused = False
                self._show_ready_overlay(stdscr)
                stdscr.nodelay(False)
                stdscr.getch()
                break

            key = stdscr.getch()

            # [P] toggles pause; resuming from auto-pause clears the auto flag
            if key in (ord('p'), ord('P')):
                if self._paused:
                    self._paused = False
                    self._auto_paused = False
                else:
                    self._paused = True
                prev = time.monotonic()

            # Auto-pause when Claude needs attention
            if self._needs_input_event.is_set() and not self._paused:
                self._paused = True
                self._auto_paused = True
                prev = time.monotonic()

            if self._paused:
                if self._auto_paused and self._needs_input_event.is_set():
                    self._show_attention_overlay(stdscr)
                elif self._auto_paused:
                    # needs_input cleared — Claude responded; waiting for user to resume
                    self._show_responded_overlay(stdscr)
                else:
                    self._show_pause_overlay(stdscr)
                time.sleep(1 / _FPS_CAP)
                continue

            keep_going = self.run_frame(stdscr, dt, key)
            if not keep_going:
                break

            stdscr.refresh()
            time.sleep(1 / _FPS_CAP)

        self.teardown(stdscr)
        self._record_score()

    def _setup_colors(self) -> None:
        """Initialize default color pairs. Override to add game-specific pairs."""
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # bird
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # pipes
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # score

    def _show_pause_overlay(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        msg = "  PAUSED — [P] to resume  "
        y = h // 2
        x = max(0, (w - len(msg)) // 2)
        try:
            stdscr.addstr(y, x, msg, curses.A_REVERSE | curses.A_BOLD)
            stdscr.refresh()
        except curses.error:
            pass

    def _show_attention_overlay(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        lines = [
            "  Claude needs your attention!  ",
            "  Switch to Claude to respond.  ",
        ]
        for i, msg in enumerate(lines):
            y = h // 2 - 1 + i
            x = max(0, (w - len(msg)) // 2)
            try:
                stdscr.addstr(y, x, msg, curses.A_REVERSE | curses.A_BOLD)
            except curses.error:
                pass
        try:
            stdscr.refresh()
        except curses.error:
            pass

    def _show_responded_overlay(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        msg = "  Claude responded — [P] to resume  "
        y = h // 2
        x = max(0, (w - len(msg)) // 2)
        try:
            stdscr.addstr(y, x, msg, curses.A_REVERSE | curses.A_BOLD)
            stdscr.refresh()
        except curses.error:
            pass

    def _show_ready_overlay(self, stdscr) -> None:
        h, w = stdscr.getmaxyx()
        msg = "  Claude is ready! Press any key...  "
        y = h // 2
        x = max(0, (w - len(msg)) // 2)
        try:
            stdscr.addstr(y, x, msg, curses.A_REVERSE | curses.A_BOLD)
            stdscr.refresh()
        except curses.error:
            pass

    def _record_score(self) -> None:
        duration = time.monotonic() - self._start_time
        try:
            StateManager().record_session(
                game_name=self._registry_name,
                score=self.get_score(),
                duration_seconds=round(duration, 1),
            )
        except Exception:
            pass

    # ---- Subclass interface ----

    def init(self, stdscr) -> None:
        """Optional: called once after curses is initialized, before the frame loop."""

    @abstractmethod
    def run_frame(self, stdscr, dt: float, key: int) -> bool:
        """
        Draw one frame. Called at ~30 FPS.
        key is the result of stdscr.getch() (-1 if no key pressed).
        Return False to quit the game loop normally.
        """

    def teardown(self, stdscr) -> None:
        """Optional: called after the frame loop ends, before score is saved."""

    def get_score(self) -> int:
        """Return the final score. Override in subclasses that track score."""
        return 0
