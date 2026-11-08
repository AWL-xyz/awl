> **Historical 0.6 report.** Current development now has a standalone native
> parser/checker preview; see [NATIVE-FRONTEND.md](NATIVE-FRONTEND.md). This report's
> stage table and measurements describe the earlier scanner-only bootstrap.
> Neither version meets the Awl-only compile-and-run distribution gate yet.

# KCC 0.6: beginning the native compiler migration

**Implemented:** optional C++20 token scanner, C ABI, Python integration, parity
and sanitizer tests, and compiler-host benchmarks. **Not implemented:** a full
C++ compiler, native parser/checker/MIR, LLVM backend, or self-hosted Awl compiler.
The bootstrap still requires Python. There are no new Awl language constructs
in this release; serialized IR remains `KIR0-structured-v0.5`.

## Does Awl's compiler need to be written in Python?

No. Python was chosen to establish executable syntax, semantics and regression
tests quickly. It is not a language requirement or the intended final critical
path for a high-throughput systems toolchain.

There are two distinct performance questions:

1. **Compiler performance:** how quickly KCC reads, checks, optimizes and builds
   source. Python object allocation and interpreted tree walks can bottleneck this.
2. **Compiled-program performance:** the machine code emitted for a Awl program.
   It does not execute through Python. The current pipeline emits C11 and invokes
   GCC/Clang; code-generation decisions, checks, algorithms and optimization flags
   determine that executable's speed. A poor emitter can produce poor machine code
   in any implementation language.

Moving the frontend to native code can improve compilation throughput. It does
not automatically improve generated code, fix an expensive compiler algorithm,
implement incremental caching, or make optimizations correct. The current C11
backend is also still a bootstrap backend, not the proposed custom optimizing IR.

## Host implementation decision

C++20 is the working native migration target for now: local GCC/Clang-compatible
toolchains are available, RAII and contiguous arenas are suitable for compiler
structures, and future LLVM/Clang integration has direct C++ APIs. Rust would also
be a reasonable native host; it is not inherently too slow for a compiler. This
choice is about implementation/toolchain integration, not a claim that C++ is the
only way to achieve performance.

C++ does not provide Awl's proposed ownership safety automatically. The native
compiler itself processes untrusted source and needs bounded inputs, explicit
ownership, checked indexing, fuzzing, sanitizers and review. No native-code safety
proof or security audit is claimed here.

Self-hosting in Awl is a later option, not a shortcut: Awl currently lacks the
allocation, slices, modules, file APIs and ownership machinery needed for a
practical self-hosted compiler. Maintaining a mature native bootstrap until those
exist is more defensible than pretending self-hosting is already possible.

## Build and use the native lexer

Python 3.10+ is still required for the driver/parser/checker/emitter. The optional
scanner additionally requires a GCC/Clang-compatible C++20 compiler.

```sh
python compiler/build_native.py
# Or: python compiler/build_native.py --cxx clang++
python compiler/kcc.py run examples/integers.aw --lexer native
python compiler/kcc.py check examples/results.aw --lexer native
python -m unittest discover -s tests -v
python compiler/test_native.py --sanitize
python benchmarks/compiler.py
```

To run all existing compiler tests using the native scanner by default:

```sh
# Linux/macOS shell
KCC_LEXER=native python -m unittest discover -s tests -v
```

```powershell
# PowerShell
$env:KCC_LEXER = 'native'
python -m unittest discover -s tests -v
Remove-Item Env:KCC_LEXER
```

`--lexer python` explicitly selects the reference; `--lexer native` explicitly
selects the optional scanner. Otherwise `KCC_LEXER` is consulted, defaulting to
Python. A missing/incompatible native library is an error when selected, never
a silent fallback. `doctor` reports the configured default and library-file
presence; presence is not a successful ABI/load test.

Native libraries are built under `compiler/native/bin/` and excluded from git and
the source release archive. Rebuild on each host. `CXX` or `--cxx` names one C++
compiler executable. Windows builds target MinGW-style GCC/Clang drivers, not
MSVC syntax; runtime dependency directories can come from the local build manifest.
Only Linux/GCC was executed here. Windows/Clang CI is authored, not validated by
local Linux results. macOS file-extension handling is not tested macOS support.

`Awl_LEXER_LIBRARY` can override the library path. It must point to **trusted native
code**, not an untrusted package's arbitrary plugin. ABI version and structure
sizes are checked before use, but that is not a sandbox or authenticity check.
An embedded long-lived Python process must restart after rebuilding a loaded library;
the adapter caches loaded library handles.

## What migrated and what did not

| Stage | Implementation in 0.6 |
|---|---|
| UTF-8 scan, token boundaries, code-point offset tracking | Optional C++20 core |
| Diagnostic formatting, Unicode suffix classification, identifier/literal policies | Python adapter/reference |
| Token object materialization | Python bulk adapter |
| Parser and typed structured IR construction | Python |
| Type/scope/return checks and IR verification | Python |
| C emission and native compiler driver | Python invoking host C compiler |
| Optimization/code generation after C emission | Host GCC/Clang |

