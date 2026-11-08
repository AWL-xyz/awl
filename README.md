## imported changes, current source versus SDK

local Packages now support `awl init --pkg NAME`, `.awpkg` manifests and `use NAME;`, see [Packages](docs/PACKAGES.md), `env`, `json` and `fsp` are present, `db`, `time`, `websocket` and `fetch` remain unfinished, no server add/install

current source includes the incoming `func main: i64 { ... };` / `func f :: arg:type: result { ... };` grammar, dotted builtins, spool, structs, maps/sets and loops, the collection name is Awl Compiler Collection (ACC), source `acc` entry with historical `kcc` compatibility

incoming complete Linux0.26 archive was independently inventoried and passed50offline isolated commands/348integer checks/5traps before0.25 retired, this unchanged archive predates the newer Package/ACC/struct/container source work, the root compiler binary remains historical0.25, use source-bound evidence rather than the repeated0.26 development version alone, current merge authority tests/package-import-checkpoint.json, score26.7% unchanged

# Awl

<img src="assets/branding/awl-icon.png" width="96" height="96" alt="Awl owl logo">

an experimental native language and its **Awl Software Development Kit [Beta]**, current Linux development release `0.26.0-dev`

sources use **`.aw`**, project manifests use **`.awproj`**, the normal public command is **`awl`**

## complete downloads

- [linux x86-64 SDK](../Awl-0.26.0-dev-linux-x86_64.tar.xz), complete compiler and bundled backend, current next syntax shipped, exported enums included, qualification is recorded in `tests/default-checkpoint.json` and `tests/awl-editor.json`
- [older windows x86-64 preview](../Awl-0.24.0-dev-windows-x86_64-preview.tar.xz), complete cross-built preview, **not native windows-host accepted**, windows qualification stays deferred until language completion
- each download has an adjacent `.sha256` sidecar

extract the entire `Awl` directory, add its `bin` directory to `PATH`, keep `libexec` beside `bin`, no end-user Python, host compiler, SDK or separate backend download is needed

```sh
awl
awl init Demo
awl build
awl build examples-next/collections/main.aw -o collections
```

`awl`, `Awl`, `AWL` and all other ASCII command-name casings work on linux, `init` and `build` verbs accept mixed case too, project names, aliases and import paths remain case-sensitive, `-o` and `-O` retain their distinct meanings

public beta commands are still **init/build only**, `kcc` is internal compiler tooling, no public run/install/Packages/registry command is claimed

## useful full-stack application

[Awl Board](apps/board/README.md) is a persistent local taskboard, native Awl HTTP/schema/storage plus shared Awl WebAssembly filtering, tested in a real browser with stale-tab, storage-error and restart workflows, [standalone Linux application](../Awl-board-0.1-linux-x86_64.tar.xz), a separate complete app download, existing SDK archives are unchanged

current practical capability assessment, **24.4% =11/45**, a coarse workload rubric rather than a claim of language completeness, Windows remains deferred

## language and useful workloads

next syntax uses `func name :: params: type { ... };` declarations, `@p` bindings, adjacent-colon initialization/assignment, mandatory semicolons, braced if/elseif/else and while blocks, module access through `exports{...}`

```text
func size :: @b values[i64], etc[i64]: i64 {
    return vector_length(values) + vector_length(etc);
};
func main: i64 {
    @p version: 128.59;
    print(version);
    return 0;
};
```

implemented foundations include checked scalar arithmetic, functions/control flow, project imports/private defining-file context/export permissions, scalar module state and f64 math, fixed arrays/structs, bounded typed scalar/text vectors with stale-safe O(1) identities, checked swap/truncate and copied slices, scoped ownership for supported resources, private associated-value enums/exhaustive matching, UTF-8 strings/builders, Linux files/streams/local TCP, strict JSON helpers and native framebuffer windows/primitives

bounded examples include `kpipe`, `ksort`, `jget`, the local CRUD/persistence service, atomic file replacement, drawing/color tools and the donut, these are foundations, not equivalents of full desktop/media/browser/3D applications

