# practical capability assessment

current source note, conversions, type tests, namespace-only built-ins, file renames, documentation cleanup and source gates do not add a workload point, the score below remains 26.7% · 12/45

## current estimate, 26.7% — 12 / 45 stage points

it's a coarse engineering judgment against the requested software scope, not an objective fraction of all possible programs, the arithmetic's explicit but the underlying judgments aren't precise

the retired weighted ~20.1% score isn't comparable, the preceding20.0% estimate used this same45-point rubric, the earlier browser1→2 review covered the persistent full-stack workload, the latest change is systems1→2 for executed bounded native process supervision, not a denominator change

syntax, test counts, version bumps and plans don't earn points by themselves, development evidence isn't an accepted distribution, windows work's deferred until the language is fully developed, its missing evidence stays visible

the Awl rebrand, command-case support and freshly rebuilt complete SDKs earn no additional domain stage, those distribution changes left the score at22.2% /10 of45 before the separate full-stack review below, native windows-host acceptance is still deferred

## current evidence

current app authority includes `tests/board-checkpoint.json` and source-candidate `tests/process-checkpoint.json`, published Linux0.25 distribution authority is `tests/default-checkpoint.json`, exact Linux archive acceptance is in `tests/default-bundle-archive.json`, Windows preview integrity is separate and not native-host acceptance, older checkpoint references below are historical and their originals are retained in the indexed evidence capsule

## unchanged rubric

nine equally weighted areas, five cumulative stages each

| stage | required evidence |
|---|---|
| 0 | no demonstrated domain workload or usable domain-specific foundation |
| 1 | executed domain-specific foundation, important blockers still prevent a representative useful application or toolchain |
| 2 | a useful bounded real workload runs natively on at least one target, with correctness/error tests, major breadth limitations remain |
| 3 | a substantial integrated representative workload works on both linux and windows, using delivered end-user tooling, with reproducible acceptance |
| 4 | applicable failure/load/security, compatibility, resource, upgrade and deployment hardening is demonstrated |
| 5 | multiple substantial representative workloads establish broad reusable capability, not a one-off implementation |

stages need review, they're not automatic checklist completions, wine isn't native windows-host acceptance, a cpu framebuffer animation isn't the requested model/lighting/shadow 3d workload

## current stages

| area | stage / 5 | evidence and limiting factor |
|---|---:|---|
| cli / persistent-data tools | 2 | native intstats, kcopy, textinfo environment-configured pipe with binary stdin/stdout and typed-vector sort, broad parsing/configuration and structured recoverable errors remain open |
| native desktop applications | 2 | pixelboard saves and reloads validated drawings, with malformed-load rollback and overwrite refusal, limited source-rendered ASCII text/color controls now exist, general fonts/widgets/accessibility/media remain blockers |
| backend apis / services | 2 | useful native valueserve text store, strict request bodies, JSON output, restart replay and checked storage errors, bounded trusted local use only, no full HTTP/general JSON parsing/TLS/auth/concurrency or crash-durable database |
| browser frontend / full-stack | 2 | useful persistent Awl Board, native Awl HTTP/schema/storage and shared Awl WASM filtering, real-browser edits/conflicts/restart/export/failure checks, JS DOM glue and contributor WASM builds remain, no native Windows qualification or general DOM bindings |
| full 3d games / renderers | 0 | no gpu 3d renderer with loaded models, lighting and shadows, software framebuffer demos don't qualify |
| systems / long-running software | 2 | useful bounded native task supervisor, explicit argv and concurrent pipe draining, deadlines, retained-identity group/leader cleanup and reaping, validated build→execution batches, source candidate only, no async/sandbox/durable scheduler/native Windows acceptance |
| native developer tooling / required toolkit | 2 | native ASDK beta initializes projects and compiles real single/multi-file workloads, including pipe, manifest/error/sanitizer tests pass on linux, complete Linux SDK exact-archive acceptance exists, native windows qualification remains open |
| website / accounts / registry | 0 | planned, not implemented |
| default manager-published Packages | 0 | Awldb and envman/ENVMAN remain planned, not implemented |
| **total** | **12 / 45** | **26.7% coarse practical-capability index, rounded** |

