from __future__ import annotations

from typing import Any, Dict, Optional

from .tokens import Token
from .errors import LoxRuntimeError

class _Uninitialized:
    def __repr__(self):
        return "<uninitialized>"

UNINITIALIZED = _Uninitialized()

class Environment:
    def __init__(self, enclosing: Optional["Environment"] = None):
        self.enclosing = enclosing
        self.values: Dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, name: Token) -> Any:
        if name.lexeme in self.values:
            value = self.values[name.lexeme]
            if value is UNINITIALIZED:
                raise LoxRuntimeError(
                    name, f"Variable '{name.lexeme}' used before it was initialized."
                )
            return value

        if self.enclosing is not None:
            return self.enclosing.get(name)

        raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def assign(self, name: Token, value: Any) -> None:
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def ancestor(self, distance: int) -> "Environment":
        env = self
        for _ in range(distance):
            env = env.enclosing
        return env

    def get_at(self, distance: int, name: str) -> Any:
        value = self.ancestor(distance).values.get(name, UNINITIALIZED)
        return value

    def assign_at(self, distance: int, name: Token, value: Any) -> None:
        self.ancestor(distance).values[name.lexeme] = value
