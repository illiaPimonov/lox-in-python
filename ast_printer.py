from __future__ import annotations

from . import ast_nodes as ast

class AstPrinter:

    def print(self, expr: ast.Expr) -> str:
        return expr.accept(self)

    def _parenthesize(self, name: str, *exprs: ast.Expr) -> str:
        parts = [name] + [e.accept(self) for e in exprs]
        return "(" + " ".join(parts) + ")"

    def visit_Binary(self, expr: ast.Binary) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_Grouping(self, expr: ast.Grouping) -> str:
        return self._parenthesize("group", expr.expression)

    def visit_Literal(self, expr: ast.Literal) -> str:
        if expr.value is None:
            return "nil"
        return str(expr.value)

    def visit_Unary(self, expr: ast.Unary) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.right)

    def visit_Conditional(self, expr: ast.Conditional) -> str:
        return self._parenthesize("?:", expr.condition, expr.then_branch, expr.else_branch)

    def visit_Comma(self, expr: ast.Comma) -> str:
        return self._parenthesize(",", expr.left, expr.right)

    def visit_Variable(self, expr: ast.Variable) -> str:
        return expr.name.lexeme

    def visit_Assign(self, expr: ast.Assign) -> str:
        return self._parenthesize("=", ast.Literal(expr.name.lexeme), expr.value)

    def visit_Logical(self, expr: ast.Logical) -> str:
        return self._parenthesize(expr.operator.lexeme, expr.left, expr.right)

    def visit_Call(self, expr: ast.Call) -> str:
        return self._parenthesize("call", expr.callee, *expr.arguments)

    def visit_Get(self, expr: ast.Get) -> str:
        return self._parenthesize("." + expr.name.lexeme, expr.obj)

    def visit_Set(self, expr: ast.Set) -> str:
        return self._parenthesize("=." + expr.name.lexeme, expr.obj, expr.value)

    def visit_This(self, expr: ast.This) -> str:
        return "this"

    def visit_Super(self, expr: ast.Super) -> str:
        return "(super." + expr.method.lexeme + ")"

    def visit_Lambda(self, expr: ast.Lambda) -> str:
        return "(fun (" + " ".join(p.lexeme for p in expr.params) + ") ...)"

class RpnPrinter:

    def print(self, expr: ast.Expr) -> str:
        return expr.accept(self)

    def visit_Binary(self, expr: ast.Binary) -> str:
        return f"{expr.left.accept(self)} {expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Grouping(self, expr: ast.Grouping) -> str:
        return expr.expression.accept(self)

    def visit_Literal(self, expr: ast.Literal) -> str:
        if expr.value is None:
            return "nil"
        return str(expr.value)

    def visit_Unary(self, expr: ast.Unary) -> str:
        return f"{expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Conditional(self, expr: ast.Conditional) -> str:
        return (
            f"{expr.condition.accept(self)} {expr.then_branch.accept(self)} "
            f"{expr.else_branch.accept(self)} ?:"
        )

    def visit_Comma(self, expr: ast.Comma) -> str:
        return f"{expr.left.accept(self)} {expr.right.accept(self)} ,"

    def visit_Variable(self, expr: ast.Variable) -> str:
        return expr.name.lexeme

    def visit_Logical(self, expr: ast.Logical) -> str:
        return f"{expr.left.accept(self)} {expr.right.accept(self)} {expr.operator.lexeme}"

    def visit_Assign(self, expr: ast.Assign) -> str:
        return f"{expr.value.accept(self)} {expr.name.lexeme} ="

    def visit_Call(self, expr: ast.Call) -> str:
        args = " ".join(a.accept(self) for a in expr.arguments)
        return f"{args} {expr.callee.accept(self)} call".strip()

    def visit_Get(self, expr: ast.Get) -> str:
        return f"{expr.obj.accept(self)} .{expr.name.lexeme}"

    def visit_Set(self, expr: ast.Set) -> str:
        return f"{expr.value.accept(self)} {expr.obj.accept(self)} .{expr.name.lexeme}="

    def visit_This(self, expr: ast.This) -> str:
        return "this"

    def visit_Super(self, expr: ast.Super) -> str:
        return f"super.{expr.method.lexeme}"

    def visit_Lambda(self, expr: ast.Lambda) -> str:
        return "<lambda>"
