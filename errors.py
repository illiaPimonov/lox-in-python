from __future__ import annotations

from typing import Any
from .tokens import Token

class LoxParseError(Exception):
    pass

class LoxRuntimeError(RuntimeError):

    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token
        self.message = message

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class ReturnException(Exception):

    def __init__(self, value: Any):
        super().__init__()
        self.value = value
