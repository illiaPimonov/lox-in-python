from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .tokens import Token

def _visit(node, visitor):
    method_name = "visit_" + type(node).__name__
    method = getattr(visitor, method_name)
    return method(node)

class Expr:
    def accept(self, visitor):
        return _visit(self, visitor)

@dataclass
class Assign(Expr):
    name: Token
    value: Expr

@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Call(Expr):
    callee: Expr
    paren: Token
    arguments: List[Expr]

@dataclass
class Get(Expr):
    obj: Expr
    name: Token

@dataclass
class Grouping(Expr):
    expression: Expr

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Set(Expr):
    obj: Expr
    name: Token
    value: Expr

@dataclass
class Super(Expr):
    keyword: Token
    method: Token

@dataclass
class This(Expr):
    keyword: Token

@dataclass
class Unary(Expr):
    operator: Token
    right: Expr

@dataclass
class Variable(Expr):
    name: Token

@dataclass
class Conditional(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Expr

@dataclass
class Comma(Expr):
    left: Expr
    right: Expr

@dataclass
class Lambda(Expr):
    params: List[Token]
    body: List["Stmt"]

class Stmt:
    def accept(self, visitor):
        return _visit(self, visitor)

@dataclass
class Block(Stmt):
    statements: List[Stmt]

@dataclass
class Class(Stmt):
    name: Token
    superclass: Optional[Variable]
    methods: List["Function"]
    static_methods: List["Function"] = field(default_factory=list)

@dataclass
class Expression(Stmt):
    expression: Expr

@dataclass
class Function(Stmt):
    name: Token
    params: List[Token]
    body: List[Stmt]
    is_getter: bool = False
    is_static: bool = False

@dataclass
class If(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]

@dataclass
class Print(Stmt):
    expression: Expr

@dataclass
class Return(Stmt):
    keyword: Token
    value: Optional[Expr]

@dataclass
class Var(Stmt):
    name: Token
    initializer: Optional[Expr]

@dataclass
class While(Stmt):
    condition: Expr
    body: Stmt

@dataclass
class For(Stmt):
    initializer: Optional[Stmt]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Stmt

@dataclass
class Break(Stmt):
    keyword: Token

@dataclass
class Continue(Stmt):
    keyword: Token
