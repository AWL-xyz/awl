# Awl 0.4: tagged unions and exhaustive match

**Implemented in 0.4, partial M1.** This document records that release;
[INTEGERS.md](INTEGERS.md) describes the subsequent 0.5 additions. This increment adds finite sum types to Awl's
existing scalar and value-struct subset. Generic types, built-in Option/Result,
error propagation operators, ownership, allocation and exceptions remain absent.

## Run it

```sh
python compiler/kcc.py run examples/results.aw
python compiler/kcc.py run examples/results.aw --sanitize
python compiler/kcc.py check tests/diagnostics/missing-case.aw
python benchmarks/run.py --case unions
```

The results example prints `7`, `true`, `6`, `false`, `false`, `-1` on separate lines.
The missing-case fixture is intentionally invalid and exits with a diagnostic.

## Declarations and constructors

```lua
union MaybeI64
    Some(value:i64)
    None()
end

union Lookup
    Found(value:i64, cached:bool)
    Missing()
    Failed(code:u64)
end
```

A union is a nominal type. It has at least one variant; each variant has zero or
more named, typed payload fields. Constructors are qualified and positional:
`Lookup.Found(42, true)`, `Lookup.Missing()`, `Lookup.Failed(7u64)`. Parentheses
are required even for nullary variants. Field names document declarations; they
are not constructor argument labels.

All payload values must be provided in declaration order with exact matching
types. Arguments evaluate left to right. Payloads may be scalars, structs, or
other finite unions. Forward aggregate type references are allowed. Every
by-value layout cycle is rejected, including a cycle with a nullary alternative;
recursive data structures require future indirection and ownership support.

Union names share the module's currently single-file declaration namespace with
structs and functions. Variant names belong to their own union: two unions may
each declare `Some`, but duplicate variants within one union are errors. A
qualified call such as `Type.Variant(...)` is a union constructor, **not** a method
call, module import or arbitrary member-function invocation.

All current values are copyable. Whole union values can be assigned, stored in
struct fields, passed as parameters and returned. The active tag travels with its
payload. Equality/ordering and automatic printing are not supported for unions.
Tags and payload storage are not directly accessible; `result.value` or
`result.k_tag` is rejected. Extraction requires a match.

## Statement matches

```lua
function read_or_default(value:MaybeI64, fallback:i64)->i64
    match value then
        case MaybeI64.Some(number) then
            return number
        case MaybeI64.None() then
            return fallback
    end
end
```

A match is a **statement**, not an expression. It evaluates its scrutinee exactly
once and matches a by-value snapshot. The scrutinee must have a union type.

Every variant must appear exactly once, regardless of whether the scrutinee is a
known constructor. Cases can appear in any order. The checker rejects:

- missing, duplicate or unknown variants;
- a case qualified with a different union type;
- a non-union scrutinee;
- incorrect payload-binding counts or duplicate non-discard binding names.

There is no wildcard arm, `else`, guard, literal/range pattern or nested pattern
syntax yet. Adding a variant deliberately breaks every match that has not been
updated, instead of silently routing it to a catch-all. Nested matches provide
explicit inspection of union-valued payloads.

Each payload position uses a binding name or `_` to discard it:

```lua
match lookup then
    case Lookup.Found(value, _) then
        print(value)
    case Lookup.Missing() then
        print(0)
    case Lookup.Failed(code) then
        print(code)
end
```

Bindings are independently mutable payload copies and exist only in their case.
They can shadow enclosing locals without changing those outer locals. Repeated
`_` is permitted; discard introduces no binding or generated symbol. If an outer
local happens to be named `_`, it is still visible in a case that discards a
payload; discard does not shadow it. Like parameters, pattern bindings form an
outer scope relative to a case's statement block, so a local declaration in that
block may shadow a pattern binding.

Case bodies may update enclosing mutable locals. Reassigning the original
scrutinee variable does not change the snapshot or extracted payload copies.
Cases do not fall through. A match returns on all paths only if every case's body
returns on all paths; the checker uses that fact for function return coverage
and unreachable-statement rejection. Ordinary side-effecting matches can fall
through to later statements.

## Explicit errors, not changed traps

The runnable example defines a concrete `DivideResult` with `Ok`, `ZeroDivisor`
and `Overflow` variants. `divide` tests for zero and MIN/-1 before performing
checked arithmetic, then returns an error variant instead of reaching a trap.

This is a library-level coding pattern, not automatic exception conversion.
Unprotected division by zero and overflow still abort as specified. There is no
hidden unwinding, error propagation operator, implicit allocation, generic
`Result[T,E]`, or standard-library error hierarchy in this release.

