"""Static resolver: computes variable scope distances before interpretation.

Walking the AST once before evaluation lets the interpreter turn every
variable reference into a fixed "how many scopes out, and under which
name" pair (see ``Interpreter.resolve`` / ``Environment.get_at``),
instead of re-searching the environment chain on every access. This pass
also catches a handful of static errors early: reading a local variable
in its own initializer, ``return`` outside a function, ``this``/``super``
outside a class, and ``break``/``continue`` outside a loop. It further
reports (as a non-fatal warning, not an error) local variables that are
declared but never read.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, List, Optional

from .tokens import Token
from . import ast_nodes as ast
from .errors import TokenErrorReporter

if TYPE_CHECKING:
    from .interpreter import Interpreter


class FunctionType(Enum):
    """What kind of function body is currently being resolved, if any."""

    NONE = auto()
    FUNCTION = auto()
    LAMBDA = auto()
    INITIALIZER = auto()
    METHOD = auto()
    GETTER = auto()


class ClassType(Enum):
    """Whether the resolver is currently inside a class, and if it has a superclass."""

    NONE = auto()
    CLASS = auto()
    SUBCLASS = auto()


class _VarState:
    """Tracks one local variable's declaration token and its ready/used flags."""

    __slots__ = ("token", "ready", "used")

    def __init__(self, token: Token) -> None:
        """Record the declaring token; starts out neither ready nor used."""
        self.token = token
        self.ready = False
        self.used = False


