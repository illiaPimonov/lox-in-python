"""Abstract syntax tree node definitions for expressions and statements.

Every node is a small ``dataclass`` deriving from either ``Expr`` or
``Stmt``. Both base classes implement the visitor pattern through a
single generic ``accept`` method: it looks up ``visit_<ClassName>`` on
whatever visitor object is passed in (an ``Interpreter``, ``Resolver``,
``AstPrinter``, ...) and calls it. This avoids hand-writing a separate
visitor interface for every consumer of the tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .tokens import Token


def _visit(node: "Expr | Stmt", visitor: Any) -> Any:
    """Dispatch ``node`` to ``visitor.visit_<NodeClassName>(node)``."""
    method_name = "visit_" + type(node).__name__
    method = getattr(visitor, method_name)
    return method(node)


# ---------------------------------------------------------------- Expr ----
class Expr:
    """Base class for every expression node in the AST."""

    def accept(self, visitor: Any) -> Any:
        """Dispatch this node to the matching ``visit_*`` method on ``visitor``."""
        return _visit(self, visitor)


@dataclass
class Assign(Expr):
    """A variable assignment: ``name = value``."""

    name: Token
    value: Expr


@dataclass
class Binary(Expr):
    """A binary operator expression: ``left operator right``."""

    left: Expr
    operator: Token
    right: Expr


@dataclass
class Call(Expr):
    """A function/method call: ``callee(arguments...)``."""

    callee: Expr
    paren: Token
    arguments: List[Expr]


@dataclass
class Get(Expr):
    """A property read: ``obj.name``."""

    obj: Expr
    name: Token


@dataclass
class Grouping(Expr):
    """A parenthesized expression: ``(expression)``."""

    expression: Expr


@dataclass
class Literal(Expr):
    """A literal value: number, string, boolean or nil."""

    value: Any


@dataclass
class Logical(Expr):
    """A short-circuiting ``and``/``or`` expression."""

    left: Expr
    operator: Token
    right: Expr


@dataclass
class Set(Expr):
    """A property write: ``obj.name = value``."""

    obj: Expr
    name: Token
    value: Expr


@dataclass
class Super(Expr):
    """A superclass method reference: ``super.method``."""

    keyword: Token
    method: Token


@dataclass
class This(Expr):
    """A reference to the current instance inside a method: ``this``."""

    keyword: Token


@dataclass
class Unary(Expr):
    """A unary operator expression: ``operator right`` (``!`` or ``-``)."""

    operator: Token
    right: Expr


@dataclass
class Variable(Expr):
    """A variable reference by name."""

    name: Token


@dataclass
class Conditional(Expr):
    """A ternary conditional expression: ``condition ? then : else``."""

    condition: Expr
    then_branch: Expr
    else_branch: Expr


@dataclass
class Comma(Expr):
    """A C-style comma expression: evaluates ``left`` then ``right``, keeping ``right``."""

    left: Expr
    right: Expr


@dataclass
class Lambda(Expr):
    """An anonymous function expression: ``fun (params) { body }``."""

    params: List[Token]
    body: List["Stmt"]


# ---------------------------------------------------------------- Stmt ----
class Stmt:
    """Base class for every statement node in the AST."""

    def accept(self, visitor: Any) -> Any:
        """Dispatch this node to the matching ``visit_*`` method on ``visitor``."""
        return _visit(self, visitor)


@dataclass
class Block(Stmt):
    """A ``{ ... }`` block introducing a new lexical scope."""

    statements: List[Stmt]


@dataclass
class Class(Stmt):
    """A class declaration, with optional superclass, instance and static methods."""

    name: Token
    superclass: Optional[Variable]
    methods: List["Function"]
    static_methods: List["Function"] = field(default_factory=list)


@dataclass
class Expression(Stmt):
    """A statement consisting of a bare expression, evaluated for its side effects."""

    expression: Expr


@dataclass
class Function(Stmt):
    """A named function or method declaration."""

    name: Token
    params: List[Token]
    body: List[Stmt]
    is_getter: bool = False
    is_static: bool = False


@dataclass
class If(Stmt):
    """A conditional statement, with an optional ``else`` branch."""

    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class Print(Stmt):
    """A ``print expression;`` statement."""

    expression: Expr


@dataclass
class Return(Stmt):
    """A ``return`` statement, with an optional value."""

    keyword: Token
    value: Optional[Expr]


@dataclass
class Var(Stmt):
    """A variable declaration, with an optional initializer."""

    name: Token
    initializer: Optional[Expr]


@dataclass
class While(Stmt):
    """A ``while`` loop."""

    condition: Expr
    body: Stmt


@dataclass
class For(Stmt):
    """A ``for`` loop, kept as a dedicated node (rather than desugared into
    ``While``) so that the interpreter can run the increment step after a
    ``continue`` as well as after normal completion of the loop body."""

    initializer: Optional[Stmt]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Stmt


@dataclass
class Break(Stmt):
    """A ``break;`` statement, only valid inside a loop."""

    keyword: Token


@dataclass
class Continue(Stmt):
    """A ``continue;`` statement, only valid inside a loop."""

    keyword: Token
