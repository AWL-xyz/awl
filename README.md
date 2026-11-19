<p align="center">
  <img src="assets/branding/awl-icon.png" width="104" height="104" alt="Awl owl logo">
</p>

<h1 align="center">Awl</h1>
<p align="center">an experimental native language, a single syntax, a growing compiler toolkit</p>

<p align="center">
  <a href="#quick-start-from-source">quick start</a> ·
  <a href="docs/AESOP.md">syntax reference</a> ·
  <a href="docs/PACKAGES.md">Packages</a> ·
  <a href="#status-and-limitations">project status</a>
</p>

---

## at a glance

| component | current state |
| :--- | :--- |
| language | **Awl** |
| source syntax | **Aesop**, the only grammar accepted by the current compiler source |
| compiler | **Awl Compiler Collection (ACC)**, native C++20 frontend with checked IR, an independent verifier and a C11 backend |
| source files | `.aw` |
| manifests | `.awproj` for projects, `.awpkg` for local Packages |
| public toolkit | `awl init`, `awl add` (local Packages), `awl check`, `awl build`, `awl run` |
| development version | `0.26.0-dev`, a development identifier, not a compatibility guarantee |
| release readiness | experimental source candidate, not production-ready |

> **source is ahead of distributed binaries**  
> the older Linux `0.26.0-dev` SDK predates this syntax and the newer Package/container work, it does not implement the declarations below  
> no source-current SDK release is claimed here, Windows native-host qualification remains deferred

## the language

function results are inferred from the body unless explicitly declared in brackets after the name, parameters follow `::`, calls still use parentheses

```text
func size :: @b values[i64], etc[i64] {
    return vector.length(values) + vector.length(etc);
};

func main[i64] {
    @p name: "Awl";
    print("hello ${name}");
    return 0;
};
```

- `func answer[i64] { ... };` declares a parameterless value-returning function
- `func greet[text] :: name:text { ... };` declares a function with a typed parameter
- omitted results are inferred from every return path, no value-returning statements means `unit`
- `func reset[unit] { ... };` explicitly requires a unit-returning body
- incompatible return types are errors, an unresolved recursive inference cycle requires an explicit result annotation
- `func make[@o vector<i64>] { ... };` declares an owned resource result
- `@p count: 3;` declares a binding, `count: count - 1;` assigns it
- braced functions/control flow and mandatory semicolons are part of Aesop, enums and matches retain their documented `end;` forms
- `vector.length(value)` queries vector length

`@b` explicitly borrows a resource parameter, an unmarked parameter does not acquire borrow permission, scoped resources must still follow the ownership rules, resource results require an explicit result/ownership annotation

the previous trailing-result, parenthesized-declaration and legacy grammars are rejected, `--syntax next` and `--syntax legacy` are not compatibility modes

see the [Aesop syntax reference](docs/AESOP.md) for declaration grammar, modifiers, imports, exports and resource rules

## quick start from source

**Prerequisites (Linux x86-64):** Python 3, a C++20 compiler, and a host C compiler with development headers and linker tools (such as GCC or Clang). Run the first two lines from the repository root:

```sh
python3 compiler/build_native.py --standalone --strip
export PATH="$PWD/compiler/native/bin:$PATH"

cd "$(mktemp -d)"
awl init Demo
awl check
awl run --cc "$(command -v cc)"           # Hello from Awl!
awl build --cc "$(command -v cc)"
./build/Demo
```

`awl init` writes starter files in the current directory without overwriting existing files. `awl check` needs no C backend. `--cc` explicitly selects a host compiler for a local build; without it, `build` and `run` still require a complete, matching SDK. The contributor build above is not a redistributable SDK.

### toolkit workflow

`check`, `build`, and `run` all accept the same targets: omit the target for the sole `.awproj` in the current directory, pass `Demo` to look for `Demo.awproj` in immediate child directories, or pass a `.aw` file directly. `awl run` passes arguments after `--` to the program and doesn't keep an executable.

For example, from the repository root, run the shipped sort utility with redirected input:

