"""Unit tests for the Scanner: token kinds, literals, and comment handling."""

import unittest
from typing import List, Tuple

from _pkg import imp

tokens_mod = imp("tokens")
Token = tokens_mod.Token
TokenType = tokens_mod.TokenType
Scanner = imp("scanner").Scanner


def scan(source: str) -> Tuple[List[Token], List[Tuple[int, str]]]:
    """Scan ``source`` and return (tokens, list of (line, message) errors)."""
    errors: List[Tuple[int, str]] = []
    tokens = Scanner(source, lambda line, message: errors.append((line, message))).scan_tokens()
    return tokens, errors


def types_of(tokens: List[Token]) -> List[TokenType]:
    """Return just the TokenType sequence, for concise assertions."""
    return [t.type for t in tokens]


class ScannerTests(unittest.TestCase):
    def test_empty_source_is_just_eof(self) -> None:
        toks, errors = scan("")
        self.assertEqual(types_of(toks), [TokenType.EOF])
        self.assertEqual(errors, [])

    def test_single_and_double_char_operators(self) -> None:
        toks, errors = scan("!= == <= >= < > = ! + - * / % ? :")
        self.assertEqual(errors, [])
        self.assertEqual(
            types_of(toks),
            [
                TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL, TokenType.LESS_EQUAL,
                TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.GREATER,
                TokenType.EQUAL, TokenType.BANG, TokenType.PLUS, TokenType.MINUS,
                TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
                TokenType.QUESTION, TokenType.COLON, TokenType.EOF,
            ],
        )

    def test_number_literal(self) -> None:
        toks, errors = scan("123 4.5")
        self.assertEqual(errors, [])
        self.assertEqual(toks[0].literal, 123.0)
        self.assertEqual(toks[1].literal, 4.5)

    def test_string_literal(self) -> None:
        toks, errors = scan('"hello world"')
        self.assertEqual(errors, [])
        self.assertEqual(toks[0].type, TokenType.STRING)
        self.assertEqual(toks[0].literal, "hello world")

    def test_unterminated_string_reports_error(self) -> None:
        toks, errors = scan('"oops')
        self.assertTrue(errors)
        self.assertIn("Unterminated string", errors[0][1])

    def test_keywords_vs_identifiers(self) -> None:
        toks, errors = scan("var class fun myVariable _private")
        self.assertEqual(errors, [])
        self.assertEqual(
            types_of(toks)[:-1],
            [TokenType.VAR, TokenType.CLASS, TokenType.FUN, TokenType.IDENTIFIER, TokenType.IDENTIFIER],
        )

    def test_line_comment_is_ignored(self) -> None:
        toks, errors = scan("1 // this is a comment\n2")
        self.assertEqual(errors, [])
        self.assertEqual([t.literal for t in toks if t.type == TokenType.NUMBER], [1.0, 2.0])

    def test_nested_block_comments(self) -> None:
        toks, errors = scan("1 /* outer /* inner */ still outer */ 2")
        self.assertEqual(errors, [])
        self.assertEqual([t.literal for t in toks if t.type == TokenType.NUMBER], [1.0, 2.0])

    def test_unterminated_block_comment_reports_error(self) -> None:
        toks, errors = scan("/* never closed")
        self.assertTrue(errors)
        self.assertIn("Unterminated block comment", errors[0][1])

    def test_line_numbers_advance_across_newlines(self) -> None:
        toks, errors = scan("1\n2\n3")
        self.assertEqual(errors, [])
        numbers = [t for t in toks if t.type == TokenType.NUMBER]
        self.assertEqual([t.line for t in numbers], [1, 2, 3])

    def test_unexpected_character_reports_error_but_keeps_scanning(self) -> None:
        toks, errors = scan("1 @ 2")
        self.assertEqual(len(errors), 1)
        self.assertEqual([t.literal for t in toks if t.type == TokenType.NUMBER], [1.0, 2.0])


if __name__ == "__main__":
    unittest.main()
