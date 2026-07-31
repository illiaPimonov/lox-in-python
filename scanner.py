from __future__ import annotations

from typing import List

from .tokens import Token, TokenType, KEYWORDS

TT = TokenType

class Scanner:
    def __init__(self, source: str, error_reporter):
        self.source = source
        self.error_reporter = error_reporter
        self.tokens: List[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1

    def scan_tokens(self) -> List[Token]:
        while not self._is_at_end():
            self.start = self.current
            self._scan_token()

        self.tokens.append(Token(TT.EOF, "", None, self.line))
        return self.tokens

    def _scan_token(self) -> None:
        c = self._advance()
        if c == "(":
            self._add_token(TT.LEFT_PAREN)
        elif c == ")":
            self._add_token(TT.RIGHT_PAREN)
        elif c == "{":
            self._add_token(TT.LEFT_BRACE)
        elif c == "}":
            self._add_token(TT.RIGHT_BRACE)
        elif c == ",":
            self._add_token(TT.COMMA)
        elif c == ".":
            self._add_token(TT.DOT)
        elif c == "-":
            self._add_token(TT.MINUS)
        elif c == "+":
            self._add_token(TT.PLUS)
        elif c == ";":
            self._add_token(TT.SEMICOLON)
        elif c == "*":
            self._add_token(TT.STAR)
        elif c == "%":
            self._add_token(TT.PERCENT)
        elif c == "?":
            self._add_token(TT.QUESTION)
        elif c == ":":
            self._add_token(TT.COLON)
        elif c == "!":
            self._add_token(TT.BANG_EQUAL if self._match("=") else TT.BANG)
        elif c == "=":
            self._add_token(TT.EQUAL_EQUAL if self._match("=") else TT.EQUAL)
        elif c == "<":
            self._add_token(TT.LESS_EQUAL if self._match("=") else TT.LESS)
        elif c == ">":
            self._add_token(TT.GREATER_EQUAL if self._match("=") else TT.GREATER)
        elif c == "/":
            if self._match("/"):
                while self._peek() != "\n" and not self._is_at_end():
                    self._advance()
            elif self._match("*"):
                self._block_comment()
            else:
                self._add_token(TT.SLASH)
        elif c in (" ", "\r", "\t"):
            pass
        elif c == "\n":
            self.line += 1
        elif c == '"':
            self._string()
        else:
            if c.isdigit():
                self._number()
            elif c.isalpha() or c == "_":
                self._identifier()
            else:
                self.error_reporter(self.line, f"Unexpected character '{c}'.")

    def _block_comment(self) -> None:
        depth = 1
        while depth > 0:
            if self._is_at_end():
                self.error_reporter(self.line, "Unterminated block comment.")
                return
            if self._peek() == "/" and self._peek_next() == "*":
                self._advance()
                self._advance()
                depth += 1
                continue
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                depth -= 1
                continue
            if self._peek() == "\n":
                self.line += 1
            self._advance()

    def _string(self) -> None:
        while self._peek() != '"' and not self._is_at_end():
            if self._peek() == "\n":
                self.line += 1
            self._advance()

        if self._is_at_end():
            self.error_reporter(self.line, "Unterminated string.")
            return

        self._advance()

        value = self.source[self.start + 1:self.current - 1]
        self._add_token(TT.STRING, value)

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()

        self._add_token(TT.NUMBER, float(self.source[self.start:self.current]))

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        text = self.source[self.start:self.current]
        token_type = KEYWORDS.get(text, TT.IDENTIFIER)
        self._add_token(token_type)

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1
        return c

    def _add_token(self, token_type: TokenType, literal=None) -> None:
        text = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, text, literal, self.line))

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)
