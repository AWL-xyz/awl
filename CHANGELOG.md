# unreleased mutable borrows and diagnostics

## Aesop source revision, not a published SDK release

- grouped built-ins now use lowercase `namespace.method(...)` names with no underscores, old underscore spellings are rejected, examples, docs, editor and tests are migrated
- numeric types provide `convert`, `isnum` and exact `match` predicates are available, float-to-integer conversions truncate toward zero and saturate, mixed integer/f64 arithmetic remains strict
- leading-k compiler files and legacy example names were renamed, public `kcc` wording was replaced with ACC while the compatibility executable alias remains silent
- current docs, examples and tests were indexed, historical docs/reports were moved to archives, community health files and metadata polish were added

- function results are optional, `func size :: @b values[i64], etc[i64] { ... };` infers its result from the body
- explicit results use `func size[i64] :: ... { ... };`, owned results retain explicit `[@o type]` annotations
- mixed return types and missing return paths are diagnosed, unresolved recursive type dependencies require annotations
- Aesop is the sole native compiler grammar, legacy/Python/prototype frontends are retired, current examples live in `examples/`
- the language is Awl, the source syntax is Aesop, those names are not a compound product name
- local `time` Package adds monotonic and UTC wall clocks, bounded sleeps and overflow-checked deadlines, `clock.wall` is a new checked intrinsic emitted only into programs that use it
- the offline editor recognizes the wall-clock intrinsic, db/websocket/fetch Packages and native Windows acceptance remain unfinished
- scanner/parser C ABI v2 removes dialect-selecting exports
- source-current native, inference, editor and generated-program evidence lives in `tests/aesop-*`, older SDK archives are unchanged


- `@m` mutable borrows for struct parameters, the callee edits the caller's value in place, arguments must be an existing local, field or element, `@m` on non-struct types is rejected with `E229`
- bare `return;` in unit functions, running the scope cleanup on the way out
- unknown field, function, local, module variable and enum variant diagnostics now suggest the closest real declaration, `E229` covers mutable-borrow misuse
- docs/NEXT-LANGUAGE.md documents the new borrow rule and the diagnostic behaviour, the tour and examples-next/structs carry `@m` examples

# unreleased structs, loops and hash containers

- `struct Name { field:type; };` value types with positional construction, field access, field mutation through nested paths, `@r struct` exports across modules and struct values in fixed arrays
- `for i in 0..n { ... };` ranges and `for value in collection { ... };` over vector, view, int_vector, fixed array, map keys and set elements, plus `break;` and `continue;` with scope cleanup in both loop forms
- `map<K,V>` and `set<T>` with one api, text or integer keys, text payload copies, hash iteration, growth and tombstones, `@s` ownership with automatic release and borrowed container arguments
- new examples `examples-next/structs`, `examples-next/loops`, `examples-next/containers`, gate `tests/next_features.py` builds and runs each one through the bundled SDK, report in tests/next-features.json
- `compiler/next/syntax.cpp` and `tests/next_examples.py` cover38 example sources including the new grammar, the tour now carries structs, loops and containers, capability stays26.7%=12/45

# unreleased structural checker repair

- syntax checker no longer reads `i < n` as a generic call, dotted enum patterns, array literals and qualified enum field types all parse, string literals stop shadowing operators such as `-`/`and`/`move`
- the checker auto-loads `use` targets from disk with a cycle/depth guard, so one file argument is enough and `demos/next-syntax` runs again
- new gate tests/next_examples.py checks all 34 examples-next sources in one file each, report in tests/next-examples.json, no capability change

# Awl 0.26.0-dev, 2026-11-07

- next function declarations replace parentheses and `end;` bodies, `func name :: @b x[i64], y:i64: i64 { ... };` and `func main: i64 { ... };`, parenthesized parameters and function `end;` are rejected
- `::` is a two-character token in the next scanner, the parser rejects `(...)` lists, empty `::`, missing `{` and a missing trailing `;`
- `awl init` starter, 47 migrated sources and every focused native/verifier fixture use the new form, 21 entry programs emit byte-identical C
- docs/NEXT-LANGUAGE.md, compiler/migrate_next.py and the standalone compiler/next structural checker follow the revision
- new `editor/awl-editor.html` single-file editor with the owl mark, current next-syntax highlighting and a source-level subset interpreter
- published the complete 0.26 Linux SDK, resources inherited and re-verified from 0.25, capability stays26.7%=12/45

