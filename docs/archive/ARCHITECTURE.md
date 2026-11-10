# Awl architecture specification — draft 0.7

**Status:** proposed architecture except where explicitly marked implemented.
Awl is the language, `awl` its public SDK command, `.aw` its source suffix, `.awproj` its project suffix, and `kcc` internal compiler tooling. This specification is a design baseline, not a claim of soundness or
production readiness. No general Rust-style borrow checker, GPU backend, installed Package resolver, direct LLVM IR backend or C++ bridge is claimed, bounded resource ownership/borrow checks and the bundled LLVM/Clang backend are distinct implemented subsets.

## 0. Mandatory native distribution contract

The shipped product must let users unpack **Awl only** on a supported Linux host
and compile `.aw` programs immediately. Installed compiler commands must not require
or invoke Python or separately installed GCC/Clang, linkers, SDKs, headers or
other development packages. Required native backend/linker/runtime/startup/sysroot
resources must be included in the Awl distribution. No implicit tool downloads.
Baseline OS/CPU and system-library assumptions must be declared and tested.

The Linux x86-64 engineering bundle now implements this workflow and passes a
network-disabled, unprivileged clean-root acceptance test on kernel 6.1.189:
[NATIVE-BUNDLE.md](NATIVE-BUNDLE.md). It ships static C++ KCC, Zig 0.15.2 with
LLVM/Clang/LLD 20.1.2, libc/startup/header resources and notices. Its C11 backend is
transitional; direct Awl-to-LLVM IR and Awl self-hosting are not implemented.
Python remains a contributor reference, never part of the installed compile path.
This is not blanket Linux/Windows compatibility, production readiness or a safety
proof. Broader platform validation, hardening and release signing remain open.

## 1. Design thesis: explicit resources, simple surface

Awl's organizing abstraction is a **resource region**: a lexical ownership domain
that can include ordinary memory, scoped tasks, and device allocations. Ownership
and access permissions are static; placement and execution strategy are separate
from program meaning. The same computation can have portable and specialized
implementations only if they satisfy one interface's semantic contract.

This is not a claim to a novel underlying type theory. The distinctive engineering
choice is to unify resource lifetime, structured parallelism, and device transfer
under one region model, rather than adding three unrelated safety mechanisms.
The cost is a more demanding compiler and occasional explicit staging of data.

Priorities, in order: defined behavior in safe code; inspectable costs and native
control; readable syntax; scalable separate builds; optimizations with evidence.
"Zero-cost" means no compulsory allocation, dispatch, reference counting, or
scheduler for an abstraction that does not need it. It does not mean safety checks,
synchronization, transfers, or task creation are free.

## 2. Surface language and semantics

### Implemented bootstrap grammar

```
program  := (structure | union | function)*
structure := 'struct' identifier (identifier ':' type ';'?)+ 'end'
function := 'function' identifier '(' params? ')' '->' type block 'end'
params   := identifier ':' type (',' identifier ':' type)*
union    := 'union' identifier variant+ 'end'
variant  := identifier '(' (identifier ':' type (',' identifier ':' type)*)? ')'
integer  := 'i8' | 'i16' | 'i32' | 'i64' | 'u8' | 'u16' | 'u32' | 'u64'
type     := integer | 'bool' | 'unit' | aggregate-name
stmt     := 'local' identifier ':' type '=' expr
          | place '=' expr
          | 'return' expr
          | 'if' expr 'then' block ('else' block)? 'end'
          | 'while' expr 'do' block 'end'
          | 'match' expr 'then' case+ 'end'
          | expr
case     := 'case' union-name '.' variant-name '(' bindings? ')' 'then' block
bindings := identifier (',' identifier)*
block    := (';' | stmt)*
```

Expressions: signed/unsigned decimal integer and boolean literals, names,
function/constructor calls, checked integer conversions, dotted field selections,
parentheses, unary `-`/`not`, and binary `* / % + - < > <= >= == != and or`.
Binary precedence is listed highest to lowest; field selection binds more tightly
than unary operators, which bind more tightly than binary operators;
binary operators associate left. Comments start with `--`. Semicolons are optional
separators; newlines are whitespace. There are no strings or pointers yet. KCC 0.3 adds nominal value structs and
checked u64; [VALUES.md](VALUES.md) specifies their exact semantics and limits.
KCC 0.4 adds finite tagged unions and exhaustive statement matching;
[UNIONS.md](UNIONS.md) specifies syntax, semantics, lowering and restrictions.
KCC 0.5 adds all eight fixed-width integer types and checked conversion syntax;
[INTEGERS.md](INTEGERS.md) specifies exact semantics and backend guards.