- [SDK usage](docs/ASDK.md)
- [next syntax](docs/NEXT-LANGUAGE.md)
- [capability assessment](docs/CAPABILITY-ASSESSMENT.md), **26.7%, 12/45**, systems stage2 for the bounded task supervisor
- [roadmap](docs/ROADMAP.md)
- [performance and limits](docs/PERFORMANCE.md), prior measurements are historical, no new universal speed claim

## offline browser files

- [awl. editor](editor/awl-editor.html), single-file next-syntax editor with the owl mark, highlighting, a structural aid, recorded visual frames and a source-level subset interpreter, **not the native compiler**
- [Awl Studio](editor/Awl-studio.html), the older single-file legacy-subset playground, **not the native compiler** and not newly requalified
- [JSON workbench](web/Awl-json-workbench.html), freshly compiled verified C → WebAssembly, bounded offline worker host, exact i64 results and explicit cancellation/timeout handling

neither file needs a local service, neither editor implements native-equivalent ownership/type checking, typed vectors, general OS access or full 64-bit semantics

## qualification and remaining work

current Linux release authority is `tests/default-checkpoint.json`, app authority is `tests/board-checkpoint.json`, source-candidate process/view qualification is separate in `tests/process-checkpoint.json`, historical rename evidence remains preserved

arbitrary owned/nested generics, static borrowing, generic/resource enum payloads, reclaimable strings, concurrency, broader networking/TLS/auth, general desktop widgets/input/media/accessibility, substantial full-stack workloads and real model/material/lighting/shadow 3D remain incomplete

historical source, compiler bytes, original reports, photos and development helpers are preserved losslessly in `history/pre-rename-evidence.tar.xz`, with a per-file SHA-256 index, immutable historical evidence and unmodified upstream/OS terminology are not relabelled as current Awl acceptance

## contributors

`compiler/build_native.py` builds the native frontend/compiler, `compiler/package_linux.py` and `compiler/package_windows.py` build complete platform bundles from pinned toolchains, `compiler/package_sdk.py` verifies the entire upstream resource tree and packages rebuilt host binaries without overlays

contributor Python/C++/Node/browser/sanitizer tools are test/build dependencies, not end-user SDK dependencies, keep generated toolchain and cache trees outside the saved workspace and audit the entire `/home/user` budget

## compiler-source development

[exported enums and typed results](docs/EXPORTED-ENUMS.md) now work across modules in the Linux0.25 SDK, including a native multi-file configuration validator, native compiler commands default to next syntax, use `--syntax legacy` for old examples, the workload score stays24.4%

[checked read-only vector views](docs/VECTOR-VIEWS.md) now work in compiler source for the11 scalar/text vector types, with zero-allocation descriptors and runtime stale-owner/structural-epoch checks, not static lifetime checking, `apps/logwindow` exercises the API across modules, this source candidate is **not included in the published SDK archives**, score remains24.4%

[bounded native subprocess supervision](docs/SUBPROCESSES.md) and `apps/taskrun` now work in compiler source, including explicit argv, atomic dual-stream capture, timeouts, process-group/direct-leader cleanup and real bundled-SDK build→execution batches, this useful systems workload moves the coarse score to26.7%=12/45, **not shipped in the published SDK yet**, prior24.4% sections are historical

## clean syntax, source candidate

current source replaces old next exports/control blocks/modifiers with `exports{...};`, `if ... { ... } elseif ... { ... } else { ... };`, `while ... { ... };`, `@s/@b/@o/@w`, vector arguments such as `@b result[i64]`, `${name}` string injection and scalar `..` concatenation, see [the current syntax reference](docs/NEXT-LANGUAGE.md),47source files migrated, **published Linux0.25 still uses its previous syntax**, older embedded test fixtures/editor interpreter remain unqualified for this revision, score stays26.7%

next function declarations now use `func size :: @b values[i64]: i64 { ... };` and `func main: i64 { ... };`, not parentheses, arrows or function `end;`, these forms are published in the0.26 SDK, see [the release notes](RELEASE-0.26.md)