## historical review, why native tooling moved from 1 to 2

the additional point's for an executed useful native developer workflow, not a rebranding or the number of new tests

- `awl init` creates a usable project without overwriting source
- `awl build` resolves current, named-child, custom-entry and direct-file builds
- multi-file private-state/math workloads execute through the real bundled backend
- the same toolkit builds the useful pipe project, which actually processes binary stdin/stdout with environment configuration and separate diagnostics
- missing/ambiguous projects, bad manifests, compiler failures, source/manifest protection and preservation of previous build output have executed checks

that's the existing stage-2 definition, a useful bounded native workload on one target with correctness/error tests, it doesn't meet stage 3, no accepted complete ASDK distribution or native windows-host execution is claimed

cli stays at 2, the new stream primitives improve its breadth but don't establish another stage, that tooling review added no browser, service, systems, registry or Package point

that historical tooling evidence includes `tests/streams-ASDK-regression.json`, `streams-linux.json`, `streams-sanitized.json`, `streams-faults.json`, `streams-legacy-regression.json` and the aggregate stream checkpoint

## history and next review

desktop moved from 1 to 2 for an actual persistent drawing workflow, not the version number, linux save/clear/load/restart and malformed-load rollback ran, exact 0.23 distribution evidence remains in `tests/persistence-release-acceptance.json`

old reports retain their original percentages and hashes in the indexed historical capsule, they aren't acceptance of changed binaries, the current complete Awl archives have separate fresh qualification, Linux exact-archive runtime acceptance and Windows unaccepted-preview integrity are explicitly distinguished

next priorities are language/runtime completeness, broader collections and parsing/configuration, safer storage, then networking/concurrency and representative applications, windows follows language completion, installed Packages and website work keep their roadmap dependencies

## historical typed-vector review

scalar/text vectors and stable multi-file sort close a real collection gap, but cli was already at stage2, this bounded workload does not meet stage3 or demonstrate a new domain, that checkpoint left the estimate at15.6% (7/45), arbitrary generics, maps, reusable parsing/results, networking and concurrency remain open

## historical review, backend moved from0 to1

this point is for a newly executed domain-specific foundation, not function/test counts or another cli tool, serve is a native Awl program accepting actual TCP connections, parsing a bounded bodyless request subset, routing health/stateful counter requests and emitting framed JSON responses

normal bundled-backend and sanitizer clients verify state changes, malformed/fragmented/oversized/slow requests and peer resets, runtime fault tests verify deadlines/cleanup/signal policy, no Python server or delegated host HTTP framework stands in for Awl

at that checkpoint stage1 only, loopback/single-threaded/manual sockets/limited process lifetime and HTTP subset remain major blockers, no production hardening, TLS, auth, request-body/JSON framework or concurrency, no native windows or full distribution acceptance, other eight area stages unchanged

## why backend now moves from1 to2

the added point's for a useful bounded local key/value backend, actual native PUT/GET/DELETE requests store text, survive process restart, return valid escaped JSON and delete persisted state, not just a health endpoint or an in-memory counter

strict request framing, independent record/checksum oracles, malformed recovery rejection, key/mutation limits and deterministic short-transfer/write/fsync/close failures have executed normal/sanitizer checks, see docs/VALUE-SERVE.md and tests/kv-{linux,sanitized,helpers,faults}.json

this matches the existing stage2 requirement on one native target, it doesn't imply broad backend readiness,128 keys/256 mutations/finite connections, trusted single writer, no full HTTP/JSON framework, TLS/auth/concurrency/compaction or power-loss durability, no new end-user bundle or native windows acceptance