# Awl 0.24.0-dev, 2026-11-07

- complete Awl Software Development Kit rebrand, .aw sources and .awproj manifests across compiler/imports/editor/examples/docs/tests/tooling
- canonical awl executable, all eight Linux ASCII casings and mixed-case init/build/help/version, no project/import/option-value folding
- fixed source-suffix length and implicit import-namespace trimming, preserved browser AST fields and corrected Unicode demo offsets/counts
- published complete freshly rebuilt Linux SDK and unaccepted Windows preview, verified18105upstream files per platform, complete inventory/archive hashes,107-command exact Linux offline acceptance
- fresh564x3zero-skip compatibility,11native sanitizer phases,12runtime groups, native/WASI/browser/worker/editor coverage and genuine opened captures
- superseded public downloads retired only after successor qualification, original source/compiler/reports/photos/helpers retained unchanged in the indexed historical capsule
- capability remains22.2%,10/45, no new universal performance or native Windows acceptance claim

# unreleased local networking foundation

- linux loopback tcp listeners/accept/read/write/close, bounded manual handles and monotonic deadlines
- real native serve, health/stateful counter routes and strict bounded bodyless HTTP subset
- socket SIGPIPE suppression is per-call, existing pipe policy unchanged
- normal/strict sanitizer/fault/independent-verifier gates, no new archive or windows qualification
- explicit --compact-shared opts into measured Os/LTO size/latency tradeoff, standalone stays O2/LTO

# unreleased typed collections and text workload

- scalar/text vector<T>, checked growth and mutation, independent slice copies
- scoped/borrow/own/move/refill/defer integration, runtime kind tags and allocation-failure preservation
- real multi-file sort, stable utf-8 bytewise line sorting and optional --unique
- strict-warning sanitizer coverage, independent verifier and injected allocator failures
- optional linux standalone --lto reduces this compiler by 40960 bytes, no speedup claim
- practical capability remains15.6% (7/45), windows deferred, no new archive

# unreleased native streams and cli breadth

- linux stdin byte reads, raw stdout/stderr writes and explicit output flush
- bounded environment size/read, missing vs empty, checked no-partial-copy errors
- real native pipe manifest project, copy/upper/lower pipelines and stderr reports
- runtime/os fault tests, generated-c sanitizers and independent verifier checks
- personality.md and the four-file per-turn reading routine are now explicit
- native tooling stage 1 → 2, coarse practical score 15.6% (7/45), no other stage raised
- windows deferred, no new complete archive published

# 0.13.0-dev — restricted owning builder parameters

- Explicit own spool parameters, same-block `move` arguments at direct statement/new-local initializer/return calls; caller consumed and callee registers normal-exit cleanup.
- Owning formals can borrow/relocate/forward, cannot copy/free/return descriptor; no owned-result functions or general control-flow joins. Borrow+consume alias/double-consume rejected.
- Owning parameter registrations counted against64scope/256project cleanup budgets, including unused functions. Contextual own preserves existing own function/local/ordinary parameter names.
-16new tests/14new verifier cases;440regressions/config,170emitted-C sanitizer methods, benchmark/Windows cross-link/full native acceptance. Retain newest complete archive only after validation.

# 0.12.0-dev — restricted local ownership moves

- Scoped-to-scoped same-block `move name`, explicit consumed-source state/E221 checks, destination LIFO cleanup and emptied source descriptor. No new payload allocation/copy.
- Conservative source eligibility rejects manual/borrowed/moved/outer-block sources and general expression/return/call moves. Not general ownership transfer or control-flow merge analysis.
- Contextual parsing preserves existing move functions/locals; verifier eligibility checked before destination-name insertion to close same-name shadow bypass.
-16new methods/12new verifier corruptions;424methods/config,154emitted-C sanitizer methods; benchmark/Windows cross-link/full native archive acceptance. Only newest full release retained after acceptance.

# 0.11.0-dev — nonescaping builder borrow parameters

