# Awl 0.3: unsigned integers and value structs

**Implemented in 0.3, partial M1.** This document records that release;
[UNIONS.md](UNIONS.md) describes the subsequent 0.4 additions. This milestone adds structured values, not ownership,
references, heap allocation, foreign layout compatibility, or an optimizing KCC IR.
All syntax in the runnable example below is accepted by KCC 0.3.

## Run the example

```sh
python compiler/kcc.py run examples/values.aw
python compiler/kcc.py run examples/values.aw --sanitize
python compiler/kcc.py emit-ir examples/values.aw -o values.kir.json
python benchmarks/run.py --case values
```

`values.aw` prints `10`, `15`, `1`, `true`, and `18446744073709551615`, one per line.

```lua
struct Point
    x: i64
    y: i64
end

struct Particle
    position: Point
    ticks: u64
    active: bool
end

function advance(p: Particle, dx: i64) -> Particle
    p.position.x = p.position.x + dx
    p.ticks = p.ticks + 1u64
    return p
end

function main() -> i64
    local first: Particle = Particle(Point(10, 20), 0u64, true)
    local next: Particle = advance(first, 5)
    print(first.position.x) -- 10; parameter changes did not mutate this value
    print(next.position.x)  -- 15
    return 0
end
```

## Unsigned semantics

`u64` ranges from 0 through 18446744073709551615. A decimal suffix `u64` selects
unsigned literal type: `0u64`, `42u64`, `18446744073709551615u64`. Unsuffixed
literals remain `i64`; destination types do not implicitly retag them.

Arithmetic `+ - * / %`, comparisons and equality support matching unsigned
operands. There are **no implicit signed/unsigned conversions**, integer
promotions, or casts yet. For example, `local count: u64 = 1` is rejected; use
`1u64`. Unary minus requires i64 and rejects `-1u64`. `print` now accepts one
`i64`, `u64`, or `bool`. The main function still returns `i64`.

Unsigned add/multiply overflow, subtraction underflow, and division/remainder
by zero terminate with the same arithmetic trap as signed arithmetic, at all
optimization levels. C's default unsigned wrapping is **not** Awl semantics.
The emitted helpers check bounds before doing the unsigned operation. Explicit
wrapping/saturating operations are still proposed, not implemented.

## Struct semantics

- Structs are top-level, nominal, by-value product types. Same field shapes with
  different struct names are different types.
- Fields can contain i64, u64, bool or another valid struct, but never unit.
  All struct declarations are collected before checking; forward type references
  are allowed. By-value layout cycles, including indirect cycles, are rejected.
- A positional constructor uses the type's name. Every field must be provided,
  in declaration order, with exact matching types. Arguments evaluate left to right.
- Constructors and functions share a global call namespace. Duplicates, including
  collisions between struct and function names, are rejected. Locals are a
  separate namespace; local variables are not callable.
- Field selection `value.field` binds more tightly than unary and binary operators.
  Fields can be read from variables, constructors, function results and nested
  selections. Parentheses work normally.
- Local assignment, function arguments and returns **copy the entire value**.
  A parameter is an independent mutable value. There are no pointers, hidden
  shared state, reference counts or destructors in this subset.
- Mutating a field requires a local-rooted place, e.g. `particle.position.x = 4`.
  Whole-struct assignment and whole nested-field replacement work. Assignment to
  `make_particle().position.x` is rejected rather than silently updating a discarded
  temporary. Fields must exist and assigned values must match their exact type.
- Parameters count as local roots. A parenthesized local-rooted place is permitted.
  Local shadowing follows the original lexical-scope rules.
- Struct equality, automatic printing, field defaults, named constructors, methods,
  visibility modifiers and destructuring are not implemented.

All current value structs are freely copyable. This does **not** commit future
resource-owning structures to copy semantics: they will require ownership/move
analysis before they can be introduced. Raw bytes, padding, address identity and
struct layout are not observable in the current language.

