from __future__ import annotations

from enum import Enum, auto
from typing import Dict, List, Optional

from .tokens import Token
from . import ast_nodes as ast

class FunctionType(Enum):
    NONE = auto()
    FUNCTION = auto()
    LAMBDA = auto()
    INITIALIZER = auto()
    METHOD = auto()
    GETTER = auto()

class ClassType(Enum):
    NONE = auto()
    CLASS = auto()
    SUBCLASS = auto()

class _VarState:
    __slots__ = ("token", "ready", "used")

    def __init__(self, token: Token):
        self.token = token
        self.ready = False
        self.used = False

class Resolver:
    def __init__(self, interpreter, error_reporter, warn_reporter=None):
        self.interpreter = interpreter
        self.error_reporter = error_reporter
        self.warn_reporter = warn_reporter or (lambda token, message: None)
        self.scopes: List[Dict[str, _VarState]] = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE
        self.loop_depth = 0

    def resolve(self, statements: List[ast.Stmt]) -> None:
        for stmt in statements:
            self._resolve_stmt(stmt)

    def _resolve_stmt(self, stmt: ast.Stmt) -> None:
        stmt.accept(self)

    def _resolve_expr(self, expr: ast.Expr) -> None:
        expr.accept(self)

    def _begin_scope(self) -> None:
        self.scopes.append({})

    def _end_scope(self) -> None:
        scope = self.scopes.pop()
        for name, state in scope.items():
            if not state.used and not name.startswith("_"):
                self.warn_reporter(
                    state.token, f"Local variable '{name}' is never used."
                )

    def _declare(self, name: Token) -> None:
        if not self.scopes:
            return
        scope = self.scopes[-1]
        if name.lexeme in scope:
            self.error_reporter(name, "Already a variable with this name in this scope.")
        scope[name.lexeme] = _VarState(name)

    def _define(self, name: Token) -> None:
        if not self.scopes:
            return
        self.scopes[-1][name.lexeme].ready = True

    def _resolve_local(self, expr: ast.Expr, name: Token) -> None:
        for i in range(len(self.scopes) - 1, -1, -1):
            if name.lexeme in self.scopes[i]:
                self.scopes[i][name.lexeme].used = True
                self.interpreter.resolve(expr, len(self.scopes) - 1 - i)
                return

    def _resolve_function(self, function: "ast.Function | ast.Lambda", ftype: FunctionType) -> None:
        enclosing_function = self.current_function
        self.current_function = ftype

        self._begin_scope()
        for param in function.params:
            self._declare(param)
            self._define(param)
        self.resolve(function.body)
        self._end_scope()

        self.current_function = enclosing_function

    def visit_Block(self, stmt: ast.Block) -> None:
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()

    def visit_Class(self, stmt: ast.Class) -> None:
        enclosing_class = self.current_class
        self.current_class = ClassType.CLASS

        self._declare(stmt.name)
        self._define(stmt.name)

        if stmt.superclass is not None:
            if stmt.name.lexeme == stmt.superclass.name.lexeme:
                self.error_reporter(stmt.superclass.name, "A class can't inherit from itself.")
            self.current_class = ClassType.SUBCLASS
            self._resolve_expr(stmt.superclass)

            self._begin_scope()
            self.scopes[-1]["super"] = _VarState(stmt.superclass.name)
            self.scopes[-1]["super"].ready = True
            self.scopes[-1]["super"].used = True

        self._begin_scope()
        self.scopes[-1]["this"] = _VarState(stmt.name)
        self.scopes[-1]["this"].ready = True
        self.scopes[-1]["this"].used = True

        for method in stmt.methods:
            if method.is_getter:
                declaration = FunctionType.GETTER
            elif method.name.lexeme == "init":
                declaration = FunctionType.INITIALIZER
            else:
                declaration = FunctionType.METHOD
            self._resolve_function(method, declaration)

        for method in stmt.static_methods:
            self._resolve_function(method, FunctionType.METHOD)

        self._end_scope()
        if stmt.superclass is not None:
            self._end_scope()

        self.current_class = enclosing_class

    def visit_Expression(self, stmt: ast.Expression) -> None:
        self._resolve_expr(stmt.expression)

    def visit_Function(self, stmt: ast.Function) -> None:
        self._declare(stmt.name)
        self._define(stmt.name)
        self._resolve_function(stmt, FunctionType.FUNCTION)

    def visit_If(self, stmt: ast.If) -> None:
        self._resolve_expr(stmt.condition)
        self._resolve_stmt(stmt.then_branch)
        if stmt.else_branch is not None:
            self._resolve_stmt(stmt.else_branch)

    def visit_Print(self, stmt: ast.Print) -> None:
        self._resolve_expr(stmt.expression)

    def visit_Return(self, stmt: ast.Return) -> None:
        if self.current_function == FunctionType.NONE:
            self.error_reporter(stmt.keyword, "Can't return from top-level code.")
        if stmt.value is not None:
            if self.current_function == FunctionType.INITIALIZER:
                self.error_reporter(stmt.keyword, "Can't return a value from an initializer.")
            self._resolve_expr(stmt.value)

    def visit_Var(self, stmt: ast.Var) -> None:
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self._resolve_expr(stmt.initializer)
        self._define(stmt.name)

    def visit_While(self, stmt: ast.While) -> None:
        self._resolve_expr(stmt.condition)
        self.loop_depth += 1
        self._resolve_stmt(stmt.body)
        self.loop_depth -= 1

    def visit_For(self, stmt: ast.For) -> None:
        self._begin_scope()
        if stmt.initializer is not None:
            self._resolve_stmt(stmt.initializer)
        if stmt.condition is not None:
            self._resolve_expr(stmt.condition)
        if stmt.increment is not None:
            self._resolve_expr(stmt.increment)
        self.loop_depth += 1
        self._resolve_stmt(stmt.body)
        self.loop_depth -= 1
        self._end_scope()

    def visit_Break(self, stmt: ast.Break) -> None:
        if self.loop_depth == 0:
            self.error_reporter(stmt.keyword, "Can't use 'break' outside of a loop.")

    def visit_Continue(self, stmt: ast.Continue) -> None:
        if self.loop_depth == 0:
            self.error_reporter(stmt.keyword, "Can't use 'continue' outside of a loop.")

    def visit_Variable(self, expr: ast.Variable) -> None:
        if (
            self.scopes
            and expr.name.lexeme in self.scopes[-1]
            and not self.scopes[-1][expr.name.lexeme].ready
        ):
            self.error_reporter(expr.name, "Can't read local variable in its own initializer.")

        self._resolve_local(expr, expr.name)

    def visit_Assign(self, expr: ast.Assign) -> None:
        self._resolve_expr(expr.value)
        self._resolve_local(expr, expr.name)

    def visit_Binary(self, expr: ast.Binary) -> None:
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Call(self, expr: ast.Call) -> None:
        self._resolve_expr(expr.callee)
        for arg in expr.arguments:
            self._resolve_expr(arg)

    def visit_Get(self, expr: ast.Get) -> None:
        self._resolve_expr(expr.obj)

    def visit_Grouping(self, expr: ast.Grouping) -> None:
        self._resolve_expr(expr.expression)

    def visit_Literal(self, expr: ast.Literal) -> None:
        pass

    def visit_Logical(self, expr: ast.Logical) -> None:
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Set(self, expr: ast.Set) -> None:
        self._resolve_expr(expr.value)
        self._resolve_expr(expr.obj)

    def visit_Super(self, expr: ast.Super) -> None:
        if self.current_class == ClassType.NONE:
            self.error_reporter(expr.keyword, "Can't use 'super' outside of a class.")
        elif self.current_class != ClassType.SUBCLASS:
            self.error_reporter(expr.keyword, "Can't use 'super' in a class with no superclass.")
        self._resolve_local(expr, expr.keyword)

    def visit_This(self, expr: ast.This) -> None:
        if self.current_class == ClassType.NONE:
            self.error_reporter(expr.keyword, "Can't use 'this' outside of a class.")
            return
        self._resolve_local(expr, expr.keyword)

    def visit_Unary(self, expr: ast.Unary) -> None:
        self._resolve_expr(expr.right)

    def visit_Conditional(self, expr: ast.Conditional) -> None:
        self._resolve_expr(expr.condition)
        self._resolve_expr(expr.then_branch)
        self._resolve_expr(expr.else_branch)

    def visit_Comma(self, expr: ast.Comma) -> None:
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Lambda(self, expr: ast.Lambda) -> None:
        self._resolve_function(expr, FunctionType.LAMBDA)