- Names resolve lexically. A local's initializer sees the outer binding; a new
  local may shadow an outer binding, but not another local in its own block.
  Function parameters form an outer scope relative to the function body.
- Locals require initialization and explicit type annotations. They are mutable
  value slots; parameters can be reassigned as local copies.
- No implicit truthiness, scalar coercion, or implicit return. Non-unit functions
  must return along every statically recognized path. Loops are conservatively
  treated as potentially terminating, even `while true`.
- Functions may call later definitions and recurse. No closures or overloading.
- Operands and call arguments evaluate left to right. `and`/`or` short circuit.
- Integer arithmetic at every supported width is checked at **every** optimization level. Overflow, division
  by zero, and MIN/-1 division or remainder trap by terminating the process.
  Division truncates toward zero; remainder has the dividend's sign.
- Unsuffixed positive literals must be in 0..9223372036854775807. KCC 0.2 also accepts
  `-9223372036854775808` directly and emits `INT64_MIN`; its positive magnitude
  is invalid on its own. Negating the minimum again traps.
- `print(integer|bool) -> unit` is the only builtin. Unit functions may fall through or
  `return` a unit expression; bare `return` is not in the bootstrap grammar.
- Entry point: `function main() -> i64`. Its low eight return bits become the
  host process exit code. Printing uses the platform C library.
- The bootstrap rejects unreachable statements after a statically total return.

### Proposed full language (not accepted by this compiler)

Keep `local`, `function`, `then`, `end`, no braces for blocks, no hidden truthiness,
and no semicolon requirement. Extend the current structures, tagged unions and fixed-width integers with
`usize`, IEEE floats, arrays, slices,
references, function values, traits, and generics. `local` remains a mutable slot;
mutation of owned data requires exclusive permission, independent of whether a
slot is mutable. `let` is deliberately not added as a second local declaration.

```
-- Illustrative proposed syntax, NOT runnable in the 0.5 bootstrap
module image.filter
import <Awl/slice> { Slice }
import "./weights.aw" as weights

function scale(dst: &mut [f32], src: &[f32], gain: f32) -> Result[unit, ShapeError]
    if dst.len() != src.len() then
        return Err(ShapeError())
    end
    for i in 0 .. src.len() do
        dst[i] = src[i] * gain
    end
    return Ok(unit)
end
```

Range bounds are half-open. Safe indexing checks bounds unless a proof eliminates
them. Integer overflow remains checked; named `wrapping_*`, `saturating_*`, and
`checked_*` operations expose alternatives. Float reassociation, NaN assumptions,
and fused operations require an explicit numerical contract, not global unsafe
"fast math." OOM is a typed allocation error in fallible APIs; an explicitly
infallible allocator may abort. No implicit exceptions or cross-FFI unwinding.
Errors use tagged `Result[T,E]` with a future propagation operator; traps are not
recoverable error handling. Drops are deterministic; abort does not run drops.

## 3. Ownership and safety model — proposed

### Rules

A place is a local, field projection, or indexed element. Each resource has one
owner; assignment of non-Copy values moves ownership. Copy is available only to
values whose bitwise duplication cannot duplicate resource obligations. Drop
executes once on each initialized owned value, in reverse initialization order.
Partial initialization and partial moves require per-field state tracking.
Self-referential movable values are rejected; a future pin abstraction must be
explicit rather than inferred.

`&T` is a shared read loan; `&mut T` is an exclusive loan. For overlapping places,
any number of reads OR exactly one write is permitted, never both. Reborrowing
suspends the parent permission until the child expires. Shared aliases cannot
mutate absent explicit synchronization/interior-mutability types. Disjoint field
projections may borrow independently; general index disjointness requires a
checked `split_at_mut`, not speculative alias reasoning.

