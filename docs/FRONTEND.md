# Frontend hardening in KCC 0.2

Status: implemented and locally tested, **partial M1**, not completion of M1.
No new memory, concurrency, module, or GPU capabilities are implied. This document
records the 0.2 increment; [VALUES.md](VALUES.md) describes the subsequent 0.3 release.

## Diagnostics

```
python compiler/kcc.py check tests/diagnostics/multiple.aw
python compiler/kcc.py check tests/diagnostics/multiple.aw --diagnostic-format json
```

Both commands return status 1. The first prints two errors with filenames,
line/column anchors and underlines; the second writes a JSON diagnostic object to
stderr. Successful check output remains plain text. JSON is not an LSP protocol.

Each source token carries `start` and `end` offsets. JSON diagnostics expose these
as zero-based, half-open **Unicode code-point offsets**, not UTF-8 byte offsets;
line/column are one-based, end_column exclusive. Columns count a tab as one source
character. Text rendering expands tabs to four-column stops. Carets are token
anchors, not complete AST-expression spans. For a return type mismatch, the
`return` keyword is underlined; parenthesized expressions do not retain full ranges.
The synthetic minimum-i64 literal retains its unary-minus anchor.

The source is UTF-8; invalid encodings are rejected. Input limits count UTF-8 bytes.
Long diagnostic excerpts and underlines are clipped to prevent output amplification.
Codes are bootstrap categories, not a promised stable diagnostics API:

| Code | Meaning |
|---|---|
| E001 | Source size limit |
| E002 | Recursive syntax nesting limit |
| E003 | Identifier length limit |
| E004 | Integer token length limit |
| E005 | Token count limit |
| E006 / E007 | IR nesting / node budget |
| E008 | Invalid UTF-8 |
| E100 / E101 | Syntax / unexpected lexical character |
| E200 / E201 | Type, scope, return / entry point |
| E210 | Declaration/layout error (added in 0.3) |
| E500 | Internal IR verifier rejection |
| E900 | Uncategorized driver/compiler error |

### Recovery boundaries

The parser synchronizes after a syntax error at a semicolon, the current block's
end token, a subsequent function, or a later-line `local`, `return`, `if`, or
`while`. Top-level recovery scans to the next `function`. It collects up to 20
syntax diagnostics, then stops. Lexer, resource-limit, and semantic errors remain
fail-fast. Recovery is deliberately conservative and can produce cascading errors
for missing delimiters; it is not a full incremental/editor parser.

**No compilation continues after any recovered error.** The partial AST is thrown
away before checking or emission, so an erroneous program cannot accidentally
produce an executable from only its valid statements. A future editor service
will need explicit error nodes instead of this batch-only design.

## Resource budgets

| Resource | Limit |
|---|---:|
| Source | 1,048,576 UTF-8 bytes |
| Tokens before EOF | 100,000 |
| Recursive syntax nesting | 64 active guarded parser calls |
| IR node depth | 64 |
| IR nodes | 100,000 |
| Identifier | 128 ASCII characters |
| Decimal integer token | 256 digits |
| Reported syntax diagnostics | 20 |

The parser nesting budget counts both expression and block calls, not simply
parentheses. A left-associative chain can be shallow in the parser but deep in its
AST, hence the separate iterative IR-depth check **before** recursive type checking.
File reads request at most the byte budget plus one byte, rather than reading an
unbounded file and checking afterward. The direct `compile_text` API applies the
same source budget before lexing.

These are defensive bootstrap limits, not a sandbox or denial-of-service proof.
They do not limit native compiler resource use, executable runtime, recursion in
compiled programs, filesystem permissions, or subprocess wall time. Source is
untrusted input; executing its compiled output is a separate trust decision.
Compiler subprocesses do not run in a security sandbox.

## Signed literals

The exact token pair `-` followed by decimal magnitude 9223372036854775808 folds
into an i64 minimum literal before checking. Whitespace between tokens is allowed.
A larger magnitude is rejected. Parenthesized positive magnitude remains out of
range: `-(9223372036854775808)` is not accepted. Positive literals keep the original
0..9223372036854775807 bound. C emission uses `INT64_MIN`, avoiding an oversized
signed C literal. Negating the minimum again traps normally.

## KIR0 verifier

`verify_ir` independently traverses checked IR without calling the type checker
or rewriting annotations. It validates:

- function/parameter signatures, entry point, emitted identifier shapes;
- statement/expression kinds and child counts;
- globally unique generated binding identities and lexical name resolution;
- literal bounds, operator domains and expression type annotations;
- call arguments, assignments, returns, branch conditions;
- total returns and unreachable statements.

It runs after type checking and again at the C-emission boundary, so test or future
transformation code cannot silently corrupt an annotation before emission. The
second pass adds compile-time overhead; native execution is unaffected. Mutation
tests corrupt types, operators, bindings, calls, literals and control flow and
expect rejection. The verifier is defense in depth, not a formal safety proof or
a general-purpose validator for adversarial Python object graphs. No serialized
IR loader exists. It does not establish that the parser or emitter is correct.

The JSON IR version is `KIR0-structured-v0.2`; added token offsets change the
serialized schema. No stable interchange or binary compatibility is promised.

## Evidence and remaining work

57 unittest methods pass locally on Linux x86-64/GCC 14.2.0/Python 3.13.16:
- Original 24 tests remain passing.
- Checked-in text diagnostic goldens, JSON/UTF-8 and recovery tests.
- Limit tests and malformed-IR mutation tests.
- 1,000 seeded insert/delete/duplicate source mutations within one test method.
- 200 generated typed expressions, independently evaluated in Python, compiled
  and run at O0 and O3 within one test method (100 integer, 100 boolean).
- Native minimum-literal and minimum-negation tests.

The arithmetic generator computes truncating division and signed remainder
explicitly instead of using Python's floor-division semantics. Only bounded
well-defined expressions are generated. These samples test compiler behavior;
they do not establish soundness. Sanitizers ran on `examples/hello.aw`, not the whole
test suite. See `tests/latest.txt` and `tests/sanitizer-smoke.txt`.

The CI matrix now includes Linux GCC, Linux Clang and Windows MinGW GCC; it has
not been executed in this workspace. Missing M1 work includes additional scalar
widths, structures/unions, exhaustive match, richer full-expression ranges,
long-running coverage-guided fuzzing and actual cross-platform CI evidence.