## Compiler decisions

KIR0 adds `struct`, `field_decl`, `uint`, `field` and `store` node kinds. Plain
name assignment keeps its existing `assign` form. Expression nodes retain exact
type names and resolved local identities; field names remain nominal projections.
The serialized schema is `KIR0-structured-v0.3` with a top-level `declarations`
array instead of the old `functions` array. There is no stable serialized-IR loader.

Layout analysis topologically orders struct dependencies and rejects cycles.
The C backend emits one native C struct per Awl struct, compound literals for
constructors, value parameters/returns and normal field assignments. It materializes
operand values in order, allowing GCC/Clang to eliminate copies when legal. Some
copies can remain; predictable value semantics are prioritized over a premature
promise that every aggregate operation is free.

The independent IR verifier validates declaration/field uniqueness, type names,
constructor signatures, nominal projections, local-rooted store paths, scalar
operator domains, unsigned bounds and type annotations, in addition to its earlier
checks. It does not rerun the type checker. Layout-cycle/size checking is a shared
utility, so this portion is not an independently implemented layout algorithm.

### Bounds and ABI limits

Structs must have 1..128 fields. Maximum nesting is 64 value-struct levels.
Estimated natural layout size is bounded to 1,048,576 bytes per type, including
estimated padding. The bootstrap estimates bool size/alignment as 1/1 and i64/u64
as 8/8; nested structs use natural maximum alignment. This is a defensive compiler
budget for the supported host backend, **not an exported ABI or sizeof contract**.
C determines actual native layout. The language exposes neither layout queries
nor FFI in this release. A future target-aware ABI implementation must replace
these assumptions before cross-target layout promises are made.

The limit does not bound total stack usage. Many aggregate locals, copies, or
recursive calls can still exhaust the stack. No security or full memory-safety
claim follows from this scalar/value-only subset.

## Validation

96 unittest methods pass locally on Linux x86-64/GCC 14.2.0/Python 3.13.16:
- All 57 previous tests remain passing.
- 39 new methods cover unsigned bounds/mixing/traps, aggregate construction,
  nominal identity, fields and stores, forward declarations, cycles, graph depth,
  field/size limits, copy semantics, evaluation order and corrupted typed IR.
- 500 source mutations of the new example are included in one method, in addition
  to the earlier 1,000 malformed-source mutations.
- 200 seeded unsigned arithmetic/comparison cases compare native O0 and O3 output
  with a Python oracle. Earlier signed/boolean generated tests remain in place.
- The values example passed AddressSanitizer and UndefinedBehaviorSanitizer smoke
  execution. This is not sanitizer coverage of the entire regression suite.

`tests/latest.txt` records test methods; `tests/validation.json` records environment,
commands and outcomes. Windows/Clang CI is authored but unexecuted in this workspace.

## Benchmark evidence

`python benchmarks/run.py --case values` executes 5,000,000 state updates through
a by-value function and checks final state and step count against an independent
Python oracle. A corresponding C implementation uses the same algorithm and a
native by-value struct. Both produce `1901417813` and `5000000`.

Local medians (seven samples after warmup, `-O3`): Awl **23.730 ms**, C **23.534 ms**,
ratio **1.008×**. See `benchmarks/values-baseline-0.3.0.json` for those raw samples. The kernel is
mathematically bounded, so the unchecked C baseline does not overflow.

Process startup is included. Cores/frequencies are not pinned, order is not
randomized, and only one small loop-carried scalar recurrence is measured. This
can catch obvious abstraction overhead on this workload; it cannot establish
language-wide performance parity, SIMD/GPU capability, or cross-platform results.

## Next gates

At 0.3, remaining M1 included more scalar widths, exhaustive tagged unions/match,
full-expression source spans, broader fuzzing, and actual cross-platform CI results.
Owned allocations, borrowing, ownership-aware MIR and modules remain M2 work.
