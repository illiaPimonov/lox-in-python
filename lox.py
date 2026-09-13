"""Top-level driver: wires the scanner, parser, resolver and interpreter
together, and turns their error callbacks into console diagnostics.

``Lox`` owns the one long-lived ``Interpreter`` instance (so global state
and native functions persist across REPL lines) and exposes two entry
points: ``run_file`` for running a script to completion, and
``run_prompt`` for an interactive REPL that also accepts bare
expressions and prints their value.
"""

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
    """Runs Lox source through scan -> parse -> resolve -> interpret, reporting errors."""

    def __init__(self) -> None:
        """Create a fresh interpreter and clear error-tracking flags."""
        self.had_error = False
        self.had_runtime_error = False
        self.interpreter = Interpreter(self._runtime_error)

    # ------------------------------------------------------------------
    def run_file(self, path: str) -> int:
        """Run the script at ``path`` to completion; return a process exit code.

        Returns 0 on success, 65 on a scan/parse/resolve error, 70 on an
        unhandled runtime error - matching the conventional jlox exit codes.
        """
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        self._run(source)

        if self.had_error:
            return 65
        if self.had_runtime_error:
            return 70
        return 0

    def run_prompt(self) -> None:
        """Run an interactive REPL until EOF/Ctrl-C, accepting statements or bare expressions."""
        print("pylox - a Python port of jlox")
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

    # ------------------------------------------------------------------
    def _run(self, source: str) -> None:
        """Run one full scan/parse/resolve/interpret pass over ``source``."""
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
        """Run one REPL line: try it as a bare expression first, then as statements."""
        tokens = self._scan(source)
        if self.had_error:
            return

        # Try 1: does the whole line parse as a single expression?
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

        # Try 2: parse (and run) as ordinary statements.
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
        """Scan ``source`` into tokens, reporting lexical errors as they occur."""
        return Scanner(source, self._scan_error).scan_tokens()

    # -- error reporting --------------------------------------------------
    def _scan_error(self, line: int, message: str) -> None:
        """Report a lexical error at ``line``."""
        self._report(line, "", message)

    def _swallow_error(self, token: Token, message: str) -> None:
        """Discard errors from the speculative bare-expression parse attempt."""
        pass

    def _parse_error(self, token: Token, message: str) -> None:
        """Report a syntax error at ``token``."""
        if token.type == TT.EOF:
            self._report(token.line, " at end", message)
        else:
            self._report(token.line, f" at '{token.lexeme}'", message)

    def _resolve_error(self, token: Token, message: str) -> None:
        """Report a static resolution error at ``token``."""
        self._report(token.line, f" at '{token.lexeme}'", message)

    def _resolve_warning(self, token: Token, message: str) -> None:
        """Print a non-fatal resolver warning to stderr."""
        where = f" at '{token.lexeme}'"
        print(f"[line {token.line}] Warning{where}: {message}", file=sys.stderr)

    def _report(self, line: int, where: str, message: str) -> None:
        """Print an error to stderr and mark that this run has failed."""
        print(f"[line {line}] Error{where}: {message}", file=sys.stderr)
        self.had_error = True

    def _runtime_error(self, error: LoxRuntimeError) -> None:
        """Print a runtime error to stderr and mark that this run has failed."""
        print(f"{error.message}\n[line {error.token.line}]", file=sys.stderr)
        self.had_runtime_error = True
