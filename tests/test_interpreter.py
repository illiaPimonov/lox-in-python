"""End-to-end tests: run small Lox programs through the full
scan -> parse -> resolve -> interpret pipeline and check their output.

These exercise the language as a whole (rather than any one module in
isolation), covering the core language plus the extra features listed
in the project README.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from typing import Tuple

from _pkg import imp

Lox = imp("lox").Lox


def run_source(source: str) -> Tuple[str, str, int]:
    """Run ``source`` as a script and return (stdout, stderr, exit_code)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = Path(tmp_dir) / "program.lox"
        script_path.write_text(source, encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = Lox().run_file(str(script_path))

        return stdout.getvalue(), stderr.getvalue(), exit_code


class ArithmeticAndStringsTests(unittest.TestCase):
    def test_basic_arithmetic(self) -> None:
        out, err, code = run_source("print 1 + 2 * 3;")
        self.assertEqual(out, "7\n")
        self.assertEqual(code, 0)

    def test_string_concatenation(self) -> None:
        out, _, code = run_source('print "foo" + "bar";')
        self.assertEqual(out, "foobar\n")
        self.assertEqual(code, 0)

    def test_string_plus_number_stringifies(self) -> None:
        out, _, code = run_source('print "count: " + 4;')
        self.assertEqual(out, "count: 4\n")
        self.assertEqual(code, 0)

    def test_integer_valued_floats_print_without_decimal(self) -> None:
        out, _, _ = run_source("print 6 / 2;")
        self.assertEqual(out, "3\n")

    def test_modulo_operator(self) -> None:
        out, _, code = run_source("print 10 % 3;")
        self.assertEqual(out, "1\n")
        self.assertEqual(code, 0)

    def test_comma_operator(self) -> None:
        out, _, code = run_source("print (1 + 1, 2 + 2);")
        self.assertEqual(out, "4\n")
        self.assertEqual(code, 0)

    def test_ternary_operator(self) -> None:
        out, _, code = run_source('print 5 > 3 ? "big" : "small";')
        self.assertEqual(out, "big\n")
        self.assertEqual(code, 0)


class ControlFlowTests(unittest.TestCase):
    def test_if_else(self) -> None:
        out, _, _ = run_source('if (1 < 2) print "yes"; else print "no";')
        self.assertEqual(out, "yes\n")

    def test_while_loop(self) -> None:
        out, _, _ = run_source(
            "var i = 0; while (i < 3) { print i; i = i + 1; }"
        )
        self.assertEqual(out, "0\n1\n2\n")

    def test_for_loop(self) -> None:
        out, _, _ = run_source("for (var i = 0; i < 3; i = i + 1) print i;")
        self.assertEqual(out, "0\n1\n2\n")

    def test_break_exits_loop(self) -> None:
        out, _, code = run_source(
            "for (var i = 0; i < 10; i = i + 1) { if (i == 3) break; print i; }"
        )
        self.assertEqual(out, "0\n1\n2\n")
        self.assertEqual(code, 0)

    def test_continue_skips_iteration(self) -> None:
        out, _, code = run_source(
            "for (var i = 0; i < 4; i = i + 1) { if (i == 2) continue; print i; }"
        )
        self.assertEqual(out, "0\n1\n3\n")
        self.assertEqual(code, 0)

    def test_break_outside_loop_is_a_static_error(self) -> None:
        _, err, code = run_source("break;")
        self.assertEqual(code, 65)
        self.assertIn("break", err)


class FunctionTests(unittest.TestCase):
    def test_function_call_and_return(self) -> None:
        out, _, code = run_source(
            "fun square(x) { return x * x; } print square(5);"
        )
        self.assertEqual(out, "25\n")
        self.assertEqual(code, 0)

    def test_recursion(self) -> None:
        out, _, _ = run_source(
            "fun fib(n) { if (n < 2) return n; return fib(n - 1) + fib(n - 2); } print fib(10);"
        )
        self.assertEqual(out, "55\n")

    def test_closures_capture_by_reference(self) -> None:
        out, _, _ = run_source(
            """
            fun makeCounter() {
              var count = 0;
              fun counter() {
                count = count + 1;
                return count;
              }
              return counter;
            }
            var counter = makeCounter();
            print counter();
            print counter();
            print counter();
            """
        )
        self.assertEqual(out, "1\n2\n3\n")

    def test_anonymous_function(self) -> None:
        out, _, _ = run_source(
            'var add = fun (a, b) { return a + b; }; print add(2, 3);'
        )
        self.assertEqual(out, "5\n")


class ClassTests(unittest.TestCase):
    def test_init_and_method(self) -> None:
        out, _, code = run_source(
            """
            class Greeter {
              init(name) { this.name = name; }
              greet() { return "hi " + this.name; }
            }
            print Greeter("world").greet();
            """
        )
        self.assertEqual(out, "hi world\n")
        self.assertEqual(code, 0)

    def test_inheritance_and_super(self) -> None:
        out, _, code = run_source(
            """
            class Animal {
              speak() { return "..."; }
            }
            class Dog < Animal {
              speak() { return super.speak() + " woof"; }
            }
            print Dog().speak();
            """
        )
        self.assertEqual(out, "... woof\n")
        self.assertEqual(code, 0)

    def test_static_method(self) -> None:
        out, _, code = run_source(
            """
            class MathUtil {
              class square(n) { return n * n; }
            }
            print MathUtil.square(6);
            """
        )
        self.assertEqual(out, "36\n")
        self.assertEqual(code, 0)

    def test_getter(self) -> None:
        out, _, code = run_source(
            """
            class Circle {
              init(r) { this.r = r; }
              doubled { return this.r * 2; }
            }
            print Circle(3).doubled;
            """
        )
        self.assertEqual(out, "6\n")
        self.assertEqual(code, 0)


class ErrorHandlingTests(unittest.TestCase):
    def test_division_by_zero_is_a_runtime_error(self) -> None:
        _, err, code = run_source("print 1 / 0;")
        self.assertEqual(code, 70)
        self.assertIn("Division by zero", err)

    def test_uninitialized_variable_is_a_runtime_error(self) -> None:
        _, err, code = run_source("var a; print a;")
        self.assertEqual(code, 70)
        self.assertIn("initialized", err)

    def test_syntax_error_is_reported_without_crashing(self) -> None:
        _, err, code = run_source("var = ;")
        self.assertEqual(code, 65)
        self.assertTrue(err)

    def test_calling_a_non_callable_is_a_runtime_error(self) -> None:
        _, err, code = run_source('var x = 1; x();')
        self.assertEqual(code, 70)
        self.assertIn("Can only call", err)


if __name__ == "__main__":
    unittest.main()
