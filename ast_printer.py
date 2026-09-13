"""Debugging visitors that render an expression AST back to text.

Neither visitor is used by the interpreter itself; they exist as small,
self-contained examples of implementing a new operation over the AST via
the same ``accept``/``visit_*`` dispatch mechanism used by ``Resolver``
and ``Interpreter``, and are handy when inspecting what the parser built.
"""

from __future__ import annotations

from . import ast_nodes as ast


class AstPrinter:
    """Renders an expression as a fully parenthesized prefix string.

    For example, ``1 + 2 * 3`` prints as ``(+ 1 (* 2 3))``.
    """

    def print(self, expr: ast.Expr) -> str:
        """Render ``expr`` to its parenthesized string form."""
        return expr.accept(self)

    def _parenthesize(self, name: str, *exprs: ast.Expr) -> str:
        """Join ``name`` and the rendered ``exprs`` inside a single pair of parens."""
        parts = [name] + [e.accept(self) for e in exprs]
        return "(" + " ".join(parts) + ")"

    def visit_Binary(self, expr: ast.Binary) -> str:
        """Render a binary expression as ``(operator left right)``."""
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_Grouping(self, expr: ast.Grouping) -> str:
        """Render a grouping as ``(group inner)``."""
        return self._parenthesize("group", expr.expression)

    def visit_Literal(self, expr: ast.Literal) -> str:
        """Render a literal value, or ``nil`` for None."""
        if expr.value is None:
            return "nil"
        return str(expr.value)

    def visit_Unary(self, expr: ast.Unary) -> str:
        """Render a unary expression as ``(operator operand)``."""
        return self._parenthesize(expr.operator.lexeme, expr.right)

    def visit_Conditional(self, expr: ast.Conditional) -> str:
        """Render a ternary conditional as ``(?: condition then else)``."""
        return self._parenthesize("?:", expr.condition, expr.then_branch, expr.else_branch)

    def visit_Comma(self, expr: ast.Comma) -> str:
        """Render a comma expression as ``(, left right)``."""
        return self._parenthesize(",", expr.left, expr.right)

    def visit_Variable(self, expr: ast.Variable) -> str:
        """Render a variable reference as its bare name."""
        return expr.name.lexeme

    def visit_Assign(self, expr: ast.Assign) -> str:
        """Render an assignment as ``(= name value)``."""
        return self._parenthesize("=", ast.Literal(expr.name.lexeme), expr.value)

    def visit_Logical(self, expr: ast.Logical) -> str:
        """Render an ``and``/``or`` expression as ``(operator left right)``."""
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_Call(self, expr: ast.Call) -> str:
        """Render a call as ``(call callee arguments...)``."""
        return self._parenthesize("call", expr.callee, *expr.arguments)

    def visit_Get(self, expr: ast.Get) -> str:
        """Render a property read as ``(.name obj)``."""
        return self._parenthesize("." + expr.name.lexeme, expr.obj)

    def visit_Set(self, expr: ast.Set) -> str:
        """Render a property write as ``(=.name obj value)``."""
        return self._parenthesize("=." + expr.name.lexeme, expr.obj, expr.value)

    def visit_This(self, expr: ast.This) -> str:
        """Render ``this``."""
        return "this"

    def visit_Super(self, expr: ast.Super) -> str:
        """Render a ``super.method`` reference."""
        return "(super." + expr.method.lexeme + ")"

    def visit_Lambda(self, expr: ast.Lambda) -> str:
        """Render an anonymous function's parameter list (body omitted for brevity)."""
        return "(fun (" + " ".join(p.lexeme for p in expr.params) + ") ...)"


class RpnPrinter:
    """Renders an expression in Reverse Polish Notation.

    For example, ``(1 + 2) * (4 - 3)`` prints as ``1 2 + 4 3 - *``.
    """

    def print(self, expr: ast.Expr) -> str:
        """Render ``expr`` to its RPN string form."""
        return expr.accept(self)

    def visit_Binary(self, expr: ast.Binary) -> str:
        """Render a binary expression as ``left right operator``."""
        return f"{expr.left.accept(self)} {expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Grouping(self, expr: ast.Grouping) -> str:
        """Groupings carry no notation of their own in RPN; render the inner expression."""
        return expr.expression.accept(self)

    def visit_Literal(self, expr: ast.Literal) -> str:
        """Render a literal value, or ``nil`` for None."""
        if expr.value is None:
            return "nil"
        return str(expr.value)

    def visit_Unary(self, expr: ast.Unary) -> str:
        """Render a unary expression as ``operand operator``."""
        return f"{expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Conditional(self, expr: ast.Conditional) -> str:
        """Render a ternary conditional as ``condition then else ?:``."""
        return (
            f"{expr.condition.accept(self)} {expr.then_branch.accept(self)} "
            f"{expr.else_branch.accept(self)} ?:"
        )

    def visit_Comma(self, expr: ast.Comma) -> str:
        """Render a comma expression as ``left right ,``."""
        return f"{expr.left.accept(self)} {expr.right.accept(self)} ,"

    def visit_Variable(self, expr: ast.Variable) -> str:
        """Render a variable reference as its bare name."""
        return expr.name.lexeme

    def visit_Logical(self, expr: ast.Logical) -> str:
        """Render an ``and``/``or`` expression as ``left right operator``."""
        return f"{expr.left.accept(self)} {expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Assign(self, expr: ast.Assign) -> str:
        """Render an assignment as ``value name =``."""
        return f"{expr.value.accept(self)} {expr.name.lexeme} ="

    def visit_Call(self, expr: ast.Call) -> str:
        """Render a call as ``arguments... callee call``."""
        args = " ".join(a.accept(self) for a in expr.arguments)
        return f"{args} {expr.callee.accept(self)} call".strip()

    def visit_Get(self, expr: ast.Get) -> str:
        """Render a property read as ``obj .name``."""
        return f"{expr.obj.accept(self)} .{expr.name.lexeme}"

    def visit_Set(self, expr: ast.Set) -> str:
        """Render a property write as ``value obj .name=``."""
        return f"{expr.value.accept(self)} {expr.obj.accept(self)} .{expr.name.lexeme}="

    def visit_This(self, expr: ast.This) -> str:
        """Render ``this``."""
        return "this"

    def visit_Super(self, expr: ast.Super) -> str:
        """Render a ``super.method`` reference."""
        return f"super.{expr.method.lexeme}"

    def visit_Lambda(self, expr: ast.Lambda) -> str:
        """Anonymous functions have no compact RPN form; render a placeholder."""
        return "<lambda>"