## Compiler implementation

The typed structured KIR0 adds `union`, `variant_decl`, `union_ctor`, `match`,
`case`, and `pattern_bind` nodes. Pattern bindings receive payload type annotations
and fresh resolved local symbols; `_` has a type but no symbol. The schema is now
`KIR0-structured-v0.4`. It retains a top-level `declarations` array and is not a
stable interchange format.

The checker independently verifies constructor argument types and match coverage.
The read-only IR verifier repeats declaration/schema, qualified-constructor,
coverage, binder type/identity/scope and branch-return checks without invoking the
type checker. A shared aggregate layout utility handles graph cycles and budgets;
this part is not an independently implemented layout algorithm.

The C11 backend emits a native struct containing a uint32 tag and a C union of
per-variant payload structs. Tags follow declaration order, starting at zero.
Nullary variants use a private one-byte dummy payload because standard C has no
empty structs. Constructors initialize the chosen payload member and its tag.
Match emits a switch on the saved tag and reads only that case's payload member.
A default branch aborts on a corrupt tag instead of proceeding with arbitrary
payload storage. Source-level safe code has no tag-forging or raw-memory API;
the defensive branch is tested using deliberately corrupted emitted C, not a
legal Awl program.

No boxing, scheduler or reference-counting runtime is introduced. The cost is
inline storage for the **largest payload**, plus the tag and padding. Returning
large unions or matching them may copy aggregates; optimization can remove some
copies but is not guaranteed to do so. No niche encoding, tag elision, pointer
tagging, or stable ABI is promised. Actual object layout is delegated to the
host C compiler and is not exposed to Awl programs.

Future ownership must distinguish moving and borrowing non-Copy payloads before
such types are accepted. The current snapshot/copy semantics must not silently
duplicate a future resource-owning payload. This release is not an ownership
checker or a formal safety proof.

### Defensive limits

- 1..128 variants per union; 0..128 payload fields per variant.
- Existing scalar/aggregate type validation and duplicate-field rejection apply.
- No recursive value graphs, including struct/union mixed cycles.
- At most 64 aggregate nesting levels and a 1,048,576-byte estimated native value
  size per aggregate, including the tag and estimated padding.
- Existing source, token, parser-depth and IR-depth budgets remain enforced.

Size/alignment estimates remain bootstrap compiler resource bounds, **not** target
ABI guarantees. They do not limit total native stack usage. Recursive functions
and many large locals can still exhaust the stack.

## Validation evidence

158 unittest methods pass locally on Linux x86-64/GCC 14.2.0/Python 3.13.16:

- All 96 prior methods remain passing; 62 union-related methods were added.
- Negative tests cover layout cycles, declaration collisions, variant/field limits,
  constructor signatures, exhaustive coverage, scope, binding counts and returns.
- IR mutation tests remove/duplicate arms and corrupt qualified identities,
  constructor types, binders, payload references and declaration shapes.
- Native tests cover nullary/payload variants, out-of-order cases, snapshot
  semantics, outer variable mutation, shadowing, nested matches, struct fields,
  evaluation order, total returns and defensive invalid-tag aborts.
- 150 seeded generated union matches, with randomized arm order, compare native
  O0 and O3 output against Python values. Earlier 400 expression cases remain.
- 750 new source mutations bring the total seeded mutation cases to 2,250.
- `examples/results.aw` passed AddressSanitizer/UndefinedBehaviorSanitizer smoke
  execution. This is not sanitizer execution of the entire regression suite.
- Diagnostic goldens now include a missing-case example.

See `tests/latest.txt`, `tests/validation.json` and sanitizer logs. None of these
constitutes a soundness proof. Linux Clang and Windows MinGW CI remain authored,
not executed in this workspace.

## Benchmark

`python benchmarks/run.py --case unions` runs 5,000,000 bounded recurrence steps,
constructs a `Selected` union, matches it, accumulates selected payloads and counts
skipped values. A native C tagged-union implementation uses the same algorithm.
Both are independently checked against Python outside timing. Expected output:

```
4292128103872500
1000189
1901417813
```

Local O3 medians over seven warmed-up process launches: Awl **33.223 ms**, C
**32.920 ms**, ratio **1.009×**. Those raw samples: `benchmarks/unions-baseline-0.4.0.json`.

Process startup is included, cores/frequency are uncontrolled, run order is fixed,
and the workload is one scalar recurrence. The C baseline omits arithmetic checks
but all values are mathematically bounded. These results do not establish general
performance parity, lack of aggregate copying, vectorization, GPU execution or
cross-platform correctness.
