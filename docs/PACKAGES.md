# Packages

**Implemented in source, development build.** A Package is a folder with a `.awpkg` manifest and Awl modules. `awl add` vendors local Package sources into a project. There is no registry, network fetch, lockfile, or version solving.

## Layout

```text
myapp/
  main.aw                use env;
  packages/
    env/
      env.awpkg          manifest
      env.aw             entry, exports{ ... }
```

A `NAME.awpkg` manifest is at most 16 KiB and uses `key: value` lines. Blank lines and `#` comments are allowed. `format: 1`, `kind: package`, and `name: NAME` are required; keys cannot repeat. `entry:` is a plain `.aw` filename beside the manifest and defaults to `NAME.aw`. The entry cannot use Windows-reserved characters or device names. `version:` and `syntax:` are informational.

## Installing and importing a Package

From the directory containing your project's sole `.awproj`, run:

```sh
awl add /path/to/awl/packages/time/time.awpkg
```

Use the installed Package in your entry file:

```text
use time;

func main {
    print(time.now());
    return 0;
};
```

`awl add` is offline and does not need a backend. It copies the named manifest and `.aw` sources into `packages/NAME/` beside the project entry file. For an entry at `src/main.aw`, this means `src/packages/NAME/`. It does not overwrite an existing installation or write through a `packages` symlink. The source folder should be dedicated to the Package: `awl add` includes `.aw` files in that folder and its subdirectories, except hidden paths and `build` and `packages` directories. Other assets are not copied. The install rejects visible symlinks and is limited to 512 traversed entries, eight levels of subdirectories, 64 source files, and 1 MiB of source data.

`awl add` validates manifest and file layout, not Awl types or the import graph; run `awl check` after adding the `use`. On a write error it rolls back its new files and directories, leaving existing Packages alone. An interrupted copy may need manual removal. Use trusted local Packages. You can commit the vendored sources with your project, or still copy the Package folder manually.

`use NAME;` resolves `packages/NAME/NAME.awpkg` from the entry source's directory. `use NAME as other;` sets an alias, required when the name is not a valid identifier. Package names are 1–64 letters, digits, underscores or hyphens, excluding reserved device names. A bare name never falls back to a file, and a missing or malformed Package is `E300`. Project-local files still use `use path/file.aw as alias;`.

## Creating a Package

In a separate library directory, run `awl init NAME --pkg` (or `awl init --pkg NAME`). It creates `NAME.awpkg` and, if absent, `NAME.aw` with an exported `hello` function. It never overwrites an existing manifest. From your project directory, run `awl add /path/to/NAME.awpkg` to use the library.

## Standard packages in this tree (`packages/`)

|package|status|API|
|---|---|---|
|`json`|working|`json.parse(source, tokens, result)`, `json.locate(pointer, tokens, result)`, same code as `examples/parsing/Json.aw` (16384 byte limit)|
|`csv`|working|`csv.parse(source, fields, rows)` and `csv.encode(fields, rows, sink)` for bounded UTF-8 tables with quoting, multiline fields, and canonical output. See [CSV API](CSV.md).|
|`env`|working|dotenv parsing, `env.parse(source, keys, values, result)`, `env.find`, `env.get(name, keys, values, fallback)`, `export` prefix, comments, double quoted escapes, single quoted literals, result[0]=1 invalid key, 2 missing `=`, 3 unterminated quote, 4 more than 256 entries, result[1]=line, 5 invalid input/buffer/allocation, 6 junk after quoted value|
|`fsp`|working|`fsp.read(path)` returning `Read.Text` or `Read.Failed`, same code as `examples/exported-enums/File.aw`|
|`time`|working|`time.now`, `time.wall`, `time.elapsed`, `time.deadline`, `time.remaining`, `time.expired`, `time.sleep`, checked monotonic/wall clocks and bounded sleeps, see [time semantics](TIME.md)|
|`db`, `websocket`, `fetch`|not started|need native runtime support (SQLite/Awldb, sockets and TLS), not expressible in Awl source yet|

`examples/packages-demo` installs copies of `env`, `fsp` and `json` and uses `env` and `json`, `examples/time-demo` installs a copy of `time` and uses its two clocks. [`examples/csv-demo`](../examples/csv-demo/) reads CSV from stdin, checks a numeric column, and totals the values.

## Not implemented

Dependency resolution between Packages, remote `add`/`install`, lockfiles, a user-wide Package directory, separate `packages/` directories per dependency, the registry, and the `Awldb`/`envman` naming and publication.

## current merge qualification

these are development-source features, the received complete0.26 SDK predates this Package/ACC/spool work, its successful offline acceptance is not acceptance of the merged source as a shipped SDK

compiler collection name is Awl Compiler Collection (ACC), the source driver recognizes `acc`, `acc` remains a compatibility executable/file name, `awl` is still the public toolkit command, future complete bundle builders include the `acc` alias, no server `add/install` command was added

`env.parse` accepts up to16384 UTF8 bytes and256total pairs, checks aligned keys/values and a result vector with at least2elements, accepts LF/CRLF and quoted newlines, comments retain the preceding pair, long keys/values aren't silently truncated, EOF empty values are empty, result code0means success, valid preceding pairs remain appended on a later error, this isn't an atomic parser, it doesn't mutate OS environment variables, `find/get` use the first matching duplicate key, bare-CR line endings and variable expansion aren't promised

14 integration groups check both Package initializer flag positions and overwrite protection, created modules/aliases, missing/wrong-case/private/cyclic imports, malformed names/format/entry and duplicate aliases, native/sanitized env/json/fsp and real WASI env/json, fsp covers actual UTF8 file reads, missing files, invalid UTF8 and over16384-byte files, `tests/aesop_time.py` separately checks native and sanitized time Package execution, wall-clock agreement with the host, checked deadlines, bounded sleeps, bad-arity rejection, Windows helper source syntax and the shipped demo, the manifest reader isn't a registry security boundary or dependency resolver

latest source evidence is `tests/aesop-checks.json`, `tests/aesop-time.json` and `tests/aesop-native.json.gz`, the original Package checkpoint and older release/editor reports are preserved under `tests/archive/` as historical evidence

map repairs during import are checked separately by `tests/map_model.py`,10000 independently modeled operations, non-power-of-two initial capacity, set zero-width storage, stale/quota traps and native/sanitized/WASI extraction surviving clear, maps charge owned text together with table storage against64MiB, immutable returned snapshots use the existing separate bounded process-lifetime string region, this isn't reclaimable text or mutation-safe/concurrent iteration

primary C interface validity reference, [POSIX2.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_01_01), zero-width set storage must not pass a null pointer to a standard memory operation, tests caught this under UBSan and the runtime now skips zero-byte/null value operations

all16 compiler ASan/UBSan phases pass on the current source, including869 targeted verifier corruptions, full historical564x3 legacy qualification was not rerun, workload score remains26.7%=12/45
