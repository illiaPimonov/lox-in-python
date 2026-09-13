"""Variable storage: a chain of lexical scopes mapping names to values.

Each ``Environment`` holds the bindings for one lexical scope (the
global scope, a function call, or a block) and a reference to its
enclosing scope, forming a linked chain that mirrors the program's
nested blocks. Lookups walk outward through ``enclosing`` until a
binding is found or the chain is exhausted.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .tokens import Token
from .errors import LoxRuntimeError


class _Uninitialized:
    """Sentinel type: marks a variable that was declared but never assigned."""

    def __repr__(self) -> str:
        """Return a readable placeholder for debugging output."""
        return "<uninitialized>"


UNINITIALIZED = _Uninitialized()
"""Singleton sentinel stored for `var name;` declarations with no initializer."""


class Environment:
    """One lexical scope's variable bindings, linked to its enclosing scope."""

    def __init__(self, enclosing: Optional["Environment"] = None) -> None:
        """Create a new scope, optionally nested inside ``enclosing``."""
        self.enclosing = enclosing
        self.values: Dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        """Bind ``name`` to ``value`` in this scope (shadowing any outer binding)."""
        self.values[name] = value

    def get(self, name: Token) -> Any:
        """Look up ``name``, searching outward through enclosing scopes.

        Raises ``LoxRuntimeError`` if the variable was declared but never
        initialized, or if it is not defined anywhere in the chain.
        """
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
        """Assign to the nearest existing binding of ``name`` in the scope chain.

        Raises ``LoxRuntimeError`` if ``name`` is not defined anywhere.
        """
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return

        raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    # -- direct access by pre-resolved scope distance (see Resolver) -----
    def ancestor(self, distance: int) -> "Environment":
        """Walk ``distance`` scopes outward and return that ``Environment``."""
        env = self
        for _ in range(distance):
            env = env.enclosing  # type: ignore[assignment]
        return env

    def get_at(self, distance: int, name: str) -> Any:
        """Read ``name`` directly from the scope ``distance`` levels out."""
        value = self.ancestor(distance).values.get(name, UNINITIALIZED)
        return value

    def assign_at(self, distance: int, name: Token, value: Any) -> None:
        """Write ``name`` directly in the scope ``distance`` levels out."""
        self.ancestor(distance).values[name.lexeme] = value
