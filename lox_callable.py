"""Runtime representations of callables, classes and instances.

``LoxCallable`` is the common interface for anything that can be called
with ``(...)``: user-defined functions/lambdas (``LoxFunction``), classes
acting as constructors (``LoxClass``), and native functions (``NativeClock``).
``LoxInstance`` holds the per-object field storage created when a class is
called.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .tokens import Token
from .errors import LoxRuntimeError, ReturnException
from .environment import Environment
from . import ast_nodes as ast

if TYPE_CHECKING:
    from .interpreter import Interpreter

FunctionDeclaration = Union[ast.Function, ast.Lambda]


class LoxCallable(ABC):
    """Interface implemented by anything Lox can invoke with call syntax."""

    @abstractmethod
    def arity(self) -> int:
        """Return the number of arguments this callable expects."""
        ...

    @abstractmethod
    def call(self, interpreter: "Interpreter", arguments: List[Any]) -> Any:
        """Invoke this callable with already-evaluated ``arguments``."""
        ...


class LoxFunction(LoxCallable):
    """A user-defined function, method, or lambda, closing over its defining scope."""

    def __init__(
        self,
        declaration: FunctionDeclaration,
        closure: Environment,
        is_initializer: bool = False,
        name: str = "<lambda>",
    ) -> None:
        """Wrap ``declaration`` so calling it runs its body in a scope nested under ``closure``."""
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer
        self.name = name
        self.is_getter = isinstance(declaration, ast.Function) and declaration.is_getter

    def bind(self, instance: "LoxInstance") -> "LoxFunction":
        """Return a copy of this function with ``this`` bound to ``instance``."""
        environment = Environment(self.closure)
        environment.define("this", instance)
        return LoxFunction(self.declaration, environment, self.is_initializer, self.name)

    def arity(self) -> int:
        """Return the number of declared parameters."""
        return len(self.declaration.params)

    def call(self, interpreter: "Interpreter", arguments: List[Any]) -> Any:
        """Run the function body in a fresh scope with parameters bound to ``arguments``."""
        environment = Environment(self.closure)
        for param, arg in zip(self.declaration.params, arguments):
            environment.define(param.lexeme, arg)

        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnException as ret:
            if self.is_initializer:
                return self.closure.get_at(0, "this")
            return ret.value

        if self.is_initializer:
            return self.closure.get_at(0, "this")
        return None

    def __str__(self) -> str:
        """Return the printable representation, e.g. ``<fn add>``."""
        if self.name == "<lambda>":
            return "<fn lambda>"
        return f"<fn {self.name}>"


class LoxClass(LoxCallable):
    """A class object: constructs instances and resolves instance/static methods."""

    def __init__(
        self,
        name: str,
        superclass: Optional["LoxClass"],
        methods: Dict[str, LoxFunction],
        static_methods: Dict[str, LoxFunction],
    ) -> None:
        """Store the class's name, superclass link, and its own method tables."""
        self.name = name
        self.superclass = superclass
        self.methods = methods
        self.static_methods = static_methods

    def find_method(self, name: str) -> Optional[LoxFunction]:
        """Look up an instance method by name, searching up the superclass chain."""
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def find_static_method(self, name: str) -> Optional[LoxFunction]:
        """Look up a static method by name, searching up the superclass chain."""
        if name in self.static_methods:
            return self.static_methods[name]
        if self.superclass is not None:
            return self.superclass.find_static_method(name)
        return None

    def get(self, name: Token) -> Any:
        """Resolve a property access on the class object itself (i.e. a static method)."""
        method = self.find_static_method(name.lexeme)
        if method is not None:
            return method.bind(self)
        raise LoxRuntimeError(name, f"Undefined static property '{name.lexeme}'.")

    def arity(self) -> int:
        """Return the initializer's arity, or 0 if the class has no ``init`` method."""
        initializer = self.find_method("init")
        if initializer is None:
            return 0
        return initializer.arity()

    def call(self, interpreter: "Interpreter", arguments: List[Any]) -> Any:
        """Construct a new instance, running ``init`` with ``arguments`` if defined."""
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def __str__(self) -> str:
        """Return the class name."""
        return self.name


class LoxInstance:
    """A runtime object created by calling a ``LoxClass``, holding its own fields."""

    def __init__(self, klass: LoxClass) -> None:
        """Create an instance of ``klass`` with an empty field table."""
        self.klass = klass
        self.fields: Dict[str, Any] = {}

    def get(self, name: Token, interpreter: Optional["Interpreter"] = None) -> Any:
        """Resolve a property access: an own field, a bound method, or a getter's value.

        ``interpreter`` is required when the resolved member is a getter,
        since evaluating its body needs the interpreter's evaluation logic.
        """
        if name.lexeme in self.fields:
            return self.fields[name.lexeme]

        method = self.klass.find_method(name.lexeme)
        if method is not None:
            bound = method.bind(self)
            if bound.is_getter:
                return bound.call(interpreter, [])
            return bound

        raise LoxRuntimeError(name, f"Undefined property '{name.lexeme}'.")

    def set(self, name: Token, value: Any) -> None:
        """Assign ``value`` to the instance field ``name`` (creating it if new)."""
        self.fields[name.lexeme] = value

    def __str__(self) -> str:
        """Return a printable representation, e.g. ``Circle instance``."""
        return f"{self.klass.name} instance"


# ------------------------------------------------------------------ native --
class NativeClock(LoxCallable):
    """The built-in ``clock()`` function: returns the current time in seconds."""

    def arity(self) -> int:
        """``clock`` takes no arguments."""
        return 0

    def call(self, interpreter: "Interpreter", arguments: List[Any]) -> Any:
        """Return the current Unix time as a float."""
        return time.time()

    def __str__(self) -> str:
        """Return the printable representation."""
        return "<native fn clock>"
