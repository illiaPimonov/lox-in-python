from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .tokens import Token, TokenType
from . import ast_nodes as ast
from .environment import Environment, UNINITIALIZED
from .errors import LoxRuntimeError, BreakException, ContinueException, ReturnException
from .lox_callable import LoxCallable, LoxFunction, LoxClass, LoxInstance, NativeClock

TT = TokenType

class Interpreter:
    def __init__(self, runtime_error_reporter):
        self.runtime_error_reporter = runtime_error_reporter
        self.globals = Environment()
        self.environment = self.globals
        self.locals: Dict[int, int] = {}

        self.globals.define("clock", NativeClock())

    def interpret(self, statements: List[ast.Stmt]) -> None:
        try:
            for statement in statements:
                self._execute(statement)
        except LoxRuntimeError as error:
            self.runtime_error_reporter(error)

    def interpret_expression(self, expr: ast.Expr) -> Any:
        try:
            return self._evaluate(expr)
        except LoxRuntimeError as error:
            self.runtime_error_reporter(error)
            return None

    def resolve(self, expr: ast.Expr, depth: int) -> None:
        self.locals[id(expr)] = depth

    def stringify(self, value: Any) -> str:
        return self._stringify(value)

    def _execute(self, stmt: ast.Stmt) -> None:
        stmt.accept(self)

    def execute_block(self, statements: List[ast.Stmt], environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self._execute(statement)
        finally:
            self.environment = previous

    def visit_Block(self, stmt: ast.Block) -> None:
        self.execute_block(stmt.statements, Environment(self.environment))

    def visit_Class(self, stmt: ast.Class) -> None:
        superclass = None
        if stmt.superclass is not None:
            superclass = self._evaluate(stmt.superclass)
            if not isinstance(superclass, LoxClass):
                raise LoxRuntimeError(stmt.superclass.name, "Superclass must be a class.")

        self.environment.define(stmt.name.lexeme, None)

        env_for_methods = self.environment
        if stmt.superclass is not None:
            env_for_methods = Environment(self.environment)
            env_for_methods.define("super", superclass)

        methods: Dict[str, LoxFunction] = {}
        for method in stmt.methods:
            function = LoxFunction(
                method, env_for_methods,
                is_initializer=(method.name.lexeme == "init"),
                name=method.name.lexeme,
            )
            methods[method.name.lexeme] = function

        static_methods: Dict[str, LoxFunction] = {}
        for method in stmt.static_methods:
            function = LoxFunction(method, env_for_methods, name=method.name.lexeme)
            static_methods[method.name.lexeme] = function

        klass = LoxClass(stmt.name.lexeme, superclass, methods, static_methods)
        self.environment.assign(stmt.name, klass)

    def visit_Expression(self, stmt: ast.Expression) -> None:
        self._evaluate(stmt.expression)

    def visit_Function(self, stmt: ast.Function) -> None:
        function = LoxFunction(stmt, self.environment, name=stmt.name.lexeme)
        self.environment.define(stmt.name.lexeme, function)

    def visit_If(self, stmt: ast.If) -> None:
        if self._is_truthy(self._evaluate(stmt.condition)):
            self._execute(stmt.then_branch)
        elif stmt.else_branch is not None:
            self._execute(stmt.else_branch)

    def visit_Print(self, stmt: ast.Print) -> None:
        value = self._evaluate(stmt.expression)
        print(self._stringify(value))

    def visit_Return(self, stmt: ast.Return) -> None:
        value = None
        if stmt.value is not None:
            value = self._evaluate(stmt.value)
        raise ReturnException(value)

    def visit_Var(self, stmt: ast.Var) -> None:
        value = UNINITIALIZED
        if stmt.initializer is not None:
            value = self._evaluate(stmt.initializer)
        self.environment.define(stmt.name.lexeme, value)

    def visit_While(self, stmt: ast.While) -> None:
        while self._is_truthy(self._evaluate(stmt.condition)):
            try:
                self._execute(stmt.body)
            except BreakException:
                break
            except ContinueException:
                continue

    def visit_For(self, stmt: ast.For) -> None:
        environment = Environment(self.environment)
        previous = self.environment
        try:
            self.environment = environment
            if stmt.initializer is not None:
                self._execute(stmt.initializer)

            while stmt.condition is None or self._is_truthy(self._evaluate(stmt.condition)):
                try:
                    self._execute(stmt.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                if stmt.increment is not None:
                    self._evaluate(stmt.increment)
        finally:
            self.environment = previous

    def visit_Break(self, stmt: ast.Break) -> None:
        raise BreakException()

    def visit_Continue(self, stmt: ast.Continue) -> None:
        raise ContinueException()

    def _evaluate(self, expr: ast.Expr) -> Any:
        return expr.accept(self)

    def visit_Literal(self, expr: ast.Literal) -> Any:
        return expr.value

    def visit_Grouping(self, expr: ast.Grouping) -> Any:
        return self._evaluate(expr.expression)

    def visit_Comma(self, expr: ast.Comma) -> Any:
        self._evaluate(expr.left)
        return self._evaluate(expr.right)

    def visit_Conditional(self, expr: ast.Conditional) -> Any:
        if self._is_truthy(self._evaluate(expr.condition)):
            return self._evaluate(expr.then_branch)
        return self._evaluate(expr.else_branch)

    def visit_Logical(self, expr: ast.Logical) -> Any:
        left = self._evaluate(expr.left)
        if expr.operator.type == TT.OR:
            if self._is_truthy(left):
                return left
        else:
            if not self._is_truthy(left):
                return left
        return self._evaluate(expr.right)

    def visit_Unary(self, expr: ast.Unary) -> Any:
        right = self._evaluate(expr.right)
        if expr.operator.type == TT.MINUS:
            self._check_number_operand(expr.operator, right)
            return -right
        if expr.operator.type == TT.BANG:
            return not self._is_truthy(right)
        return None

    def visit_Binary(self, expr: ast.Binary) -> Any:
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)
        op = expr.operator.type

        if op == TT.PLUS:
            return self._evaluate_plus(expr.operator, left, right)
        if op == TT.MINUS:
            self._check_number_operands(expr.operator, left, right)
            return left - right
        if op == TT.STAR:
            self._check_number_operands(expr.operator, left, right)
            return left * right
        if op == TT.SLASH:
            self._check_number_operands(expr.operator, left, right)
            if right == 0:
                raise LoxRuntimeError(expr.operator, "Division by zero.")
            return left / right
        if op == TT.PERCENT:
            self._check_number_operands(expr.operator, left, right)
            if right == 0:
                raise LoxRuntimeError(expr.operator, "Modulo by zero.")
            return math.fmod(left, right)
        if op == TT.GREATER:
            self._check_number_operands(expr.operator, left, right)
            return left > right
        if op == TT.GREATER_EQUAL:
            self._check_number_operands(expr.operator, left, right)
            return left >= right
        if op == TT.LESS:
            self._check_number_operands(expr.operator, left, right)
            return left < right
        if op == TT.LESS_EQUAL:
            self._check_number_operands(expr.operator, left, right)
            return left <= right
        if op == TT.BANG_EQUAL:
            return not self._is_equal(left, right)
        if op == TT.EQUAL_EQUAL:
            return self._is_equal(left, right)

        return None

    def _evaluate_plus(self, operator: Token, left: Any, right: Any) -> Any:
        if isinstance(left, float) and isinstance(right, float):
            return left + right
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, str) or isinstance(right, str):
            return self._stringify(left) + self._stringify(right)
        raise LoxRuntimeError(operator, "Operands must be two numbers or two strings.")

    def visit_Variable(self, expr: ast.Variable) -> Any:
        return self._look_up_variable(expr.name, expr)

    def visit_Assign(self, expr: ast.Assign) -> Any:
        value = self._evaluate(expr.value)
        distance = self.locals.get(id(expr))
        if distance is not None:
            self.environment.assign_at(distance, expr.name, value)
        else:
            self.globals.assign(expr.name, value)
        return value

    def visit_Call(self, expr: ast.Call) -> Any:
        callee = self._evaluate(expr.callee)
        arguments = [self._evaluate(arg) for arg in expr.arguments]

        if not isinstance(callee, LoxCallable):
            raise LoxRuntimeError(expr.paren, "Can only call functions and classes.")

        if len(arguments) != callee.arity():
            raise LoxRuntimeError(
                expr.paren,
                f"Expected {callee.arity()} arguments but got {len(arguments)}.",
            )

        return callee.call(self, arguments)

    def visit_Get(self, expr: ast.Get) -> Any:
        obj = self._evaluate(expr.obj)
        if isinstance(obj, LoxInstance):
            return obj.get(expr.name, self)
        if isinstance(obj, LoxClass):
            return obj.get(expr.name)
        raise LoxRuntimeError(expr.name, "Only instances have properties.")

    def visit_Set(self, expr: ast.Set) -> Any:
        obj = self._evaluate(expr.obj)
        if not isinstance(obj, LoxInstance):
            raise LoxRuntimeError(expr.name, "Only instances have fields.")
        value = self._evaluate(expr.value)
        obj.set(expr.name, value)
        return value

    def visit_Super(self, expr: ast.Super) -> Any:
        distance = self.locals[id(expr)]
        superclass: LoxClass = self.environment.get_at(distance, "super")
        obj = self.environment.get_at(distance - 1, "this")

        method = superclass.find_method(expr.method.lexeme)
        if method is None:
            raise LoxRuntimeError(expr.method, f"Undefined property '{expr.method.lexeme}'.")
        return method.bind(obj)

    def visit_This(self, expr: ast.This) -> Any:
        return self._look_up_variable(expr.keyword, expr)

    def visit_Lambda(self, expr: ast.Lambda) -> Any:
        return LoxFunction(expr, self.environment)

    def _look_up_variable(self, name: Token, expr: ast.Expr) -> Any:
        distance = self.locals.get(id(expr))
        if distance is not None:
            value = self.environment.get_at(distance, name.lexeme)
        else:
            value = self.globals.get(name)

        if value is UNINITIALIZED:
            raise LoxRuntimeError(
                name, f"Variable '{name.lexeme}' used before it was initialized."
            )
        return value

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return True

    @staticmethod
    def _is_equal(a: Any, b: Any) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, bool) or isinstance(b, bool):
            return isinstance(a, bool) and isinstance(b, bool) and a == b
        return a == b

    @staticmethod
    def _check_number_operand(operator: Token, operand: Any) -> None:
        if isinstance(operand, float):
            return
        raise LoxRuntimeError(operator, "Operand must be a number.")

    @staticmethod
    def _check_number_operands(operator: Token, left: Any, right: Any) -> None:
        if isinstance(left, float) and isinstance(right, float):
            return
        raise LoxRuntimeError(operator, "Operands must be numbers.")

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            if math.isnan(value):
                return "NaN"
            if math.isinf(value):
                return "Infinity" if value > 0 else "-Infinity"
            if value.is_integer() and abs(value) < 1e16:
                return str(int(value))
            return repr(value)
        return str(value)
