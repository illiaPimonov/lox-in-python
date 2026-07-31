from __future__ import annotations

import sys
from typing import List

from .tokens import Token, TokenType
from .scanner import Scanner
from .parser import Parser
from .resolver import Resolver
from .interpreter import Interpreter
from .errors import LoxRuntimeError
from . import ast_nodes as ast

TT = TokenType

class Lox:
    def __init__(self):
        self.had_error = False
        self.had_runtime_error = False
        self.interpreter = Interpreter(self._runtime_error)

    def run_file(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        self._run(source)

        if self.had_error:
            return 65
        if self.had_runtime_error:
            return 70
        return 0

    def run_prompt(self) -> None:
        print("pylox - a Python port of jlox (Crafting Interpreters, Part I)")
        print("Type Lox statements or a bare expression. Ctrl-D / Ctrl-C to exit.")
        while True:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if line.strip() == "":
                continue
            self._run_repl_line(line)
            self.had_error = False

    def _run(self, source: str) -> None:
        tokens = self._scan(source)
        if self.had_error:
            return

        statements = Parser(tokens, self._parse_error).parse()
        if self.had_error:
            return

        resolver = Resolver(self.interpreter, self._resolve_error, self._resolve_warning)
        resolver.resolve(statements)
        if self.had_error:
            return

        self.interpreter.interpret(statements)

    def _run_repl_line(self, source: str) -> None:
        tokens = self._scan(source)
        if self.had_error:
            return

        expr = Parser(list(tokens), self._swallow_error).parse_single_expression()
        if expr is not None:
            resolver = Resolver(self.interpreter, self._resolve_error, self._resolve_warning)
            resolver.resolve([ast.Expression(expr)])
            if self.had_error:
                return
            value = self.interpreter.interpret_expression(expr)
            if not self.had_runtime_error:
                print(self.interpreter.stringify(value))
            self.had_runtime_error = False
            return

        statements = Parser(tokens, self._parse_error).parse()
        if self.had_error:
            return
        resolver = Resolver(self.interpreter, self._resolve_error, self._resolve_warning)
        resolver.resolve(statements)
        if self.had_error:
            return
        self.interpreter.interpret(statements)
        self.had_runtime_error = False

    def _scan(self, source: str) -> List[Token]:
        return Scanner(source, self._scan_error).scan_tokens()

    def _scan_error(self, line: int, message: str) -> None:
        self._report(line, "", message)

    def _swallow_error(self, token: Token, message: str) -> None:
        pass

    def _parse_error(self, token: Token, message: str) -> None:
        if token.type == TT.EOF:
            self._report(token.line, " at end", message)
        else:
            self._report(token.line, f" at '{token.lexeme}'", message)

    def _resolve_error(self, token: Token, message: str) -> None:
        self._report(token.line, f" at '{token.lexeme}'", message)

    def _resolve_warning(self, token: Token, message: str) -> None:
        where = f" at '{token.lexeme}'"
        print(f"[line {token.line}] Warning{where}: {message}", file=sys.stderr)

    def _report(self, line: int, where: str, message: str) -> None:
        print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
        self.had_error = True

    def _runtime_error(self, error: LoxRuntimeError) -> None:
        print(f"{error.message}\n[line {error.token.line}]", file=sys.stderr)
        self.had_runtime_error = True