A reference's lifetime must be contained within its resource's live interval.
The checker computes non-lexical loan liveness on the CFG and solves region
inclusion constraints. A returned reference must trace to a compatible input
region or static storage. Public interfaces specify region relationships when
elision would be ambiguous. No lifetime names are required for unambiguous local
borrows. Async frames and closures preserve these obligations after capture.

CFG state: per-place initialized/moved state plus active loans and provenance.
At joins, an owner is usable only if initialized on all incoming paths; possible
loans are conservatively unioned. Loop fixed points must converge. Drop elaboration
comes after ownership checking and before machine lowering. Optimization may not
invent alias privileges or extend a loan across a conflicting access.

### Concurrency

`Send` means ownership may transfer to another thread; `Sync` means shared loans
may cross threads. Derive structurally with explicit exclusions for raw pointers,
thread-affine resources, and unsynchronized mutable cells. An owning smart pointer
is not automatically Sync. Atomics use a documented C11-like memory ordering model;
data races in safe Awl are forbidden by the type system and library contracts.
Device handles may be Send but thread-affine driver contexts must not be.

A `scope` owns child tasks and does not exit until every child has completed or
cancelled and joined. Cancellation is cooperative, never arbitrary stack
termination. Borrowed captures are valid only while the enclosing scope is live.
Detached work requires owned Send + static captures and an explicit supervisor.
Async tasks are stackless state machines; suspension may not retain a temporary
borrow with insufficient lifetime. Holding a lock across suspension is rejected
for guard types marked non-suspendable; this is not a general deadlock proof.

### Unsafe boundary and proof limits

Raw pointers, unchecked indexing, allocator internals, FFI and device driver
calls require `unsafe` blocks with stated obligations. Unsafe cannot disable
arithmetic rules elsewhere. Pointer provenance must be specified before raw
pointer optimizations ship; C pointer rules are not automatically Awl's rules.
Safe wrappers must validate lengths, alignment, lifetimes, initialization, ABI,
and synchronization. Static checking does not prove freedom from deadlocks,
logical races, leaks from intentional cycles, stack exhaustion, or timing attacks.

The current scalar/struct/tagged-union implementation has **none of this ownership machinery**.
It avoids exposing user-addressable memory, but recursion can exhaust the stack,
and the compiler has not undergone a soundness audit.

## 4. Modules, imports, separate compilation, ABI — proposed

Imports resemble C/C++ path selection, but are semantic dependencies, not textual
inclusion. No macros leak through headers, no include-order-dependent definitions.

```
module net.http
import <Awl/net>                       -- package search roots
import <math/vec> { Vec3, dot as inner } -- selective binding
import "./codec.aw" as codec             -- package-relative path
extern "C" import "zlib.h" as z         -- generated, audited interface
```

Only explicit `pub` exports enter an interface. One canonical module identity
(package instance + normalized path); path aliases cannot duplicate types. Type-only
cycles may be resolved as a group; initialization cycles and compile-time execution
cycles are errors. Avoid dynamic module initialization initially: constants only,
explicit initialization functions for resources.

KCC emits target-independent public type/region/effect summaries and target-tagged
layout metadata in versioned `.kmi` interfaces, plus `.o`/`.obj`. Dependency and
compiler hashes invalidate caches. Generic bodies needed downstream are serialized
as checked IR, not arbitrary source text. Monomorphizations get content-based
identities and link-once emission where ABI supports it. Linkage names encode
package identity, canonical type arguments, and ABI epoch. No stable Awl ABI in
0.x; stable C ABI is the interoperability escape hatch.

`extern "C"` accepts ABI-safe scalar types, pointers, and explicitly `repr(C)`
layouts. No slices, owning strings, traits, or implicit unwinding across the ABI.
A slice crosses C as pointer + length only through an explicit wrapper. Each
binding has nullability, ownership, callback lifetime, thread and failure contracts;
header parsing alone cannot recover them. Platform calling conventions must be
selected explicitly on 32-bit Windows. `long`, `wchar_t`, enums, packing, and bitfields
must follow the target, not compiler-host assumptions.

C++ integration is **two-tier**, not a promise of universal direct ABI support:
1. Generated C-linkage shims for an explicitly supported C++ subset; constructors,
   destructors, exceptions (caught and converted to errors), and templates instantiated
   in the C++ toolchain. Opaque owned handles preserve RAII with explicit deleters.