class Resolver:
    """Performs a static pass over the AST to resolve variable scope distances."""

    def __init__(
        self,
        interpreter: "Interpreter",
        error_reporter: TokenErrorReporter,
        warn_reporter: Optional[TokenErrorReporter] = None,
    ) -> None:
        """Prepare to resolve against ``interpreter``, reporting errors/warnings via the callbacks."""
        self.interpreter = interpreter
        self.error_reporter = error_reporter
        self.warn_reporter = warn_reporter or (lambda token, message: None)
        self.scopes: List[Dict[str, _VarState]] = []
        self.current_function = FunctionType.NONE
        self.current_class = ClassType.NONE
        self.loop_depth = 0

    # ------------------------------------------------------------------
    def resolve(self, statements: List[ast.Stmt]) -> None:
        """Resolve a list of statements in the current scope."""
        for stmt in statements:
            self._resolve_stmt(stmt)

    def _resolve_stmt(self, stmt: ast.Stmt) -> None:
        """Dispatch a single statement to its ``visit_*`` handler."""
        stmt.accept(self)

    def _resolve_expr(self, expr: ast.Expr) -> None:
        """Dispatch a single expression to its ``visit_*`` handler."""
        expr.accept(self)

    # -- scopes ----------------------------------------------------------
    def _begin_scope(self) -> None:
        """Push a new, empty lexical scope."""
        self.scopes.append({})

    def _end_scope(self) -> None:
        """Pop the current scope, warning about any variable that was never read."""
        scope = self.scopes.pop()
        for name, state in scope.items():
            if not state.used and not name.startswith("_"):
                self.warn_reporter(
                    state.token, f"Local variable '{name}' is never used."
                )

    def _declare(self, name: Token) -> None:
        """Register ``name`` in the current scope as declared but not yet initialized."""
        if not self.scopes:
            return
        scope = self.scopes[-1]
        if name.lexeme in scope:
            self.error_reporter(name, "Already a variable with this name in this scope.")
        scope[name.lexeme] = _VarState(name)

    def _define(self, name: Token) -> None:
        """Mark ``name`` in the current scope as fully initialized and usable."""
        if not self.scopes:
            return
        self.scopes[-1][name.lexeme].ready = True

    def _resolve_local(self, expr: ast.Expr, name: Token) -> None:
        """Find which enclosing scope defines ``name`` and record the distance for ``expr``."""
        for i in range(len(self.scopes) - 1, -1, -1):
            if name.lexeme in self.scopes[i]:
                self.scopes[i][name.lexeme].used = True
                self.interpreter.resolve(expr, len(self.scopes) - 1 - i)
                return
        # Not found locally: treated as a global at interpretation time.

    def _resolve_function(
        self, function: "ast.Function | ast.Lambda", ftype: FunctionType
    ) -> None:
        """Resolve a function/method/lambda body in its own new scope."""
        enclosing_function = self.current_function
        self.current_function = ftype

        self._begin_scope()
        for param in function.params:
            self._declare(param)
            self._define(param)
        self.resolve(function.body)
        self._end_scope()

        self.current_function = enclosing_function

    # -- statements --------------------------------------------------------
    def visit_Block(self, stmt: ast.Block) -> None:
        """Resolve a block's statements in a fresh nested scope."""
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()

    def visit_Class(self, stmt: ast.Class) -> None:
        """Resolve a class declaration: superclass, then ``this``/``super`` scopes, then methods."""
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

        self._end_scope()  # "this"
        if stmt.superclass is not None:
            self._end_scope()  # "super"

        self.current_class = enclosing_class

    def visit_Expression(self, stmt: ast.Expression) -> None:
        """Resolve the expression inside an expression statement."""
        self._resolve_expr(stmt.expression)

    def visit_Function(self, stmt: ast.Function) -> None:
        """Declare a named function in the enclosing scope, then resolve its body."""
        self._declare(stmt.name)
        self._define(stmt.name)
        self._resolve_function(stmt, FunctionType.FUNCTION)

    def visit_If(self, stmt: ast.If) -> None:
        """Resolve an if statement's condition and both branches."""
        self._resolve_expr(stmt.condition)
        self._resolve_stmt(stmt.then_branch)
        if stmt.else_branch is not None:
            self._resolve_stmt(stmt.else_branch)

    def visit_Print(self, stmt: ast.Print) -> None:
        """Resolve a print statement's expression."""
        self._resolve_expr(stmt.expression)

    def visit_Return(self, stmt: ast.Return) -> None:
        """Resolve a return statement, checking it is valid in the current context."""
        if self.current_function == FunctionType.NONE:
            self.error_reporter(stmt.keyword, "Can't return from top-level code.")
        if stmt.value is not None:
            if self.current_function == FunctionType.INITIALIZER:
                self.error_reporter(stmt.keyword, "Can't return a value from an initializer.")
            self._resolve_expr(stmt.value)

    def visit_Var(self, stmt: ast.Var) -> None:
        """Resolve a variable declaration: initializer first, then mark it ready."""
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self._resolve_expr(stmt.initializer)
        self._define(stmt.name)

    def visit_While(self, stmt: ast.While) -> None:
        """Resolve a while loop's condition and body, tracking loop depth for break/continue."""
        self._resolve_expr(stmt.condition)
        self.loop_depth += 1
        self._resolve_stmt(stmt.body)
        self.loop_depth -= 1

    def visit_For(self, stmt: ast.For) -> None:
        """Resolve a for loop's clauses and body in their own scope, tracking loop depth."""
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
        """Check that ``break`` appears inside a loop."""
        if self.loop_depth == 0:
            self.error_reporter(stmt.keyword, "Can't use 'break' outside of a loop.")

    def visit_Continue(self, stmt: ast.Continue) -> None:
        """Check that ``continue`` appears inside a loop."""
        if self.loop_depth == 0:
            self.error_reporter(stmt.keyword, "Can't use 'continue' outside of a loop.")

    # -- expressions ---------------------------------------------------
    def visit_Variable(self, expr: ast.Variable) -> None:
        """Resolve a variable reference, flagging use in its own initializer."""
        if (
            self.scopes
            and expr.name.lexeme in self.scopes[-1]
            and not self.scopes[-1][expr.name.lexeme].ready
        ):
            self.error_reporter(expr.name, "Can't read local variable in its own initializer.")

        self._resolve_local(expr, expr.name)

    def visit_Assign(self, expr: ast.Assign) -> None:
        """Resolve an assignment's value, then the assignment target itself."""
        self._resolve_expr(expr.value)
        self._resolve_local(expr, expr.name)

    def visit_Binary(self, expr: ast.Binary) -> None:
        """Resolve both operands of a binary expression."""
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Call(self, expr: ast.Call) -> None:
        """Resolve the callee and all argument expressions of a call."""
        self._resolve_expr(expr.callee)
        for arg in expr.arguments:
            self._resolve_expr(arg)

    def visit_Get(self, expr: ast.Get) -> None:
        """Resolve the object expression of a property read."""
        self._resolve_expr(expr.obj)

    def visit_Grouping(self, expr: ast.Grouping) -> None:
        """Resolve the inner expression of a parenthesized group."""
        self._resolve_expr(expr.expression)

    def visit_Literal(self, expr: ast.Literal) -> None:
        """Literals contain no variable references; nothing to resolve."""
        pass

    def visit_Logical(self, expr: ast.Logical) -> None:
        """Resolve both operands of an ``and``/``or`` expression."""
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Set(self, expr: ast.Set) -> None:
        """Resolve the value and object expressions of a property write."""
        self._resolve_expr(expr.value)
        self._resolve_expr(expr.obj)

    def visit_Super(self, expr: ast.Super) -> None:
        """Check ``super`` is used validly and resolve it like any other bound name."""
        if self.current_class == ClassType.NONE:
            self.error_reporter(expr.keyword, "Can't use 'super' outside of a class.")
        elif self.current_class != ClassType.SUBCLASS:
            self.error_reporter(expr.keyword, "Can't use 'super' in a class with no superclass.")
        self._resolve_local(expr, expr.keyword)

    def visit_This(self, expr: ast.This) -> None:
        """Check ``this`` is used inside a class and resolve it like any other bound name."""
        if self.current_class == ClassType.NONE:
            self.error_reporter(expr.keyword, "Can't use 'this' outside of a class.")
            return
        self._resolve_local(expr, expr.keyword)

    def visit_Unary(self, expr: ast.Unary) -> None:
        """Resolve the operand of a unary expression."""
        self._resolve_expr(expr.right)

    def visit_Conditional(self, expr: ast.Conditional) -> None:
        """Resolve all three parts of a ternary conditional expression."""
        self._resolve_expr(expr.condition)
        self._resolve_expr(expr.then_branch)
        self._resolve_expr(expr.else_branch)

    def visit_Comma(self, expr: ast.Comma) -> None:
        """Resolve both operands of a comma expression."""
        self._resolve_expr(expr.left)
        self._resolve_expr(expr.right)

    def visit_Lambda(self, expr: ast.Lambda) -> None:
        """Resolve an anonymous function's body in its own scope."""
        self._resolve_function(expr, FunctionType.LAMBDA)
