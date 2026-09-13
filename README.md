# lox-in-python

A tree-walking interpreter for the **Lox** language, written in Python
with no third-party runtime dependencies (Python 3.9+).

Lox is the small dynamically-typed scripting language: C-like syntax, variables, closures,
classes with single inheritance, and first-class functions.

## Features

- **Scanner** — tokenizes source text, including line comments (`//`)
  and nestable block comments (`/* ... */`).
- **Parser** — recursive-descent parser producing an AST (see
  `parser.py` for the full grammar).
- **Resolver** — a static pass that pre-computes variable scope
  distances and catches a handful of errors before execution (`this`
  outside a class, `return` outside a function, `break`/`continue`
  outside a loop, reading a variable in its own initializer, and warns
  about unused local variables).
- **Interpreter** — evaluates the resolved AST directly.

Beyond the base language, this implementation also supports:

- the comma operator: `a, b`
- the ternary conditional operator: `cond ? a : b`
- `%` (modulo)
- string + number concatenation (`"n = " + 4`)
- `break` and `continue` inside loops
- anonymous functions / lambdas: `fun (a) { return a; }`
- static methods: `class Foo { class bar() { ... } }`
- getters: `class Circle { area { return ...; } }`
- a REPL that auto-prints the value of a bare expression

Division/modulo by zero and reading an uninitialized variable are
reported as runtime errors rather than producing `inf`/`nil`.

## Project layout

```
__main__.py       command-line entry point (python -m lox-in-python)
lox.py            driver: wires scanner/parser/resolver/interpreter together
tokens.py         TokenType enum and the Token record
scanner.py        lexer
ast_nodes.py      AST node classes (Expr / Stmt)
parser.py         recursive-descent parser (grammar documented in the module docstring)
resolver.py       static variable-scope resolution pass
environment.py    lexical scope / variable storage
lox_callable.py   LoxFunction, LoxClass, LoxInstance, native functions
interpreter.py    tree-walking evaluator
ast_printer.py    optional debugging visitors (prefix and RPN printers)
errors.py         exception types and error-reporter callback signatures
tests/            automated tests (see below)
```

## Usage

From the parent directory of `lox-in-python`:

```bash
# interactive REPL
python3 -m lox-in-python

# run a script
python3 -m lox-in-python path/to/script.lox
```

Exit codes from running a script: `0` on success, `65` on a
scan/parse/resolve error, `70` on an unhandled runtime error.

### REPL example

```
> 1 + 2
3
> var a = 10;
> a * 2
20
> print "hi";
hi
```

## Running the tests

The test suite uses only the standard library (`unittest`), so no
extra install is required:

```bash
# from the parent directory of lox-in-python
python3 -m unittest discover -s lox-in-python/tests -v
```

It also runs with `pytest` if you have it installed:

```bash
python3 -m pytest lox-in-python/tests
```

The tests cover the scanner (tokens, string/number literals, both
comment styles), the environment (variable definition/lookup/scoping,
including the uninitialized-variable case), and the interpreter
end-to-end: arithmetic and string operations, control flow (`if`,
`while`, `for`, `break`, `continue`), functions and closures
(including recursion), classes (fields, methods, `init`, inheritance,
`super`, static methods, getters), the extra operators (comma,
ternary, modulo), and error handling (division by zero, uninitialized
variable access, syntax errors).