2. Optional direct ABI bridges tied to exact Clang/MSVC ABI/toolchain versions.
   No mixing incompatible standard-library objects or compiler runtime ownership.

Linux uses ELF/System V where applicable; Windows uses COFF, Win64 ABI, import
libraries and DLL export control. Allocations must be freed by the allocating
runtime across DLL boundaries. C++ polymorphism and templates cannot be made
"seamless" by simply declaring `extern` functions.

## 5. Compiler and intermediate representations

### Implemented native engineering pipeline

C++ scanner → arena parser → resolution/type/layout/control-flow checks →
independent read-only native arena verifier → sequenced C11 emission →
**bundled** Zig 0.15.2 / LLVM-Clang-LLD 20.1.2 / musl startup/runtime → static
Linux x86-64 executable. No host development tools or Python are invoked.

The native arena exports `KAST-arena-v1`; it is not SSA, ownership MIR, a stable
module format or an external ABI. Every emission re-verifies it. Arithmetic uses
checked helpers; operands are sequenced despite C argument evaluation rules.
KCC has no custom vectorizer/PGO; optimization comes from its bundled native
backend. CPU target is baseline, not `-march=native`. `-O0..3` does not change
source arithmetic semantics. Build/run driver staging and toolchain/provenance
are documented in [NATIVE-BUNDLE.md](NATIVE-BUNDLE.md).

The separate Python contributor reference can still export typed structured
`KIR0-structured-v0.5`, emit C and invoke a host C compiler. It is not installed
in the native bundle. Its scanner/parser bridges are regression tools, not the
product execution path. [NATIVE-COMPILER.md](NATIVE-COMPILER.md) retains the earlier
0.6 migration history. Direct Awl-to-LLVM IR emission and self-hosting remain
future work; they are not prerequisites for the now-tested native-only workflow.

### Planned production stages

1. Lossless syntax tree and stable source maps; incremental query-based frontend.
2. HIR: resolved modules, typed generics, explicit effects and region relationships.
3. Ownership MIR: CFG, places, moves, borrows, suspend points, drop obligations.
4. **KIR-R**: verified resource IR retaining address spaces, regions, task scopes,
   transfer events, alias permissions, and numerical contracts.
5. KIR-S: typed SSA for scalar/vector/loop optimization with explicit memory effects
   and trap ordering. Verify dominance, type consistency, effect order and address
   spaces after every transformation in debug compiler builds.
6. LLVM CPU lowering and target-specific GPU lowering. CPU backends first for
   x86-64 and AArch64; debug info, unwind tables where needed, object emission.

Keep resource semantics until heterogeneous scheduling and bounds/alias analyses
have run. Prematurely converting every buffer to `i8*` would lose the information
needed to prove transfers and launches safe. Conversely, retaining high-level
abstractions all the way to instruction selection would make backend maintenance
unmanageable. KIR-R → KIR-S is the intentional boundary.

Compiler optimizations include monomorphization, devirtualization, inlining,
scalar replacement, loop-invariant motion, bounds-check elimination using range
proofs, alias-aware vectorization, and target instruction selection. Traps and
observable side effects cannot be reordered as though arithmetic were undefined.
A verifier and differential execution precede aggressive optimizations. Escape
analysis can remove allocations, but cannot change observable drop order.

## 6. Metaprogramming — proposed

- `comptime` expressions execute a deterministic, typed bytecode interpreter.
  No native host execution, filesystem, network, clocks, or ambient environment.
- Reflection sees declared type structure and permitted public declarations; it
  cannot bypass module privacy or manufacture reference permissions.
- Hygienic typed syntax builders produce declarations with origin/source traces,
  then re-enter type, ownership, and effect checking. Generated code has no safety
  exemption. Avoid unrestricted token rewriting and textual preprocessor macros.
- Fuel, memory and recursion quotas prevent accidental nontermination from hanging
  a build. Exhaustion is a diagnostic, not a change in resulting program behavior.
- Compile-time arithmetic and layout queries use **target** widths and ABI, not
  host Python or host C semantics. Effects enter cache keys explicitly.