other eight areas are unchanged, a source-level sorted text map isn't builtin arbitrary generic collections, JSON escaping isn't JSON parsing, file fsync isn't directory-safe persistence, this remains an early language with most requested scope unfinished

## structured parsing review, no new point

bounded native JSON event parsing, Unicode escape decoding, exact numeric text, byte-offset diagnostics and JSON Pointer now support a real jget configuration lookup workload,440parser+28CLI cases each native/sanitized, see docs/JSON-PARSING.md

CLI and backend were already stage2, this strengthens their reusable foundations without meeting another cumulative stage, index stays20.0% =9/45, windows remains deferred and builtin aggregates/generic DOM/reclaimable text are still missing

## native drawing review, no new point

source-level checked RGB/grayscale surfaces, clipped primitives and authored bitmap text now support the native Color Lab mouse-driven picker,275geometry/font cases and17real-window checks each native/sanitized, actual capture and limitations in docs/GRAPHICS.md

desktop already held stage2, no native Windows or substantial delivered cross-platform application evidence is added, no3D/domain point is earned, index stays20.0% =9/45

## atomic persistence review, no new point

Linux file.replace and native save now demonstrate checked atomic same-directory publication, precommit error preservation and explicit postcommit uncertainty, source+directory synchronization and fault tests close a real runtime gap

this strengthens existing stage2 persistent-data tools, it doesn't establish a substantial new systems workload or stage3 cross-platform evidence, index remains20.0%=9/45, see docs/ATOMIC-SAVE.md

## private enum language checkpoint

private associated-value enums, nested typed results and exhaustive matching are implemented and regression-tested, this improves reusable foundations without delivering another cumulative workload stage, practical score remains20.0%=9/45, exported/resource/generic enum types remain unimplemented, see [ENUMS.md](archive/ENUMS.md)

## current browser foundation review

browser0→1 earns one point for an executed production-compiler-to-webassembly path and interactive offline JSON inspection, not a javascript reimplementation,437native/browser parity cases and444webassembly integer/enum oracle cases pass, cancellation, timeout and opaque sandbox execution are checked, see [BROWSER-WASM.md](archive/BROWSER-WASM.md)

all other stages stay unchanged, important browser blockers prevent a general representative frontend/full-stack platform, no stage2browser or native windows/distribution acceptance is claimed

## vector performance review

checked vector lookup/access improvements and swap/truncate strengthen existing workloads, local sort and optimized comparison evidence is in [PERFORMANCE.md](PERFORMANCE.md), no new domain stage, index stays22.2%=10/45, rust-competitive performance is a target rather than a universal superiority claim

## useful full-stack review, browser1→2

Awl Board adds a useful bounded full-stack application, not another syntax count or JSON-only workbench, native Awl validates and persists tasks, the same schema/filter source executes as browser WASM, JavaScript supplies DOM/events and a narrow WASI host, no Python server or delegated framework replaces Awl

executed evidence,198 HTTP/storage/state-machine checks on each normal, public-SDK and ASan/UBSan build,24 deterministic storage fault checks,80 native/79 WASM independent filter/schema cases,6 maximum-capacity/deadline checks on each public/sanitizer build,23 real Chromium checks including independent stale tabs, actual storage refusal, lost acknowledgements and published-but-uncertain fail-stop, see `apps/board/README.md` and `tests/board-*.json`

this meets the existing stage2 useful bounded workload criterion on Linux, it earns exactly one point, total11/45=24.4%, not a stage3 or new backend/systems point, no native Windows acceptance, generic DOM bindings, concurrency, TLS/auth, interprocess store locking or arbitrary containers is claimed, browser compilation remains a contributor path, the separate standalone Linux app doesn't change the existing complete0.24 SDK archives

all other eight area stages remain unchanged, source-level helper reuse improves practical breadth but isn't new compiler syntax, a production framework or general language completeness

## exported result-type review, no new point

compiler-source exported enums now allow native multi-file settings/file-read APIs to return and exhaustively handle typed nested results, private variant access and nominal type identity remain checked, see [EXPORTED-ENUMS.md](archive/EXPORTED-ENUMS.md)