- Explicit `borrow b:spool` parameters; safe use/forwarding through checked synchronous helpers/modules/recursion without ownership transfer or callee release.
- Reject copy/escape/free/reassign or by-value forwarding; shared mutable descriptor borrows, not exclusive references/general lifetimes. Manual alias caveats remain.
-16borrow methods,13new verifier cases,4minimum-version gate tests;408regressions/config,138emitted-C sanitizer methods; benchmark/cross-link/exact full-archive acceptance.
- Native feature test selection no longer silently loses coverage for new minor releases; historical evidence retained. Only newest complete release archive retained after acceptance.

# 0.10.0-dev — restricted scoped ownership

- Fresh scope-owned spool bindings with static no-copy/no-escape/no-reassign restrictions;11explicit built-in synchronous borrow contexts; manual/deferred free rejected E220.
- Validity-guarded automatic LIFO release on normal exits/returns, interleaved with defer; recoverable unavailable allocation and zero-capacity handling. Not general borrowing/moves/ownership or trap unwinding.
-16focused methods/12new verifier corruptions;388methods per configuration;122emitted-C sanitizer methods; benchmark/cross-link/exact full-native-archive acceptance.
- Complete merged distribution retained; all older release archives removed at user request only after validation. Historical source/docs/evidence retained.

# 0.9.1-dev — compact construction / complete native bundle

- Native `[seed;count]` with once-only seed evaluation, fixed value copies and independent count/shape/layout verification; no ownership/dynamic allocation claims.
- Full native Linux distribution merges all updates and the pinned base toolchain: one archive, no overlay installation.
- Eight new methods,14new verifier corruptions, benchmark and Windows cross-link; final artifact acceptance recorded separately.
- Contributor builder restores executable mode even when replacing snapshot-restored non-executable binaries.

# Changelog

## 0.9.0-dev — typed fixed-size arrays

- Native project `[T;N]` structural types/literals, checked i64 reads and local-rooted element stores, nested/nominal/module types, function/aggregate value copies and array.length with preserved effects.
- Independent checker/verifier layout/type/shape/count/1MiB budgets; generated C wrapper types avoid pointer decay and preserve copies. Bounds violations trap before access/RHS evaluation. Resource descriptor elements remain aliases, not owners.
- Emission collects types only from verified reachable nodes; private regression ensures orphan arena type metadata cannot affect generated C.
- All integer/bool/string/resource/aggregate/union element tests, order/bounds/budgets/seeded matrix checks, sanitizers and artifact acceptance recorded separately. Dynamic arrays/slices/generics/ownership remain absent.
- Defined roadmap credit+0.60planning points (core category35→38, unchanged weight20), broad estimate~15.5%, subjective—not measurement. Earlier archives unchanged; compact overlay still directly over complete0.7.1.

## 0.8.4-dev — scoped deferred resource releases

- Native project-only `defer` for spool.free/buffer.free/window.close. Capture argument once at registration, LIFO lexical exit and nested-return cleanup; evaluate return value before cleanup. Scope cleanup per loop iteration and match arm.
- Checker/independent verifier validate permitted calls, metadata, project mode,64registrations per scope/256per project. Lower to captured C locals/explicit exit calls, no runtime closure stack.
-100,000-call example; tests for ordering/capture/returns/branches/loops/unit/match, reclaimed buffers and100actual X11 windows. This is NOT static ownership/borrowing, transfer/escape analysis, arbitrary defer or trap/exception unwinding.
- Exact validation/artifact acceptance recorded separately. Broad language roadmap estimate remains~15%, subjective and incomplete. Prior archives preserved.

## 0.8.3-dev — typed reusable UTF-8 builders

- Opaque `spool` type with independent checker/verifier layout/type checking; not interchangeable with integer/buffer/window handles. Manual checked aliases, not ownership/moves/borrowing.
- Fixed-capacity UTF-8 append/scalar/decimal construction, atomic capacity/scalar failures, direct output with recoverable stream error, clear/reuse and immediate payload reclamation. Snapshot copies into existing bounded immutable string region.
- Source-level tagged Status/Created example module,100,000-update native example; tests cover1million reuse iterations,100,000 create/release cycles, allocator/atexit failure injection, accounting and ID exhaustion.
- Full language roadmap and explicit~15% subjective progress rubric. Packages website/API/accounts/uploads recorded but deferred.
- Native-only distribution acceptance and detailed validation recorded separately; earlier releases remain immutable.