- Generics are constrained and monomorphized by default; explicit dynamic trait
  dispatch is available when code size matters. A body is checked abstractly and
  specialized instances are revalidated for layout and target restrictions.
- Specialization is limited to coherent, ordered cases with a unique best match;
  overlapping incomparable implementations are rejected. Hardware specialization
  is distinct from type specialization and must preserve fallback semantics.

Trade-off: no ambient I/O makes macros less convenient. Explicit build generators
can perform I/O in a separately sandboxed build step with declared inputs. This
preserves reproducible and remote builds and avoids treating packages as trusted
compiler plugins.

## 7. CPU/GPU hardware architecture — proposed

### CPU multiversioning

Always ship a documented baseline variant. Optional variants carry required ISA,
OS context support, numerical contract and ABI identity. An x86 resolver must check
CPUID **and** OSXSAVE/XGETBV state before choosing AVX/AVX2/AVX-512; CPU vendor alone
is insufficient. Similar OS-provided capability discovery applies to AArch64.
Resolve once per process or explicitly managed execution domain, cache a function
pointer, and allow an override to disable optional variants for testing. Avoid
assuming that every processor in a heterogeneous or virtualized system shares the
same capabilities. Use the OS-supported process-wide set or restrict affinity
before using a narrower variant. Unknown hardware uses the baseline.

Variant ranking accounts for workload size, frequency throttling, transfer cost,
and measured tuning data; "widest SIMD wins" is not a correct policy. Bounds and
integer behavior remain identical; floating point variants must conform to their
selected contract. Runtime discovery is advisory for performance, not permission
to alter results. Hardware names from `doctor` today are informational only.

### Device backends

- NVIDIA: NVPTX/PTX plus optional architecture-specific cubins, CUDA driver adapter.
- AMD: AMDGPU/HSACO through a pinned supported ROCm/HSA stack.
- Intel: SPIR-V through Level Zero where supported; device capability validation.

These are backend plans, not present capabilities. OS/device/driver support varies;
first-class Windows does not mean every Linux device backend works there. Publish
an exact validated driver/device/OS matrix before release, and return a typed
Unavailable/Unsupported error where a driver is absent. No silent CPU fallback
for an explicitly device-only kernel.

A `device function` subset excludes arbitrary host pointers, blocking host syscalls,
unbounded recursion, host allocators, and cross-device references. Kernel interfaces
carry dimensional bounds and address spaces. A portable kernel must satisfy all
selected device limits or provide constrained variants. Validate launch dimensions,
shared memory, subgroup assumptions and argument layout on the host before launch.

Owned device buffers belong to an execution region. A submitted event temporarily
borrows its input buffers and exclusively borrows writable outputs until completion.
Event completion returns permissions; buffer drop waits or is explicitly deferred
inside the owning scope. Unified virtual memory does not waive synchronization.
Unknown device-side aliasing or unsafe kernels require an unsafe contract.
Initially reject cross-workgroup writable sharing without explicit atomics; full
race freedom for arbitrary GPU kernels is not claimed.

Automatic placement applies only to pure/data-parallel functions with CPU fallback
and matching semantics. Runtime choice uses calibrated launch/transfer overhead,
problem size and residency. Failure before work begins may use fallback; failure
after partial side effects must surface an error, not rerun a kernel and duplicate
effects. Device loss and asynchronous errors remain observable typed failures.

## 8. Standard library, runtime, parallelism — proposed

Layer the ecosystem so bare-metal users do not link a scheduler by accident:

| Layer | Contents | Allocation/OS dependency |
|---|---|---|
| `Awl.core` | integers, traits, Option/Result, slices, atomics | none |
| `Awl.alloc` | Vec, String, Box, allocator APIs | explicit allocator |
| `Awl.sys` | Linux/Windows handles, memory maps, threads | OS |
| `Awl.std` | files, collections, networking, clocks | OS + allocator |
| `Awl.task` | scoped fork/join, async executor, cancellation | opt-in runtime |
| `Awl.compute` | device discovery, buffers, events, kernels | optional drivers |

The current bootstrap has scalar builtin types, by-value structs, tagged unions and `print`,
backed by libc. There is no separate standard-library package yet.

