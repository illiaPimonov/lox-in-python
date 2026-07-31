from __future__ import annotations

from typing import List, Optional, Callable

from .tokens import Token, TokenType
from . import ast_nodes as ast
from .errors import LoxParseError

TT = TokenType

class Parser:
    def __init__(self, tokens: List[Token], error_reporter):
        self.tokens = tokens
        self.current = 0
        self.error_reporter = error_reporter

    def parse(self) -> List[ast.Stmt]:
        statements: List[ast.Stmt] = []
        while not self._is_at_end():
            decl = self._declaration()
            if decl is not None:
                statements.append(decl)
        return statements

    def parse_single_expression(self) -> Optional[ast.Expr]:
        try:
            expr = self._expression()
            if not self._is_at_end():
                return None
            return expr
        except LoxParseError:
            return None

    def _declaration(self) -> Optional[ast.Stmt]:
        try:
            if self._match(TT.CLASS):
                return self._class_declaration()
            if self._match(TT.FUN):
                return self._function("function")
            if self._match(TT.VAR):
                return self._var_declaration()
            return self._statement()
        except LoxParseError:
            self._synchronize()
            return None

    def _class_declaration(self) -> ast.Stmt:
        name = self._consume(TT.IDENTIFIER, "Expect class name.")

        superclass = None
        if self._match(TT.LESS):
            self._consume(TT.IDENTIFIER, "Expect superclass name.")
            superclass = ast.Variable(self._previous())

        self._consume(TT.LEFT_BRACE, "Expect '{' before class body.")

        methods: List[ast.Function] = []
        static_methods: List[ast.Function] = []
        while not self._check(TT.RIGHT_BRACE) and not self._is_at_end():
            is_static = self._match(TT.CLASS)
            fn = self._function("method")
            if is_static:
                static_methods.append(fn)
            else:
                methods.append(fn)

        self._consume(TT.RIGHT_BRACE, "Expect '}' after class body.")
        return ast.Class(name, superclass, methods, static_methods)

    def _function(self, kind: str) -> ast.Function:
        name = self._consume(TT.IDENTIFIER, f"Expect {kind} name.")

        if kind == "method" and self._check(TT.LEFT_BRACE):
            self._consume(TT.LEFT_BRACE, "Expect '{' before getter body.")
            body = self._block()
            return ast.Function(name, [], body, is_getter=True)

        self._consume(TT.LEFT_PAREN, f"Expect '(' after {kind} name.")
        params = self._parameter_list()
        self._consume(TT.LEFT_BRACE, "Expect '{' before " + kind + " body.")
        body = self._block()
        return ast.Function(name, params, body)

    def _parameter_list(self) -> List[Token]:
        params: List[Token] = []
        if not self._check(TT.RIGHT_PAREN):
            while True:
                if len(params) >= 255:
                    self._error(self._peek(), "Can't have more than 255 parameters.")
                params.append(self._consume(TT.IDENTIFIER, "Expect parameter name."))
                if not self._match(TT.COMMA):
                    break
        self._consume(TT.RIGHT_PAREN, "Expect ')' after parameters.")
        return params

    def _var_declaration(self) -> ast.Stmt:
        name = self._consume(TT.IDENTIFIER, "Expect variable name.")
        initializer = None
        if self._match(TT.EQUAL):
            initializer = self._expression()
        self._consume(TT.SEMICOLON, "Expect ';' after variable declaration.")
        return ast.Var(name, initializer)

    def _statement(self) -> ast.Stmt:
        if self._match(TT.FOR):
            return self._for_statement()
        if self._match(TT.IF):
            return self._if_statement()
        if self._match(TT.PRINT):
            return self._print_statement()
        if self._match(TT.RETURN):
            return self._return_statement()
        if self._match(TT.WHILE):
            return self._while_statement()
        if self._match(TT.BREAK):
            return self._break_statement()
        if self._match(TT.CONTINUE):
            return self._continue_statement()
        if self._match(TT.LEFT_BRACE):
            return ast.Block(self._block())
        return self._expression_statement()

    def _for_statement(self) -> ast.Stmt:
        self._consume(TT.LEFT_PAREN, "Expect '(' after 'for'.")

        initializer: Optional[ast.Stmt]
        if self._match(TT.SEMICOLON):
            initializer = None
        elif self._match(TT.VAR):
            initializer = self._var_declaration()
        else:
            initializer = self._expression_statement()

        condition = None
        if not self._check(TT.SEMICOLON):
            condition = self._expression()
        self._consume(TT.SEMICOLON, "Expect ';' after loop condition.")

        increment = None
        if not self._check(TT.RIGHT_PAREN):
            increment = self._expression()
        self._consume(TT.RIGHT_PAREN, "Expect ')' after for clauses.")

        body = self._statement()

        return ast.For(initializer, condition, increment, body)

    def _if_statement(self) -> ast.Stmt:
        self._consume(TT.LEFT_PAREN, "Expect '(' after 'if'.")
        condition = self._expression()
        self._consume(TT.RIGHT_PAREN, "Expect ')' after if condition.")

        then_branch = self._statement()
        else_branch = None
        if self._match(TT.ELSE):
            else_branch = self._statement()

        return ast.If(condition, then_branch, else_branch)

    def _print_statement(self) -> ast.Stmt:
        value = self._expression()
        self._consume(TT.SEMICOLON, "Expect ';' after value.")
        return ast.Print(value)

    def _return_statement(self) -> ast.Stmt:
        keyword = self._previous()
        value = None
        if not self._check(TT.SEMICOLON):
            value = self._expression()
        self._consume(TT.SEMICOLON, "Expect ';' after return value.")
        return ast.Return(keyword, value)

    def _while_statement(self) -> ast.Stmt:
        self._consume(TT.LEFT_PAREN, "Expect '(' after 'while'.")
        condition = self._expression()
        self._consume(TT.RIGHT_PAREN, "Expect ')' after condition.")
        body = self._statement()
        return ast.While(condition, body)

    def _break_statement(self) -> ast.Stmt:
        keyword = self._previous()
        self._consume(TT.SEMICOLON, "Expect ';' after 'break'.")
        return ast.Break(keyword)

    def _continue_statement(self) -> ast.Stmt:
        keyword = self._previous()
        self._consume(TT.SEMICOLON, "Expect ';' after 'continue'.")
        return ast.Continue(keyword)

    def _block(self) -> List[ast.Stmt]:
        statements: List[ast.Stmt] = []
        while not self._check(TT.RIGHT_BRACE) and not self._is_at_end():
            decl = self._declaration()
            if decl is not None:
                statements.append(decl)
        self._consume(TT.RIGHT_BRACE, "Expect '}' after block.")
        return statements

    def _expression_statement(self) -> ast.Stmt:
        expr = self._expression()
        self._consume(TT.SEMICOLON, "Expect ';' after expression.")
        return ast.Expression(expr)

    def _expression(self) -> ast.Expr:
        return self._comma()

    def _comma(self) -> ast.Expr:
        expr = self._assignment()
        while self._match(TT.COMMA):
            right = self._assignment()
            expr = ast.Comma(expr, right)
        return expr

    def _assignment(self) -> ast.Expr:
        expr = self._conditional()

        if self._match(TT.EQUAL):
            equals = self._previous()
            value = self._assignment()

            if isinstance(expr, ast.Variable):
                return ast.Assign(expr.name, value)
            if isinstance(expr, ast.Get):
                return ast.Set(expr.obj, expr.name, value)

            self._error(equals, "Invalid assignment target.")

        return expr

    def _conditional(self) -> ast.Expr:
        expr = self._or()

        if self._match(TT.QUESTION):
            then_branch = self._expression()
            self._consume(TT.COLON, "Expect ':' after then-branch of conditional expression.")
            else_branch = self._conditional()
            expr = ast.Conditional(expr, then_branch, else_branch)

        return expr

    def _or(self) -> ast.Expr:
        expr = self._and()
        while self._match(TT.OR):
            operator = self._previous()
            right = self._and()
            expr = ast.Logical(expr, operator, right)
        return expr

    def _and(self) -> ast.Expr:
        expr = self._equality()
        while self._match(TT.AND):
            operator = self._previous()
            right = self._equality()
            expr = ast.Logical(expr, operator, right)
        return expr

    def _binary_level(self, operators, next_rule: Callable[[], ast.Expr]) -> ast.Expr:
        if self._check_any(operators):
            operator = self._peek()
            self._error(operator, f"Expect expression before '{operator.lexeme}'.")
            self._advance()
            next_rule()
            return ast.Literal(None)

        expr = next_rule()
        while self._match(*operators):
            operator = self._previous()
            right = next_rule()
            expr = ast.Binary(expr, operator, right)
        return expr

    def _equality(self) -> ast.Expr:
        return self._binary_level((TT.BANG_EQUAL, TT.EQUAL_EQUAL), self._comparison)

    def _comparison(self) -> ast.Expr:
        return self._binary_level(
            (TT.GREATER, TT.GREATER_EQUAL, TT.LESS, TT.LESS_EQUAL), self._term
        )

    def _term(self) -> ast.Expr:
        if self._check(TT.PLUS):
            operator = self._peek()
            self._error(operator, f"Expect expression before '{operator.lexeme}'.")
            self._advance()
            self._factor()
            return ast.Literal(None)

        expr = self._factor()
        while self._match(TT.MINUS, TT.PLUS):
            operator = self._previous()
            right = self._factor()
            expr = ast.Binary(expr, operator, right)
        return expr

    def _factor(self) -> ast.Expr:
        return self._binary_level((TT.SLASH, TT.STAR, TT.PERCENT), self._unary)

    def _unary(self) -> ast.Expr:
        if self._match(TT.BANG, TT.MINUS):
            operator = self._previous()
            right = self._unary()
            return ast.Unary(operator, right)
        return self._call()

    def _call(self) -> ast.Expr:
        expr = self._primary()

        while True:
            if self._match(TT.LEFT_PAREN):
                expr = self._finish_call(expr)
            elif self._match(TT.DOT):
                name = self._consume(TT.IDENTIFIER, "Expect property name after '.'.")
                expr = ast.Get(expr, name)
            else:
                break

        return expr

    def _finish_call(self, callee: ast.Expr) -> ast.Expr:
        arguments: List[ast.Expr] = []
        if not self._check(TT.RIGHT_PAREN):
            while True:
                if len(arguments) >= 255:
                    self._error(self._peek(), "Can't have more than 255 arguments.")
                arguments.append(self._assignment())
                if not self._match(TT.COMMA):
                    break

        paren = self._consume(TT.RIGHT_PAREN, "Expect ')' after arguments.")
        return ast.Call(callee, paren, arguments)

    def _primary(self) -> ast.Expr:
        if self._match(TT.FALSE):
            return ast.Literal(False)
        if self._match(TT.TRUE):
            return ast.Literal(True)
        if self._match(TT.NIL):
            return ast.Literal(None)

        if self._match(TT.NUMBER, TT.STRING):
            return ast.Literal(self._previous().literal)

        if self._match(TT.SUPER):
            keyword = self._previous()
            self._consume(TT.DOT, "Expect '.' after 'super'.")
            method = self._consume(TT.IDENTIFIER, "Expect superclass method name.")
            return ast.Super(keyword, method)

        if self._match(TT.THIS):
            return ast.This(self._previous())

        if self._match(TT.IDENTIFIER):
            return ast.Variable(self._previous())

        if self._match(TT.LEFT_PAREN):
            expr = self._expression()
            self._consume(TT.RIGHT_PAREN, "Expect ')' after expression.")
            return ast.Grouping(expr)

        if self._match(TT.FUN):
            return self._lambda_body()

        raise self._error(self._peek(), "Expect expression.")

    def _lambda_body(self) -> ast.Expr:
        self._consume(TT.LEFT_PAREN, "Expect '(' after 'fun'.")
        params = self._parameter_list()
        self._consume(TT.LEFT_BRACE, "Expect '{' before lambda body.")
        body = self._block()
        return ast.Lambda(params, body)

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _check_any(self, types) -> bool:
        return any(self._check(t) for t in types)

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TT.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _error(self, token: Token, message: str) -> LoxParseError:
        self.error_reporter(token, message)
        return LoxParseError(message)

    def _synchronize(self) -> None:
        self._advance()
        while not self._is_at_end():
            if self._previous().type == TT.SEMICOLON:
                return
            if self._peek().type in (
                TT.CLASS, TT.FUN, TT.VAR, TT.FOR, TT.IF, TT.WHILE, TT.PRINT, TT.RETURN,
            ):
                return
            self._advance()
