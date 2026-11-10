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
| public toolkit | `awl`, currently `init` and `build` |
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

**contributor prerequisites:** Python 3, a C++20 compiler and a C compiler for the generated-program example below, Linux is the currently exercised host

```sh
python3 compiler/build_native.py --standalone --strip

compiler/native/bin/acc check examples/collections/main.aw
compiler/native/bin/acc emit-c examples/collections/main.aw > /tmp/awl-collections.c
cc -std=c11 -O2 /tmp/awl-collections.c -lm -o /tmp/awl-collections
/tmp/awl-collections
```

this builds a contributor compiler, not a complete redistributable SDK, `acc check` and `acc emit-c` work without the bundled backend

### toolkit workflow

```sh
compiler/native/bin/awl init Demo
compiler/native/bin/awl init Greeting --pkg
```

`init` writes Aesop starters without overwriting existing files, project initialization uses the current directory rather than creating a named child directory

with a complete, matching SDK backend installed alongside the driver, project builds use:

```sh
awl build
awl build Demo
awl build relative/main.aw -o program
```

`awl build` selects the sole current-directory project manifest, `awl build Demo` searches immediate child folders for `Demo.awproj`, a `.aw` target compiles directly

`awl` command-name casing and `init`/`build` verb casing are ASCII-insensitive, source paths, import paths, Package names and aliases remain case-sensitive, `-o` and `-O` are distinct

[toolkit details →](docs/ASDK.md)

## local Packages

```sh
awl init Greeting --pkg
```

local Package imports resolve through `packages/NAME/NAME.awpkg`, project-local file imports use `use path/File.aw as alias;`

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
```

current source evidence is recorded in `tests/aesop-native.json.gz`, `tests/aesop-checks.json`, `tests/aesop-program-sanitizers.json`, `tests/aesop-time.json`, `tests/aesop-migration.json` and `tests/aesop-editor.json`, these cover their stated source/native/editor scopes, not a complete standalone SDK or native Windows release

older reports and test utilities may describe retired compiler versions, they are historical evidence rather than acceptance for the current source tree

## license

see [LICENSE](LICENSE) for this project and [`third-party/`](third-party/) for bundled-resource notices