## 0.8.2-dev — immutable native UTF-8 strings

- First-class `string` values/literals, escapes and Unicode scalar validation; embedded NUL preserved through generated C and printing. Strings pass through native source modules, aggregate fields, unions and function calls/returns.
- Concatenation/equality, byte/scalar counts/access, checked scalar slicing, lexicographic compare, exact i64/u64 formatting. No implicit conversions, normalization or ordering operators.
- Native immutable storage: static literals plus bounded process-lifetime region, 64 MiB payload/65,536 allocations; normal-exit cleanup. NOT ownership/GC/individual reclamation or a production long-running heap.
- Actual UTF-8 X11 window-title updates; 1,024-byte/no-NUL policy. Project-only string scanner retains legacy quote-error behavior; checker/verifier/layout/runtime extended independently.
- String/scalar/heap/provenance/runtime regression and sanitizer evidence recorded in tests/strings-validation.json. Full0.7.1 and prior overlays remain unchanged; compact0.8.2 overlay applies directly over0.7.1.

## 0.8.1-dev — native source modules

- Added rooted native import resolution, aliases, isolated namespaces, qualified functions/structs/unions/types/patterns, deterministic linking and canonical/hard-link identity deduplication. All declarations exported initially; import DAGs only.
- Added originating-file diagnostics/AST provenance and protection against overwriting any imported source. File/depth/edge/aggregate source/token/arena budgets enforced; missing/nonregular/escaping sources fail without fallback.
- Added15module methods, including15seeded graph oracles; modular four-file windowed pyramid tested.292methods/configuration pass. Source-byte parser mutation compatibility preserved by isolating filesystem project grammar.
- Native project verifier harness rejects8provenance corruptions; emitted-C module/runtime and native frontend/driver sanitizers pass. Still whole-program C emission, not binary separate compilation or a full language.

## 0.8.0-dev — experimental native application primitives

- Added 17 exact-signature intrinsics for checked byte-buffer handles, monotonic timing/sleep, native Linux X11 windows, pixel presentation and resize/close/key/mouse events. Checker and independent verifier validate calls; no general FFI added.
- Native runtime implements a narrow local X11 wire client and cookie authentication; server pixmap presentation needs no Xlib/SDL/Python/runtime downloads. Real-window pyramid demo replaces stdout transport for this workload.
- Ten new product/runtime-sanitizer methods cover resource misuse and actual authenticated window/input/pixel/resize/close behavior. Verifier targeted corruption coverage increased to79.
- Experimental/manual handle lifetimes, not ownership or production GUI safety. Native Wayland/Windows windows, modules/strings/generic arrays, HTTP/TLS and browser target remain unfinished. Python reference retains older subset. Complete 0.7.1 release unchanged; compact dev overlay reuses its resources.

## 0.7.1-preview — native process/resource hardening

- Added configurable backend wall-time/address-space limits and optional run timeout.
- Forwarded INT/TERM/HUP/QUIT, escalated after 500 ms, cleaned up/reaped process-group descendants, and closed inherited descriptors before exec.
- Added bounded static ELF validation, symlink/empty-output rejection and umask-respecting publication. Existing outputs survive failed compilation.
- Fixed a cold-cache Zig descriptor regression caught by offline acceptance: preserve soft limit while capping hard descriptors at 32768, not 1024.
- Nine new hardening test methods also pass on the ASan/UBSan driver. All 266 methods pass per configuration; 1262 runtime outputs match at each O0/O3; offline isolation covers 20 commands.
- Language scope unchanged. These are per-process operational limits, not a sandbox; see docs/PROCESS-LIMITS.md.

## 0.7.0-preview — Linux x86-64 Awl-only engineering bundle

- Added a relocatable native build/run driver using only its own shipped toolchain.
  Pinned Zig 0.15.2, LLVM/Clang/LLD 20.1.2, static musl/startup/compiler-runtime and
  headers; no Python, host compiler/linker/SDK or runtime downloads.
- Packaged ACC is itself static musl/libc++, built by the bundled toolchain.
  Compiler subprocess environment is explicit; no PATH/CC fallback. Outputs are
  atomically staged; source overwrites rejected; run propagates exits/signals.
