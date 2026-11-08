# Native frontend/C-emitter preview — 0.7 work in progress

Latest increment: [complete Linux native engineering bundle](NATIVE-BUNDLE.md).
The component build below is not the complete distribution.

The component-only build below checks/emits C but lacks backend resources. The complete 0.7 Linux engineering bundle now supports build/run using shipped native tools and passes the offline clean-root test. A component executable without those resources fails rather than falling back to Python/system compilers.

## Implemented

The C++20 executable owns the whole current frontend:

- strict whole-source UTF-8 scanning, token/identifier/literal budgets and lexical diagnostic priority;
- arena parsing, precedence, bounded recursion and multi-error syntax recovery;
- declaration/local resolution, exact-width integer types and literal bounds, argument checks, field access and local-rooted stores;
- value-layout size/alignment estimates, recursive-layout rejection, tagged-union constructors, exhaustive matches and pattern bindings;
- scoped locals, definite returns and unreachable-statement checks;
- structured JSON diagnostics and syntax/checked-arena export;
- independent read-only arena verification and a guarded native C11 emitter.

Syntax and semantic annotations remain in native-owned memory. The standalone path does **not** serialize into Python, load the optional frontend shared library, spawn an interpreter/compiler, or download tools. JSON and generated C are exported only on request.

The typed arena is still the value-only bootstrap representation, not ownership MIR. This is not a borrow checker, ABI specification, safety proof or optimizer. The new independent native IR verifier checks internal well-formedness, not source equivalence or ownership safety.

## Contributor build and use

Contributors currently need Python and a GCC/Clang-compatible C++20 toolchain to build the preview. These are build dependencies, not dependencies of the resulting static executable. This source-tree build is **not** the eventual end-user installation flow.

Locally validated on Linux x86-64 with GCC 14.2:

```sh
python3 compiler/build_native.py --standalone --static
compiler/native/bin/kcc --version
compiler/native/bin/kcc check examples/integers.aw
compiler/native/bin/kcc check tests/diagnostics/type.aw --diagnostic-format json
compiler/native/bin/kcc emit-checked-ast examples/results.aw
compiler/native/bin/kcc emit-c examples/results.aw > results.c
PATH=/no-development-tools compiler/native/bin/kcc check examples/hello.aw
```

`emit-ast` skips semantic checking. `emit-checked-ast` checks and independently verifies first. `emit-c` emits verified C11, not machine code. Both export `KAST-arena-v1`, **not** serialized KIR0. The latter adds inferred expression types and resolved local symbols. Input is capped at 1 MiB; the driver bounds file reads too. Source rejection exits 1; unsupported commands/internal failures exit 2. Successful checks exit 0.

`readelf` found no ELF interpreter or dynamic section in this host's static executable. Example checks succeeded with an empty development-tool PATH. This is useful frontend evidence, **not** a clean-machine/offline compile-and-run acceptance test. No native Windows/Clang execution is claimed. CI is configured for those builds but has not run here. This static host build does not establish a final Linux kernel/libc compatibility baseline.

## Validation

Reproduce with:

```sh
python3 -m unittest discover -s tests -v
KCC_LEXER=native KCC_PARSER=native python3 -m unittest discover -s tests -v
python3 tests/native_frontend_suite.py
python3 compiler/test_native.py --sanitize
python3 benchmarks/native_frontend.py
```

The regression adapter routes default in-process `compile_text` calls through C++ scanning/parsing/checking, hydrates their output for the existing Python IR verifier/emitter, and reuses the tests. Explicit backend selections and Python CLI subprocess tests remain their stated reference/bootstrap paths. That adapter is contributor-only; it is never invoked by the standalone executable.

New tests compare complete typed trees, local symbols and exact diagnostics with the reference; they include 1,000 seeded malformed-source mutations, layout/type errors, lexical budgets, Unicode errors, integer extremes and native CLI checks. Separate parser comparisons include 1,500 seeded mutations. The standalone ASan/UBSan harness exercises parser/checker/verifier/emitter ownership, limits, examples, 10,000 raw-byte inputs and 10,000 source mutations; the existing scanner harness separately tests 10,000 raw-byte inputs. A separate verifier harness rejects 45 targeted and 10,000 seeded structural corruptions without repairing the arena; see NATIVE-IR.md. Passing these finite tests is not a security proof.

Current run counts and logs: [frontend-validation.json](../tests/frontend-validation.json). Historical 0.6 runtime/compiler measurements remain separate.

## Measurement scope

[Native frontend measurements](../benchmarks/native-frontend-latest.json) record raw samples, source/compiler/binary hashes and build flags. The benchmark uses one 3,000-local, 60,814-byte synthetic source. In-process check comparisons now cover scanning/parsing/checking and independent IR verification on both sides. Additional measurements cover C-source emission. The earlier pre-verifier samples are retained separately. Native timing does not materialize Python tokens or export/hydrate JSON.

CLI measurements include startup and file I/O. Both checkers now independently verify IR, but representations and internal traversals differ. C emission is transitional, not executable generation. Sampling order alternates, but CPU frequency/affinity and file caches are uncontrolled. Library and executable optimization flags differ. These results do not measure representative full builds, optimization, linking, generated-program speed, or prove an overall compiler speedup.

## Unicode and distribution

Native Unicode classification is pinned to Unicode 15.1.0 and stored as generated range tables. `compiler/generate_unicode.py` refuses another Unicode version. The installed executable needs neither Python nor Unicode files. A Python reference using a different Unicode database can differ on newly assigned non-ASCII characters; no cross-version parity guarantee is made. Awl identifiers remain ASCII.

The Unicode notice/provenance is under `third-party/`. The subsequent Linux engineering bundle now carries pinned backend/runtime resources and notices and passes its first clean-root test. See NATIVE-BUNDLE.md for packaging status; broader compatibility and production hardening remain open.

## Subsequent distribution integration

The previously listed native distribution work now has a tested Linux engineering
implementation: [NATIVE-BUNDLE.md](NATIVE-BUNDLE.md). This component report is not
its installation guide. Current end-to-end evidence covers 257 methods/configuration,
plus offline clean-root and bundled-codegen oracle tests. Broader host validation,
release hardening and the larger language design remain unfinished.