this closes a language/library-composition gap rather than a new workload domain or cumulative stage, current24.4%=11/45 stays unchanged, existing published SDK/compiler binaries aren't relabelled as containing this source-development feature

## next-default Linux SDK delivery, no new point

Linux0.25 now ships the qualified exported-enum implementation and makes Aesop syntax the default for all native compiler commands, public awl retains its init/build scope, legacy sources require an explicit compatibility selector or manifest declaration, the legacy C ABI/Python reference parser remain compatibility APIs

62 default/override/casing/error/output-preservation cases,187 native/sanitized exported-result/configuration checks and107 native/107 WASI result oracles bind the rebuilt compiler, the exact complete SDK passed112commands,348integer checks and5traps in an offline unprivileged environment without a host shell/Python/compiler,18105 upstream backend files were verified, see tests/default-checkpoint.json

this improves delivery and consistency, not another cumulative workload stage, score stays24.4%=11/45, the Windows0.24 preview remains older and not native-host accepted

## checked vector-view source review, no new point

read-only `view<T>` now supports the existing11 scalar/text vectors, with nonallocating descriptors, runtime identity/epoch/range checking, independent verifier tests and native/sanitized/WASI execution, the bounded multi-file logwindow reader/renderer adds a useful CLI example, not another cumulative domain stage

this is not static lifetime checking, arbitrary/resource generic storage, concurrent borrowing or a new published SDK, Linux0.25 and older Windows preview bytes stay unchanged, score remains24.4%=11/45, see VECTOR-VIEWS.md and tests/vector-views-checkpoint.json

## systems process-supervision review, one new point

systems moves1→2 because a useful native batch supervisor now runs real bundled-SDK build→execution jobs, validates the entire JSON plan before side effects, handles exit/signal/deadline/quota/UTF8 failures, drains both pipes, closes unrelated descriptors and reaps its direct child without retaining temporary allocations, this is process-lifecycle orchestration implemented in Awl/native runtime, not Python orchestration standing in for the application

103 native/sanitized/runtime/workload checks,24fault/lifecycle plus200repeated captures in each4sanitizer modes,13independent compiler sanitizer phases and view/default/enum/collection regressions bind the source candidate, test counts support the claim but don't themselves earn the point, no additional CLI/tooling point is awarded for the same workflow

this meets the unchanged stage2 useful bounded workload criterion on one native target, it does not meet stage3, no native Windows acceptance/new published SDK/process sandbox/async tasks/durable scheduler/hostile-descendant containment/hard real-time cleanup is claimed, procfs/default SIGCHLD and trusted jobs are required, see SUBPROCESSES.md

current total12/45=26.7%, all other area stages remain unchanged, original24.4% reports and preceding review sections describe their historical milestones rather than the new current estimate

## 0.26 publication note

the published0.26 Linux SDK now ships the revised next function declaration syntax and `editor/awl-editor.html`, a single-file editor with highlighting, a structural aid, recorded visual frames and a source-level subset interpreter, its bundled examples are re-checked by `acc check` in tests/awl-editor.json

an editor and a syntax revision are tooling and language surface work, they don't demonstrate a new application workload, so every stage and the total stay at26.7%=12/45

the practical gaps that would move a stage are unchanged, general desktop widgets/media, real model/material/lighting/shadow3D, concurrency and cancellation, HTTP/TLS/auth service workloads, a general browser DOM/compiler target, and the roadmap website/registry and default manager Packages

## local Package import review

source now has local creation/manifests/imports and tested env/json/fsp, the default manager-published Awldb/envman category remains0because those manager publications and database service aren't implemented, no rubric/category change, total26.7%=12/45 unchanged

current received Linux archive is0.26, independently accepted with50offline isolated commands, source is newer than that archive, current merge evidence tests/package-import-checkpoint.json, prior0.25 reports above remain historical