- Offline unprivileged clean-root/private-network test passes 18 commands including
  all examples, 348 integer checks, traps, relocation and missing-resource failure.
- 257 methods pass per configuration. Bundled codegen matches 1,262 value-oracle
  outputs at each O0/O3. New driver passes ASan/UBSan checks. Full-build measurements
  report warm timings and the much larger first empty-cache runtime-build cost.
- Added lock/provenance manifests, notices, MIT project license, source in bundle,
  contributor packaging, archive checksum and a Linux bundle CI job (not executed
  remotely here). Linux 6.1.189 x86-64 is the locally tested baseline only.
- Engineering preview, not stable/production-safe. No Windows/ARM bundle, ownership,
  modules/GPU, direct LLVM IR backend or self-hosting claim.

## Earlier 0.7 development — native frontend/C emitter

- Made the Awl-only Linux installation requirement a mandatory release gate.
  Created concise read-first agents/memory/to-do notes.
- Added the C++20 arena parser, bounded recovery, optional parser parity bridge,
  and source-byte frontend with pinned Unicode lexical policy.
- Ported value-language resolution, type/layout/control-flow/match checking to C++.
  Native source/typed arenas stay in native memory in the standalone executable.
- Added a static Linux native `acc` frontend: check, structured diagnostics,
  emit-ast and emit-checked-ast. It explicitly rejects build/run: native machine-code generation,
  linking and complete distribution remain unfinished.
- Added typed-tree/diagnostic parity tests, malformed-input mutations, standalone
  parser/checker sanitizers and frontend-only latency measurements. Exact results
  and caveats are recorded in docs/NATIVE-FRONTEND.md and tests/frontend-validation.json.
- Added an independent read-only native IR verifier with graph/schema, type,
  symbol, layout and control-flow checks; never repairs or trusts cached success.
- Added a native guarded C11 emitter and emit-c CLI command. Runtime templates are
  embedded data; output matches reference cases byte-for-byte. Build/run still
  require an unimplemented bundled machine-code/linking path.
- Current validation: 248 methods per configuration, 45 targeted + 10,000 seeded
  IR corruption rejections, native-emitted C's 348-check sanitizer matrix.
- No new language constructs or packaged 0.7 release. The installed-product release
  acceptance criterion remains unmet; Python/external-C build is contributor-only.

## 0.6.0 — measured native compiler migration, stage 1

- Added an optional C++20 UTF-8/token scanner, bounded record buffer, explicit C ABI
  ownership and version/structure-size checks. Python still owns token policies,
  parsing, type checking, IR verification, C emission and the native compiler driver.
- Added `--lexer python|native`, ACC_LEXER selection and explicit missing-library
  errors. Python remains default. Native binaries are host-built and not in the zip.
- Added bulk POD-record transfer after measuring that per-field ctypes transfer was
  slower than the reference. Both the slower baseline and latest raw timings remain.
- Added in-process scanner/frontend and cold CLI check/build benchmarks. The latest
  synthetic test improves integrated lex/check times, but full build time is nearly
  unchanged. No compiled-program speedup or fully native compiler claim.
- 213 test methods pass with both lexer defaults. Added 2,000 randomized parity cases
  and a standalone native scanner ASan/UBSan harness with 10,000 raw-byte inputs.
- No new Awl syntax/semantics; KIR0 schema remains v0.5. Direct API invalid-Unicode
  input now reports E008 consistently. No language features silently completed.

## 0.5.0 — fixed-width integer family (partial M1)

- Added i8/i16/i32 and u8/u16/u32 alongside existing i64/u64, with typed literal
  suffixes, signed minima, exact-width operators, printing and aggregate fields.
- Added explicit checked conversions using integer type-call syntax. No implicit
  widening, signedness changes, C promotions or boolean conversions.
- Generated C guards narrowing and arithmetic before undefined/implementation-defined
  signed behavior; unsigned operations retain Awl checked rather than wrapping rules.
- Only referenced integer arithmetic/print/conversion helpers are emitted.
- Added literal suffix boundary diagnostics and width-aware layout resource estimates.
- Extended IR verification and KIR0-structured-v0.5 literal/conversion metadata.
- Expanded 158 tests to 196 methods: 512 generated expressions, all 64 conversion
  pairs, valid/invalid bounds at O0/O3 and 500 additional source mutations.
