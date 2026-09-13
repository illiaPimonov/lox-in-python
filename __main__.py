"""Command-line entry point.

Usage:
    python -m lox-in-python            # start the REPL
    python -m lox-in-python script.lox # run a script file
"""

from __future__ import annotations

import sys
from typing import List, Optional

from .lox import Lox


def main(argv: Optional[List[str]] = None) -> int:
    """Parse ``argv`` and either run a script file or start the REPL.

    Returns the process exit code: 64 for incorrect usage, otherwise
    whatever ``Lox.run_file`` reports (0 success, 65 or 70 on error), or
    0 after an interactive REPL session ends.
    """
    argv = sys.argv[1:] if argv is None else argv

    if len(argv) > 1:
        print("Usage: pylox [script]")
        return 64

    lox = Lox()
    if len(argv) == 1:
        return lox.run_file(argv[0])

    lox.run_prompt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
