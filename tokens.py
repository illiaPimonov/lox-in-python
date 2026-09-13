"""Lexical token definitions for the Lox scanner and parser.

Defines the set of token kinds the scanner can produce (``TokenType``),
the keyword lookup table used while scanning identifiers, and the
immutable ``Token`` record that pairs a token kind with its source text,
literal value and line number.
"""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict


class TokenType(Enum):
    """Every distinct kind of lexeme the scanner can emit."""

    # Single-character tokens.
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    DOT = auto()
    MINUS = auto()
    PLUS = auto()
    SEMICOLON = auto()
    SLASH = auto()
    STAR = auto()
    PERCENT = auto()
    QUESTION = auto()
    COLON = auto()

    # One or two character tokens.
    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    # Literals.
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Keywords.
    AND = auto()
    CLASS = auto()
    ELSE = auto()
    FALSE = auto()
    FUN = auto()
    FOR = auto()
    IF = auto()
    NIL = auto()
    OR = auto()
    PRINT = auto()
    RETURN = auto()
    SUPER = auto()
    THIS = auto()
    TRUE = auto()
    VAR = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()

    EOF = auto()


KEYWORDS: Dict[str, TokenType] = {
    "and": TokenType.AND,
    "class": TokenType.CLASS,
    "else": TokenType.ELSE,
    "false": TokenType.FALSE,
    "for": TokenType.FOR,
    "fun": TokenType.FUN,
    "if": TokenType.IF,
    "nil": TokenType.NIL,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
    "return": TokenType.RETURN,
    "super": TokenType.SUPER,
    "this": TokenType.THIS,
    "true": TokenType.TRUE,
    "var": TokenType.VAR,
    "while": TokenType.WHILE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
}
"""Maps reserved words to their token kind; anything else scans as IDENTIFIER."""


@dataclass(frozen=True)
class Token:
    """A single lexeme produced by the scanner.

    Attributes:
        type: The kind of token (see ``TokenType``).
        lexeme: The exact source text that produced this token.
        literal: The decoded literal value for NUMBER/STRING tokens, else None.
        line: The 1-based source line the token started on, used in error messages.
    """

    type: TokenType
    lexeme: str
    literal: Any
    line: int

    def __str__(self) -> str:
        """Return a compact debug representation, e.g. ``NUMBER 3 3.0``."""
        return f"{self.type.name} {self.lexeme} {self.literal}"
