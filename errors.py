"""Exception types used for error reporting and non-local control flow.

Two different concerns share the exception mechanism here:

* Genuine errors (``LoxParseError``, ``LoxRuntimeError``) that abort the
  current parse/evaluation step and are turned into a diagnostic message.
* Control-flow signals (``BreakException``, ``ContinueException``,
  ``ReturnException``) that are raised and caught internally by the
  interpreter to unwind out of loops/functions; they never reach the user.

This module also defines the callable type aliases used throughout the
project for error/warning reporter callbacks, so every component that
accepts a reporter can be type-checked consistently.
"""

from __future__ import annotations

from typing import Any, Callable
from .tokens import Token


class LoxParseError(Exception):
    """Raised by the parser on a syntax error; caught internally to resynchronize."""


class LoxRuntimeError(RuntimeError):
    """A runtime error tied to the token whose evaluation triggered it."""

    def __init__(self, token: Token, message: str) -> None:
        """Store the offending token and message alongside the exception."""
        super().__init__(message)
        self.token = token
        self.message = message


class BreakException(Exception):
    """Signals a ``break`` statement; caught by the nearest enclosing loop."""


class ContinueException(Exception):
    """Signals a ``continue`` statement; caught by the nearest enclosing loop."""


class ReturnException(Exception):
    """Signals a ``return`` statement; caught by the enclosing function call."""

    def __init__(self, value: Any) -> None:
        """Carry the returned value back up to the function call site."""
        super().__init__()
        self.value = value


# Callback signatures shared by the scanner, parser, resolver and interpreter.
ScanErrorReporter = Callable[[int, str], None]
"""Reporter used by the scanner: called with (line_number, message)."""

TokenErrorReporter = Callable[[Token, str], None]
"""Reporter used by the parser/resolver: called with (offending_token, message)."""

RuntimeErrorReporter = Callable[[LoxRuntimeError], None]
"""Reporter used by the interpreter: called with the raised LoxRuntimeError."""
