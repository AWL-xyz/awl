# Compact fixed-array construction — 0.9.1-dev

Native filesystem projects now accept `[expression; count]`. For example:

```Awl
local pixels:[u32;1024]=[0u32;1024]
local grid:[[i64;4];3]=[[0;4];3]
grid[1][2]=42
```

The seed expression is evaluated **once**, before construction. Its resulting
value is copied into each slot. This is not a per-element generator or a dynamic
allocation. The decimal count must be a literal from1 to1024 (leading zeroes are
normalized); variables, arithmetic expressions, suffixes and zero are rejected.
An omitted local type annotation is still unsupported. Existing `[a,b,c]`
literals retain left-to-right, once-per-expression evaluation. Empty arrays and
trailing commas remain unsupported. Postfix reads like `[7;2][1]` work.

Nested arrays/structs/unions are value copies: changing one row does not change
another row or the seed. Strings retain their existing immutable-region rules.
**Resource descriptors alias:** `[spool_new(16);64]` creates ONE builder,
not64 independent builders. Freeing any alias invalidates the other aliases;
register one deferred release, not one per copy. This feature is not ownership,
borrowing, cloning/destructors, slicing or an allocation-error policy.

The existing type/layout budgets still apply:1024elements,1MiB per value,
64layout height and128canonical type characters. These are not a total stack
budget. Large temporaries/frames/recursion can exhaust the stack. Bounds traps
abort without unwinding deferred releases.

## Architecture and evidence

The parser records one `array_repeat` child and a normalized decimal payload;
it does not expand source/IR into1024children. The checker infers the seed's
value type. The independent read-only verifier separately checks count payload,
arity, inferred type, project-only syntax and layout budgets before C emission.
The emitter evaluates/snapshots the seed before a bounded initialization loop;
all slots are assigned before any read. No C payload is emitted from unverified
count text. Large input/output objects can still require by-value copies.

`tests/test_repeat.py`:8methods cover once-only effects, nested independence,
all1024slots, structs/unions/strings/bools/integer widths, resource aliases,
modules/parameters/returns, malformed counts, type/layout budgets, deterministic
bounded C and the example.14new private verifier corruptions bring the total
to182; ASan/UBSan and full regressions are recorded in `repeat-*-suite.txt`,
`repeat-*-sanitized.txt` and `repeat-validation.json`. Windows cross-link is
not Windows runtime acceptance; remote CI remains unexecuted.

Seven alternating warm builds compare an explicit1024element literal against
`[7;1024]`, both summing to7168: median full builds55.747/52.919ms;
whole-process runtime0.369/0.488ms. These tiny startup-dominated measurements
show a trade-off, NOT a general speedup or zero-cost guarantee. See
`benchmarks/repeat-latest.json` for samples and scope.

Accepted planning credit, conditional on final distribution acceptance:
core-language maturity38→39.5 at the unchanged20-point weight, +0.30points;
15.45→15.75 (~15.8%). This is a subjective planning judgement for compact
construction/evaluation/copy contracts and validation, not measured universal
completeness. No dynamic-container or ownership credit is awarded.
