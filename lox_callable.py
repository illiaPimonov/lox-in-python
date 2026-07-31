from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .tokens import Token
from .errors import LoxRuntimeError, ReturnException
from .environment import Environment
from . import ast_nodes as ast

class LoxCallable(ABC):
    @abstractmethod
    def arity(self) -> int: ...

    @abstractmethod
    def call(self, interpreter, arguments: List[Any]) -> Any: ...

class LoxFunction(LoxCallable):
    def __init__(
        self,
        declaration,
        closure: Environment,
        is_initializer: bool = False,
        name: str = "<lambda>",
    ):
        self.declaration = declaration
        self.closure = closure
        self.is_initializer = is_initializer
        self.name = name
        self.is_getter = isinstance(declaration, ast.Function) and declaration.is_getter

    def bind(self, instance: "LoxInstance") -> "LoxFunction":
        environment = Environment(self.closure)
        environment.define("this", instance)
        return LoxFunction(self.declaration, environment, self.is_initializer, self.name)

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter, arguments: List[Any]) -> Any:
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
        if self.name == "<lambda>":
            return "<fn lambda>"
        return f"<fn {self.name}>"

class LoxClass(LoxCallable):
    def __init__(
        self,
        name: str,
        superclass: Optional["LoxClass"],
        methods: Dict[str, LoxFunction],
        static_methods: Dict[str, LoxFunction],
    ):
        self.name = name
        self.superclass = superclass
        self.methods = methods
        self.static_methods = static_methods

    def find_method(self, name: str) -> Optional[LoxFunction]:
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def find_static_method(self, name: str) -> Optional[LoxFunction]:
        if name in self.static_methods:
            return self.static_methods[name]
        if self.superclass is not None:
            return self.superclass.find_static_method(name)
        return None

    def get(self, name: Token) -> Any:
        method = self.find_static_method(name.lexeme)
        if method is not None:
            return method.bind(self)
        raise LoxRuntimeError(name, f"Undefined static property '{name.lexeme}'.")

    def arity(self) -> int:
        initializer = self.find_method("init")
        if initializer is None:
            return 0
        return initializer.arity()

    def call(self, interpreter, arguments: List[Any]) -> Any:
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def __str__(self) -> str:
        return self.name

class LoxInstance:
    def __init__(self, klass: LoxClass):
        self.klass = klass
        self.fields: Dict[str, Any] = {}

    def get(self, name: Token, interpreter=None) -> Any:
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
        self.fields[name.lexeme] = value

    def __str__(self) -> str:
        return f"{self.klass.name} instance"

class NativeClock(LoxCallable):
    def arity(self) -> int:
        return 0

    def call(self, interpreter, arguments: List[Any]) -> Any:
        return time.time()

    def __str__(self) -> str:
        return "<native fn clock>"