- Added 348-check ASan/UBSan boundary/conversion matrix and narrow-integer benchmark;
  native outputs were checked against Python. Four sanitizer example smokes passed.
- Newly builtin integer names are reserved; some formerly accepted numeric/name
  adjacency is now a lexical error. ABI and serialized IR remain unstable.
- Ownership, modules, floats, usize, generic metaprogramming and GPU remain absent.

## 0.4.0 — tagged unions and exhaustive matches (partial M1)

- Added finite nominal tagged unions with qualified constructors, nullary variants
  and multi-field typed payloads, including scalar/struct/union nesting.
- Added exhaustive statement matches with ordered single evaluation, scoped mutable
  payload copies, discards, no fallthrough and branch-aware return analysis.
- Rejects missing/duplicate/foreign cases, invalid payload patterns, direct payload
  projections, declaration cycles and oversized/deep aggregate graphs.
- Extended the independent IR verifier and C11 code generation. Native representation
  uses a tag plus union payload; a defensive invalid-tag branch aborts.
- Added concrete result-handling example, diagnostic golden and union benchmark.
- Expanded 96 tests to 158 methods, including 750 source mutations, 150 generated
  native O0/O3 matches and corrupted-IR tests. Results sanitizer smoke passed locally.
- KIR0-structured-v0.4 adds union and match node forms; serialization remains unstable.
- Generic Option/Result, ownership, heap allocation, imports and GPU remain absent.

## 0.3.0 — value types (partial M1)

- Added u64 with explicit suffixed literals, exact-type arithmetic/comparison and
  checked add/subtract/multiply/divide/remainder. No signed/unsigned coercions.
- Added nominal by-value structs, nested scalar/struct fields, positional
  constructors, field selection, local-rooted field mutation and value calls/returns.
- Added cycle, field-count, value-depth and estimated-size limits to layout analysis.
- Extended the independent IR verifier to the new scalar and aggregate operations.
- Added a runnable values example and C/Python-oracle-validated value-state benchmark.
- Expanded tests from 57 to 96 methods, including 500 new source mutations and
  200 unsigned differential cases at O0/O3. Values sanitizer smoke passed locally.
- KIR0-structured-v0.3 uses a declarations array and new aggregate node kinds.
- Ownership/references, heap allocation, tagged unions and ABI interoperability
  remain unimplemented. No executed Windows/Clang CI evidence is claimed.

## 0.2.0 — frontend hardening (partial M1)

- Added source token offsets and rendered code-point source ranges.
- Added text/JSON diagnostics and panic-mode syntax recovery, capped at 20 errors.
- Added source, token, literal, identifier, syntax and IR-depth budgets.
- Added bounded UTF-8 file reads with encoding diagnostics.
- Added independent read-only KIR0 verifier after checking and before C emission.
- Added minimum-i64 direct literal syntax and portable `INT64_MIN` emission.
- Expanded tests from 24 to 57 methods, including golden diagnostics, malformed
  IR mutation, 1,000 seeded source mutations and 200 generated expressions tested
  against an independent oracle at two native optimization levels.
- Expanded authored CI matrix to Linux GCC/Clang and Windows MinGW GCC, with Linux
  sanitizer smoke runs. Remote CI has not run here.
- Versioned typed IR JSON as KIR0-structured-v0.2; not backward-stable interchange.
- Preserved the initial benchmark at benchmarks/baseline-0.1.0.json and reran the
  smoke benchmark, now recording ACC version. No language-wide performance claim.

## 0.1.0 — bootstrap M0

Initial scalar language, Python compiler, typed structured IR, C11 native backend,
24 tests, examples, benchmark harness, architecture and milestone plan.

## bounded persistent backend checkpoint

`examples-next/apps/valueserve` adds native text PUT/GET/DELETE, strict body framing, JSON escaping, sorted text-map helpers and checksummed exclusive mutation segments with restart replay

192 native +192 strict sanitizer service cases,746 helper assertions per native/sanitized mode and15 storage fault checks passed, actual terminal capture in `demos/valueserve/native-kv.png`, contract and limits in [docs/VALUE-SERVE.md](docs/archive/VALUE-SERVE.md)

