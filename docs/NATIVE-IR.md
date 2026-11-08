# Native IR verification and C emission — 0.7 components

> The complete [Linux native bundle](NATIVE-BUNDLE.md) now implements build/run.
> The component-only commands below do not install its bundled backend resources.

## Current capability and remaining gate

Native `kcc` now scans, parses, checks, independently verifies and emits C11 without invoking Python or another program:

```sh
# Contributor build; requires Python and a C++20 toolchain on the builder.
python3 compiler/build_native.py --standalone --static

compiler/native/bin/kcc check examples/results.aw
compiler/native/bin/kcc emit-checked-ast examples/results.aw
PATH=/no-development-tools compiler/native/bin/kcc emit-c examples/results.aw > results.c
```

The component-only build above does not install the backend resources. The full Linux engineering bundle now supports native build/run with shipped Zig/LLVM/musl; it never falls back to host compilers. The historical component tests described below use a contributor C toolchain; separate bundle tests exercise the shipped backend.

## Backend boundary

Implementation: `compiler/native/kverify.inc`, `kemit.inc`, `kparse.h`.

`Awl_check_unit` performs the frontend analysis and writes types/local symbols. `Awl_verify_unit` independently checks the resulting arena. It neither calls the semantic checker, trusts its checked flag, repairs annotations, nor caches a successful result. Its analysis uses a const arena; the API wrapper may publish rejection diagnostics and invalidate diagnostic JSON, but does not change nodes.

Every `Awl_emit_c` call enters the verifier again before traversing the program or producing output. Reusing an internal emitter object also rechecks the current arena. Earlier success is not a capability that survives arbitrary IR changes. Backend implementations must preserve this boundary.

C ABI status: 0 accepted/emitted, 1 diagnosed, 2 argument/internal failure. Verification rejection is E500. Emission-budget rejection is E501. Native CLI treats backend/verifier failure as compiler failure (exit 2), rather than silently regenerating annotations. Existing source diagnostics are preserved. Output strings are owned by the unit until the next corresponding export/emission or free. Handles require valid caller memory and are not a sandbox for arbitrary native pointers.

## Accepted representation

The current format remains `KAST-arena-v1`: an internal structured value-language tree, **not** ownership MIR, stable interchange format, external ABI, or serialized KIR0. There is no untrusted serialized-IR loader in this increment.

Verifier requirements include:

- Reachable roots are declarations; every child reference points backward to a valid node. Reachable nodes cannot be shared or repeated. Synthetic `#list` nodes preserve list grouping without counting as semantic nesting levels.
- At most 100,000 reachable semantic nodes, depth 64, 200,002 stored nodes, 1 MiB source and 100,001 token records including EOF. Edge and string budgets are checked before traversal expansion. Token/map references must be in bounds.
- Valid identifier spelling, declaration and field uniqueness, exact value representations, child arities, permitted annotation locations and literal signedness/ranges. Decimal integer payloads are canonical, with no leading zeros or negative zero.
- Reconstructed declaration signatures, aggregate dependencies, finite layouts, size/alignment estimates and nesting budgets. These estimates are not an exported ABI.
- Globally unique binding symbols, scoped name resolution, matching use/assignment symbols, valid call/constructor arguments, field projections and local-rooted stores.
- Independently derived expression types matching stored annotations; exact-width operators/conversions; boolean conditions; exhaustive, unique union cases and correctly typed pattern bindings; definite returns and unreachable-statement rejection.

Backends traverse roots and reachable children only. Unreachable storage is not emitted or treated as validated program content. The verifier checks well-formedness, not equivalence to source, optimizer correctness, ownership safety or memory-safety soundness. A future transform must rerun it, but passing it alone does not prove that transform correct.

## Transitional C11 backend

The native emitter implements the existing bootstrap semantics: checked fixed-width arithmetic and conversions, scalar printing, value structs, tagged unions, functions, locals, control flow and exhaustive statement matches. It explicitly sequences operand/argument evaluation, preserves boolean short-circuiting, snapshots aggregate values and defensively traps invalid union tags.

Its C runtime helper text is checked-in data embedded in the executable (`kruntime.inc`). `compiler/generate_runtime.py` is a contributor-only generator from the reference runtime templates; `--check` detects drift. Neither that generator, the Python reference, a runtime template file nor the optional shared library is loaded by native `kcc`. Only required integer helpers are emitted. Aggregate declaration order and temporary naming are deterministic. Total C output is bounded to 64 MiB.

Porting emission to C++ removes Python from this phase; it does not improve the generated machine code by itself. Direct Awl-to-LLVM IR emission is not implemented. The subsequent Linux bundle now ships this route using pinned Zig/LLVM/musl; see NATIVE-BUNDLE.md.

## Validation and measurements

- **248 distinct test methods** pass in each of the reference, native-lexer/parser, and native-semantic-frontend regression configurations. These are repeated configurations, not 744 distinct tests. Explicit reference cases and bootstrap CLI subprocess tests remain reference/bootstrap paths.
- Standalone ASan/UBSan runs pass: 10,000 scanner raw-byte inputs; 10,000 frontend raw-byte inputs and 10,000 source mutations; **45 targeted IR corruptions and 10,000 seeded structural corruptions**. Corruption tests inspect private arenas in a test-only translation unit; production exports no mutation backdoor. The tests verify read-only rejection and stale-verification rejection at emission.
- Eight new emitter test methods include byte-identical C versus the reference for examples, exact-width operations/conversions, forward aggregate layouts and generated expressions. Two hundred generated integer/boolean expressions match their value oracle at O0/O3; sequencing and short-circuit tests also pass at both levels.
- Native-emitted C passes the ASan/UBSan integer matrix: **348 checks across all 64 conversion type pairs**. This test uses a host C compiler and is not the Awl-only installation test.

Evidence: [frontend-validation.json](../tests/frontend-validation.json), `native-verifier-sanitizer.txt`, `native-emitter-parity.txt`, `native-integer-sanitizer-matrix.json` under `tests/`.

[Benchmark samples and build hashes](../benchmarks/native-frontend-latest.json) cover one synthetic 3,000-local, 60,814-byte input. Both check paths now include their independent verifiers; C-emission timing also records output materialization. Internal traversals and representations differ; the reference repeats verification at compile and emit entry. CPU/cache conditions are uncontrolled and the library/executable optimization flags differ. The previous pre-verifier measurements are retained separately. No full native executable-build speedup or generated-program performance improvement is claimed.

## Subsequent bundle integration

Pinned native codegen/linking/runtime resources and Linux native build/run are
now integrated; the offline clean-root acceptance test passes. See
[NATIVE-BUNDLE.md](NATIVE-BUNDLE.md) for that increment, final-bundle evidence,
license/provenance, full-build measurements and remaining compatibility/hardening
work. The 248-method component results above predate the nine bundle tests;
current full runs contain 257 methods. No ownership/security proof is implied.