```sh
printf 'owl\nant\nowl\n' | awl run examples/apps/sort/main.aw --cc "$(command -v cc)" -- --unique
```

`awl` command-name and verb casing are ASCII-insensitive; project names, paths, Package names, and aliases remain case-sensitive. `-o` and `-O` are distinct.

[toolkit details →](docs/ASDK.md)

## local Packages

From an initialized project's directory, vendor a Package from this checkout or another local folder:

```sh
awl add /path/to/awl/packages/time/time.awpkg
```

Import it with `use time;` in Awl source, then run `awl check`. `awl add` copies the manifest and sources into `packages/` beside the project entry file without overwriting an existing installation. It needs no network or backend. To start your own library in a separate folder, run `awl init Greeting --pkg` there.

Project-local file imports still use `use path/File.aw as alias;`.

| Package | source implementation |
| :--- | :--- |
| `env` | dotenv parsing and environment-file helpers |
| `json` | JSON parsing and query helpers |
| `fsp` | filesystem path helpers |
| `time` | monotonic and wall clocks, bounded sleeps and checked deadlines |
| `db`, `websocket`, `fetch` | unfinished, not advertised as usable standard Packages |

registry publishing, server-based `awl add`/`install`, accounts and upload/review workflows are not implemented

[Package layout and examples →](docs/PACKAGES.md)

[time Package semantics and limitations →](docs/TIME.md)

## examples and tools

| location | purpose |
| :--- | :--- |
| [`examples/`](examples/) | the single current example tree, including collections, structs, loops, modules, local Packages and a standalone time demo |
| [`apps/taskrun/`](apps/taskrun/) | a bounded native subprocess supervisor |
| [`apps/logwindow/`](apps/logwindow/) | bounded UTF-8 log-window processing |
| [`apps/board/`](apps/board/) | a local persistent taskboard with native service code and a shared WebAssembly filter |
| [`editor/awl-editor.html`](editor/awl-editor.html) | a single-file offline Aesop subset editor/interpreter, **not the native compiler** |
| [`web/`](web/) | bounded browser/WebAssembly demonstrations with separate historical qualification |

existing prebuilt application artifacts and historical reports are not requalified by a source syntax migration

## status and limitations

implemented foundations include checked integer arithmetic, f64 values/math, typed functions, project imports and explicit exports, module-private context, fixed arrays, structs, bounded scalar/text vectors, checked runtime views, maps/sets, enums/matching, UTF-8 text/spools, local file/stream/TCP operations and native framebuffer primitives

important gaps remain in arbitrary owned/nested generic collections, static lifetime checking, resource enum payloads, reclaimable text, language-level concurrency, comprehensive networking/TLS/auth, general desktop widgets/media/accessibility and full model/material/lighting/shadow 3D

runtime views are not a static borrow checker, subprocess supervision is not a security sandbox, local demos are not substitutes for production browser, desktop, media or game engines

the current coarse [workload capability assessment](docs/CAPABILITY-ASSESSMENT.md) remains **26.7% · 12/45**, syntax changes and test counts do not increase that score

[performance methodology and limits →](docs/PERFORMANCE.md)

## development and validation

all current frontend, checker, verifier and emitter code lives in **`compiler/native/`**, there is no separate `compiler/next` frontend or Python language-parser fallback

```sh
python3 compiler/test_native.py
python3 compiler/test_native.py --sanitize
python3 tests/aesop.py --acc compiler/native/bin/acc
python3 tests/aesop_time.py --acc compiler/native/bin/acc --sanitize --report tests/aesop-time.json
python3 compiler/generate_runtime.py --check
python3 compiler/generate_platform.py --check
python3 tests/toolkit.py
```

See the [current test gates](tests/README.md). Checked-in evidence is bound to the compiler and sources recorded in each report; it does not qualify a new SDK or native Windows release.

older reports and test utilities may describe retired compiler versions, they are historical evidence rather than acceptance for the current source tree

## license

see [LICENSE](LICENSE) for this project and [`third-party/`](third-party/) for bundled-resource notices
