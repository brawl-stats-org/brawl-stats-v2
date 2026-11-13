"""Terminal output, pacman style. Colours and progress bars only on a TTY.

:: derive  fr en                          header()
 tokens    578 entries   57.0 KB  0.08s   done()
warning: ...                              warn()
error: ...                                fail()
 csv_logic/cards  [#####-----]  50%       progress(), rewritten in place
"""

import shutil
import sys

TTY = sys.stdout.isatty()


def _colour(code: str) -> str:
    return code if TTY else ""


GREEN = _colour("\033[32m")
RED = _colour("\033[31m")
YELLOW = _colour("\033[33m")
BLUE = _colour("\033[34m")
BOLD = _colour("\033[1m")
ORANGE = _colour("\033[38;5;208m")
OFF = _colour("\033[0m")

BAR_WIDTH = 30

# A progress line is printed without its newline; any other print must end it first.
_progress_open = False


def human_size(size: int) -> str:
    """Bytes as B/KB/MB."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def header(title: str, detail: str = "") -> None:
    """Opens a run. One per command."""
    end_progress()
    tail = f"  {detail}" if detail else ""
    print(f"{BOLD}{BLUE}::{OFF} {BOLD}{title}{OFF}{tail}")


def done(text: str) -> None:
    end_progress()
    print(f" {text}")


def warn(text: str) -> None:
    end_progress()
    print(f"{BOLD}{YELLOW}warning:{OFF} {text}")


def fail(text: str) -> None:
    end_progress()
    print(f"{BOLD}{RED}error:{OFF} {text}")


def progress(text: str, current: int, total: int) -> None:
    """One line rewritten in place with a bar. Silent when not on a TTY.

    The line is cut to the terminal width: `\\r` only returns to the start of the
    last screen row, so a wrapped line could not be rewritten.
    """
    global _progress_open
    if not TTY:
        return
    filled = BAR_WIDTH * current // total
    tail = f" [{'#' * filled}{'-' * (BAR_WIDTH - filled)}] {100 * current // total:>3}%"
    room = max(shutil.get_terminal_size().columns - len(tail) - 2, 0)
    print(f"\r {text[:room]:<{room}}{tail}", end="", flush=True)
    _progress_open = True


def end_progress() -> None:
    """Ends the progress line where it stands; it stays on screen."""
    global _progress_open
    if _progress_open:
        print()
        _progress_open = False
