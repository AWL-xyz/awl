# Native source modules — 0.8.1-dev

**Implemented and locally tested.** This increment adds real file-based namespaces and static module linking. It does not add binary separate compilation, packages, ownership or a complete application ecosystem. Subsequent0.8.2 adds immutable UTF-8 strings (STRINGS.md), including values crossing module boundaries.

## Example

`geometry/points.aw`:

```Awl
struct Point
    x: i64
    y: i64
end
function shifted(p: Point, dx: i64) -> Point
    return Point(p.x + dx,p.y)
end
```

`main.aw`, in the parent directory:

```Awl
import geometry.points as geo
function main() -> i64
    local p: geo.Point = geo.Point(10,20)
    print(geo.shifted(p,5).x)
    return 0
end
```

```sh
./bin/kcc run /path/to/project/main.aw
```

Output: `15`. No interpreter, host compiler or package manager participates.

The shipped `examples/modules/main.aw` exercises shared types, tagged unions and diamond imports and prints `10`, `15`, `3`. `examples/apps/pyramid/main.aw` is the native window application split into **four files**: entry/event loop, window helper, renderer and geometry/math. The modular application was tested against an authenticated display, including rendered pixels, motion over time and normal close.

## Resolution and names

- An entry program is still a `.aw` file with `function main() -> i64`.
- `import geometry.points` loads `geometry/points.aw` and binds namespace `points`. `as geo` selects an explicit alias.
- Every import path is rooted at the **canonical entry file's directory**, regardless of current working directory or which module contains the import. Imports omit the `.aw` extension.
- Path components and aliases are identifiers, not strings; no `..`, absolute path, wildcard, network import, package registry or environment search path is accepted.
- Imports precede declarations. A module alias cannot collide with a declaration, local/parameter/pattern binding, reserved keyword or builtin name.
- All top-level functions, structs and unions in an imported file are exported in this first version. There is no `pub`/private visibility syntax yet. Importing a module does **not** inject its declarations into the caller's unqualified scope, nor re-export its imported namespaces.
- Qualified calls/constructors: `geo.shifted(...)`, `geo.Point(...)`. Qualified types work in parameters, results, fields and locals.
- Qualified union construction/patterns: `results.Result.Value(...)`, `case results.Result.Value(point) then ...`. The example includes both.
- Same-spelled types in different files have distinct nominal identities. Struct fields/union variants retain their original names.
- Canonical aliases and hard links to one file share a module identity. Diamond imports do not duplicate declarations. All import cycles are rejected, including cycles containing only functions. Local function recursion remains supported.
- A library may define a namespaced `main`; only the entry module's `main` is the program entry point. `check library.aw` still checks it as an entry program, not as a standalone library target.

## Compiler architecture

`compiler/native/kproject.inc` implements the native filesystem loader. Each file is scanned/parsed into its own arena. The loader builds a bounded dependency DAG, resolves qualified names, assigns deterministic collision-free internal symbols, and merges the resolved arenas into the existing checker/verifier/emitter pipeline. This is AST-level static linking, **not textual concatenation or a preprocessing shell script**.

The ordinary checker validates the resulting cross-file signatures, layouts and control flow. The independent read-only verifier still validates every emitted arena and now also checks project-origin metadata. C emission remains whole-program C11 consumed by the unchanged shipped native backend.

Compilation reloads source files on every invocation. Editing an imported dependency is observed on the next build; there is no stale frontend project cache. Source-order symbol numbering does not embed absolute filenames into generated C, so relocating the same project preserves its emitted C in the tested examples. That is not a general binary reproducibility guarantee.

Native C ABI additions: `Awl_parse_file`, `Awl_source_file_count`, `Awl_source_file_path`. No existing ABI function signatures changed. Existing source-byte/token APIs remain filesystem-free with their older value-language grammar/diagnostic behavior; imports through them are diagnosed when checked. Module syntax resolution requires the filesystem project entry API. This preserves the contributor Python bridge's existing mutation-parity contract; Python does **not** implement filesystem modules.

## Diagnostics, limits and publication

- Text diagnostics name the originating file and its original line/column.
- Multi-file JSON diagnostics include a per-diagnostic `file`; `start`/`end` are original-file Unicode-code-point offsets, not UTF-8 byte offsets. The top-level `file` remains the requested entry name. Checked AST exports add `sources` and token-indexed `origins` entries `[file_index,start,end,line,column]` for merged projects.
- Internal linked type names are translated back to user-facing file/type names in diagnostic messages.
- E300: loading/path/budget/import-position failure; E301: cycle; E302: unknown module/member or inappropriate declaration kind; E303: alias collision. Existing E100/E200/E210 diagnostics remain applicable within files.
- Budgets: 64 unique files, 32 levels (entry counts as level one), 256 import edges, 16 path components/128 path characters, aggregate 1 MiB source (including merge separators), 100,001 total token records including per-file EOF, and 200,002 arena slots. Existing verifier reachable-node/nesting/layout/C-output budgets also remain. This is a deliberately bounded foundation, not large-codebase scalability certification.
- Only regular files are loaded. Canonical import paths must remain inside the project root; symlink escapes fail. This is a resolution policy under normal filesystem permissions, **not a hostile-filesystem race-proof sandbox**.
- Build output may not overwrite **any loaded source**, including through canonical paths, symlinks or hard links. Failed parsing/checking still preserves a previous executable.

## Executed evidence

Fifteen module-test methods cover aliases, qualified types/unions/parameters/results, namespace isolation, shared identity/diamonds, cycles, nonexistent/nonregular/escaping sources, collisions, errors/provenance, every source's output protection, depth/file/edge/source budgets, relocation/determinism, changed dependencies, source-byte API isolation and 15 seeded graph output oracles. All generated module examples pass at O0/O3 where selected; emitted-C ASan/UBSan runs pass too.

A further platform method validates the four-file pyramid in a real authenticated X11 window, including under emitted-C ASan/UBSan. Native sanitizer harnesses check a valid resolved project, read-only verification, eight targeted origin-metadata corruptions and the filesystem C ABI, alongside the existing 79 arena-corruption cases and 10,000 structural mutations.

Full **292-method** regression suites pass in three configurations. The first regression run caught grammar/diagnostic drift in the source-byte parser; project grammar was isolated from that compatibility API, and all original mutation-parity tests now pass without weakening their assertions. Current report: `tests/modules-validation.json`; final extracted-update acceptance remains external to the immutable archive.

Warm full-build samples for the tiny three-file example and equivalent monolith both had medians around **48.6 ms** on this host, seven alternating samples each. This is not evidence of general zero-overhead modules, large-project scalability or generated-program speedup. See `benchmarks/modules-build-latest.json`.

Next: typed arrays/slices and resource/error types; immutable strings now exist with separately bounded process-lifetime storage; explicit visibility, separate compilation/incremental builds and packages remain open. The previous native window limitations and unfinished broader platform goals still apply.