`compiler/native/klex.cpp` is working code, not a placeholder native rewrite.
It validates UTF-8, scans ASCII syntax, tracks Unicode code-point positions in
comments, bounds source/token allocation and returns a contiguous array of span
records. It does not itself enforce every Awl lexical policy; the adapter applies
those checks in source order, preserving diagnostic priority and the reference's
Unicode `isalnum` behavior. The scanner accepts arbitrary UTF-8 comments but does
not add Unicode identifiers to Awl.

The C ABI uses fixed-width records and explicit result ownership. Every result
must be freed by the same library before reuse; owned results must not be
shallow-copied. Input pointers must address their declared byte lengths. Python
uses a `finally` block to release each result, including on diagnostic failures.
The scanner library is a compiler dependency only; it is not linked into generated
Awl programs. C++ exceptions are caught at the scan boundary. Arbitrary malicious ABI callers
or corrupted pointers are outside the source-input validation guarantee.

## Measurement-driven correction

The first bridge read every C token field separately through ctypes. On the
60,814-byte synthetic input it measured **20.185 ms** for reference lexing versus
**23.416 ms** for integrated native lexing: the supposed acceleration was slower.
Frontend checking was slower too. Those raw results are retained in
`benchmarks/compiler-bridge-baseline-0.6.0.json`.

The bridge now bulk-decodes the contiguous plain-data record array, then constructs
Python tokens and performs the same lexical policy checks. This avoids repeated
ctypes field access while keeping spans and memory ownership explicit. Native
storage remains alive until conversion finishes; returned Python tokens do not
retain pointers into freed C++ storage.

Latest host measurements: Linux x86-64, GCC/G++ 14.2.0, Python 3.13.16; 3,000 local
declarations, 60,814 bytes, 18,010 tokens including EOF:

| Measurement | Python lexer path | Native lexer path | Reference/native ratio |
|---|---:|---:|---:|
| Integrated lexing | 17.942 ms | 12.068 ms | 1.487× |
| In-process frontend check | 56.010 ms | 46.585 ms | 1.202× |
| CLI check, including startup | 136.755 ms | 121.492 ms | 1.126× |
| CLI native build, including C compilation/linking | 253.552 ms | 251.960 ms | 1.006× |

**The end-to-end build result is essentially unchanged within this noisy test.**
It is not evidence of a meaningful build-speed improvement. Native scanning is
only one stage; Python startup, parsing/checking/emission and host compilation
still contribute. Keeping Python as the default avoids making one synthetic case
a broad release policy and preserves the simplest portable bootstrap.

The isolated C++ scan took about **0.202 ms**, but returns span records rather than
Python Token objects and omits adapter policy work. It is not an apples-to-apples
compiler speedup and must not be advertised as an ~89× faster KCC. The integrated
measurements include encoding, FFI, policy validation and Python token allocation.

Raw samples, flags and C++ source/header hashes are in
`benchmarks/compiler-latest.json`. In-process runs exclude initial library loading;
CLI runs include startup and loading. The dataset uses unused locals, which the C
backend optimizes away. CPU affinity/frequency are uncontrolled, measurement order
is fixed, and samples are small. These measurements do not cover representative
large builds, incremental compilation, peak memory, optimization-heavy programs
or compiled Awl execution speed.

## Validation

- **213 unittest methods passed locally** with the reference default, and the same
  **213 passed again** with `KCC_LEXER=native`. This is two runs of one suite,
  not 426 distinct tests.
- The 196 previous tests still cover language semantics/native execution. Seventeen
  new methods cover ABI ownership, limits, diagnostic priority, UTF-8/offsets,
  concurrent independent results, error fixtures, CLI selection and 2,000 seeded
  randomized scanner parity inputs. Tokens, typed IR and diagnostics are compared.
- A standalone C++ harness passed under ASan/UBSan, including boundary/UTF-8/ownership
  checks and 10,000 raw-byte inputs. This instruments the compiler scanner itself;
  it is distinct from sanitizing generated Awl programs.
- Existing source-mutation/expression/match tests remain. Seeded random cases are
  smoke coverage, not coverage-guided fuzzing, a soundness proof or a security audit.
- With no optional library built, the 17 native-specific methods skip explicitly;
  the reference compiler remains usable. CI builds it first before both suite runs.

Evidence: `tests/latest.txt`, `tests/native-suite.txt`,
`tests/native-lexer-sanitizer.txt`, `tests/validation.json`.

## Native migration sequence — proposed beyond this release

1. **Delivered:** native scanning and a bulk bridge, reference parity and host timing.
2. Native parser with native token arrays and arena-backed syntax/IR IDs. Test
   whole syntax trees against the reference. Do not bounce every AST node through
   Python and expect the scanner's isolated throughput to survive.
3. Native resolution/type checking and resource-aware MIR with explicit verifiers;
   keep diagnostics and negative tests in parity. Move the whole check pipeline
   behind a native driver before removing Python from the compiler's critical path.
4. Native C emission/driver can eliminate the Python compiler dependency even before
   LLVM exists. Add LLVM independently after a validated native frontend baseline.
5. Ownership/borrowing, modules/separate compilation and incremental queries proceed
   with their existing release gates. A native host does not mean these are done.
6. Consider self-hosting only after Awl's own core facilities and bootstrap
   reproducibility are sufficient. Freeze/retire the Python reference deliberately;
   do not maintain two expanding language definitions indefinitely.

This is a staged engineering decision, not a completed production compiler rewrite.