current practical capability20.0% =9/45, backend1→2 for a useful bounded native workload, no other area rises, not production readiness, no new archive, windows remains deferred

## reusable structured JSON checkpoint

native `examples-next/parsing/Json.aw` now parses bounded nested JSON with decoded Unicode, exact number text, byte-offset diagnostics and transactional token publication, JSON Pointer lookup and the real `jget` configuration CLI are implemented

440 parser/pointer cases and28 CLI cases passed EACH native/strict sanitizer mode, actual display capture in `demos/json/native-json.png`, API/limits in [docs/JSON-PARSING.md](docs/archive/JSON-PARSING.md)

capability remains20.0% =9/45, existing CLI/backend stage2 strengthened, no manufactured point, compiler/protected archives unchanged, no new distribution or windows/browser acceptance

## native source graphics checkpoint

`examples-next/apps/colorlab` adds a real native RGB/grayscale picker and reusable checked rectangles, lines, disks and scaled5x7 text on typed pixel surfaces, actual mouse/resize/close behavior is tested, screenshot in `demos/colorlab/native-colorlab.png`

275 cases/59503 pixel-status assertions plus17 real-window checks EACH native/sanitized, contract in [docs/GRAPHICS.md](docs/archive/GRAPHICS.md), index remains20.0% =9/45, no extra desktop stage or3D claim, compiler/distributions unchanged

## native atomic-save checkpoint

new `file.replace(directory,temporary,target)` publishes a completed staging file through atomic same-directory rename, source and directory syncs are checked, status1 explicitly means published but durability uncertain, real native `save` handles binary stdin without truncating the old target

72API/CLI cases,14fault/reuse cases and all10native compiler sanitizer phases passed, rebuilt networking/JSON/jget/graphics regressions passed, contract in [docs/ATOMIC-SAVE.md](docs/archive/ATOMIC-SAVE.md), actual capture in demos/replace/native-replace.png

compiler rebuilt to SHAa5bd2899…, older checkpoints remain historical, full3mode legacy wasn't rerun, index remains20.0%=9/45, no new archive or native Windows acceptance

## private associated-value enums

next syntax now accepts private typed enums and exhaustive matches, nested payloads and arm-local bindings are independently verified, the real checked `calc` workload exercises typed parse/arithmetic errors, see [the enum contract](docs/archive/ENUMS.md)

54 feature cases,450 calculator oracle cases per native/sanitized mode, all11compiler sanitizer phases and564legacy tests in each of3modes passed, current hashes are in tests/enum-checkpoint.json,67editor sources are browsable but its browser runtime still doesn't execute enums

capability stays20.0%=9/45, exported/resource/generic enums remain work, no new downloadable archive or native windows acceptance

## compiled browser foundation

[open the offline json workbench](web/archive/Awl-json-workbench.html), production-verified Awl runs as real webassembly, with strict JSON validation, exact numeric text and JSON Pointer selection, no remote service or host compiler is needed to use the standalone HTML

437 native/browser parity cases and444webassembly integer/enum oracle cases pass, fresh workers, cancellation, timeout and opaque sandbox execution are checked, all11native sanitizer phases and564legacy tests in each of3modes pass on the rebuilt compiler

browser foundation0→1, current practical index22.2%=10/45, not a full browser compiler/framework or full-stack platform, see [the contract](docs/archive/BROWSER-WASM.md), protected SDK downloads remain unchanged and native windows stays deferred

## checked vector performance and collection polish

O(1) handle lookup and fixed-size typed get/set retain identity/kind/layout/bounds and checked arithmetic, new vector.swap/vector.truncate support in-place mutation and capacity reuse, see [the measured performance review](docs/PERFORMANCE.md)

35focused cases,440078runtime assertions,12Node WASI cases,11native sanitizer phases and564legacy tests across3modes pass, the real10000line sorter improves from8.704to7.552ms in this local comparison, optimized C++ and rust wins/losses and raw samples are reported, no universal faster-than claim

rust-competitive native performance is a core goal, not an accomplished blanket result, practical workload index stays22.2%=10/45,69editor sources, no updated archive or native windows acceptance