Use a work-stealing CPU executor with scoped local queues for CPU tasks, and
reactor-based I/O (epoll/io_uring as supported on Linux, IOCP on Windows).
Blocking operations go to a bounded separate pool. Async futures are lazy state
machines; no heap allocation for every await is required, though spawning an
independent task generally allocates a frame. Task counts and nested parallelism
must be bounded to avoid oversubscription. Avoid mandatory tracing GC.

Determinism requires a separate reduction order contract; parallel float reduction
is not silently substituted for a serial fold. Cancellation, completion ordering,
and resource cleanup have specified behavior. Expose hardware placement and manual
transfer control for expert users; automatic scheduling is not always optimal.

## 9. Build, package, and development ecosystem — proposed

`kbuild` reads `Awl.toml`; `kpkg` resolves packages and writes `Awl.lock` with exact
versions and content hashes. No manifest or resolver implementation exists yet.
Dependencies may be registry, workspace, or pinned git revisions. Feature resolution
must be deterministic; target predicates evaluated against a declared target,
not the build machine. Cross compilation separates host build tools from target
artifacts. Cache key: compiler/ABI epoch, source, resolved deps, target triple,
CPU feature set, numerical mode, interface hashes, and declared generator inputs.

Native dependencies record include roots, C/C++ compiler and ABI, link mode,
system libraries and runtime requirements. A package cannot inject arbitrary
compiler flags into dependents. Signed provenance is a goal, but signatures do
not substitute for sandboxing build code. Registry policy, naming and license
handling need separate governance before public publishing.

`kcc` coordinates check/build/link; `kfmt`, `klint`, and a language server share the
parser and typed queries. Plan completion, definition/reference navigation,
borrow explanations, rename, and diagnostics with source spans. `kdoc` documents
public contracts and runnable examples. Debug builds expose DWARF/PDB mappings to
LLDB/GDB/WinDbg as backend support allows. A target-aware test runner supports
unit, compile-fail, integration, property and device tests. No claims that these
tools already exist.

PGO pipeline: instrument native variants → representative workload suite → merge
profiles keyed to IR/build identity → rebuild → validate against unprofiled output.
LTO requires compatible backend/toolchain versions across participating objects;
foreign libraries can remain opaque. SIMD annotations are contracts or requests,
never authorization for out-of-bounds loads. Ship optimization remarks explaining
why loops vectorized or did not. Benchmark latency, throughput, binary size,
compile time, peak memory and energy where measurable, not only best-case kernels.

## 10. Engineering decisions and rejected shortcuts

| Decision | Rationale | Cost/alternative |
|---|---|---|
| C11 bootstrap | Deliver observable native behavior early | No precise Awl alias ABI, limited debug mapping; replace incrementally |
| Checked arithmetic always | Optimization-independent semantics | Checks can inhibit vectorization; prove or choose explicit wrapping |
| Ownership before SSA | Preserve source-level resource reasoning | Two IR families and verifier maintenance |
| Explicit region/device loans | Prevent premature release during async execution | More visible synchronization and conservative rejections |
| Semantic imports | Stable incremental compilation and no macro leakage | Cannot reuse arbitrary C preprocessor metaprograms directly |
| C shims first for C++ | Toolchain can honor its own ABI/exceptions | Wrapper overhead for some calls; not universal zero-copy integration |
| Baseline + optional variants | Portable artifact with predictable fallback | Larger binaries and more test combinations |
| Deterministic CT interpreter | Reproducible, unprivileged builds | Quotas and restricted build-time APIs |
| Cooperative cancellation | Destructors and loans remain valid | Uncooperative tasks can delay scope exit |

## 11. Safety and validation release gates

Do not label Awl production memory-safe based on a handful of examples. Required:
formal operational semantics for moves/loans/provenance, a small executable model,
a preservation/progress argument for a specified core (with explicit unsafe and FFI
assumptions), negative tests, randomized differential tests, and external review.
LLVM correctness and foreign libraries remain trusted dependencies, not proofs.

Milestones and acceptance criteria are in [ROADMAP.md](ROADMAP.md). Architecture
changes should include a decision record, diagnostic examples, compatibility notes,
and benchmark/test evidence. Performance regressions need explanations, not silent
semantic weakening.
