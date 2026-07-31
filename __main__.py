from __future__ import annotations

import sys

from .lox import Lox

def main(argv=None) -> int:
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
