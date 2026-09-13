"""Unit tests for Environment: variable definition, lookup, scoping, assignment."""

import unittest

from _pkg import imp

tokens_mod = imp("tokens")
Token = tokens_mod.Token
TokenType = tokens_mod.TokenType
env_mod = imp("environment")
Environment = env_mod.Environment
UNINITIALIZED = env_mod.UNINITIALIZED
errors_mod = imp("errors")
LoxRuntimeError = errors_mod.LoxRuntimeError


def name_token(lexeme: str) -> Token:
    """Build a minimal IDENTIFIER token for use as a variable name."""
    return Token(TokenType.IDENTIFIER, lexeme, None, 1)


class EnvironmentTests(unittest.TestCase):
    def test_define_and_get(self) -> None:
        env = Environment()
        env.define("x", 42.0)
        self.assertEqual(env.get(name_token("x")), 42.0)

    def test_get_undefined_raises(self) -> None:
        env = Environment()
        with self.assertRaises(LoxRuntimeError):
            env.get(name_token("missing"))

    def test_assign_undefined_raises(self) -> None:
        env = Environment()
        with self.assertRaises(LoxRuntimeError):
            env.assign(name_token("missing"), 1.0)

    def test_lookup_falls_through_to_enclosing_scope(self) -> None:
        outer = Environment()
        outer.define("x", 1.0)
        inner = Environment(outer)
        self.assertEqual(inner.get(name_token("x")), 1.0)

    def test_inner_scope_shadows_outer(self) -> None:
        outer = Environment()
        outer.define("x", 1.0)
        inner = Environment(outer)
        inner.define("x", 2.0)
        self.assertEqual(inner.get(name_token("x")), 2.0)
        self.assertEqual(outer.get(name_token("x")), 1.0)

    def test_assign_updates_nearest_existing_binding(self) -> None:
        outer = Environment()
        outer.define("x", 1.0)
        inner = Environment(outer)
        inner.assign(name_token("x"), 99.0)
        self.assertEqual(outer.get(name_token("x")), 99.0)

    def test_get_at_and_assign_at_use_ancestor_distance(self) -> None:
        outer = Environment()
        outer.define("x", 1.0)
        middle = Environment(outer)
        inner = Environment(middle)

        self.assertEqual(inner.get_at(2, "x"), 1.0)
        inner.assign_at(2, name_token("x"), 5.0)
        self.assertEqual(outer.get(name_token("x")), 5.0)

    def test_uninitialized_variable_raises_on_get(self) -> None:
        env = Environment()
        env.define("x", UNINITIALIZED)
        with self.assertRaises(LoxRuntimeError):
            env.get(name_token("x"))

    def test_assigning_clears_uninitialized_state(self) -> None:
        env = Environment()
        env.define("x", UNINITIALIZED)
        env.assign(name_token("x"), 7.0)
        self.assertEqual(env.get(name_token("x")), 7.0)


if __name__ == "__main__":
    unittest.main()
