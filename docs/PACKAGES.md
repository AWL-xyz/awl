# Packages

**Implemented in source, development build.** A package is a folder holding a manifest and a library source file, installed by copying it under the project root, there is no registry, network fetch, lockfile or version solving yet.

## Layout

```text
myapp/
  main.aw                use env;
  packages/
    env/
      env.awpkg          manifest
      env.aw             entry, exports{ ... }
```

`NAME.awpkg` is `key: value` lines, `format: 1`, `kind: package`, `name: NAME` are required and must match the folder name, `entry:` names a plain `.aw` file in the same folder and defaults to `NAME.aw`, `version:` and `syntax:` are informational for now.

## Using a package

`use NAME;` selects `packages/NAME/NAME.awpkg` under the project root, the alias is `NAME` or an explicit `use NAME as other;`, a bare name never falls back to a local file and a missing or malformed package is `E300`, package names are 1..64 letters/digits/_/- and need `as` when they are not valid identifiers, project files keep using `use path/file.aw as alias;`.

## Creating a package

`awl init NAME --pkg` (or `awl init --pkg NAME`) creates `NAME.awpkg` and, if absent, `NAME.aw` with an exported `hello` function, an existing manifest is never overwritten, copy the folder to `<project>/packages/NAME/` to install it.

## Standard packages in this tree (`packages/`)

|package|status|API|
|---|---|---|
|`json`|working|`json.parse(source, tokens, result)`, `json.locate(pointer, tokens, result)`, same code as `examples-next/parsing/Json.aw` (16384 byte limit)|
|`env`|working|dotenv parsing, `env.parse(source, keys, values, result)`, `env.find`, `env.get(name, keys, values, fallback)`, `export` prefix, comments, double quoted escapes, single quoted literals, result[0]=1 invalid key, 2 missing `=`, 3 unterminated quote, 4 more than 256 entries, result[1]=line, 5 invalid input/buffer/allocation, 6 junk after quoted value|
|`fsp`|working|`fsp.read(path)` returning `Read.Text` or `Read.Failed`, same code as `examples-next/exported-enums/File.aw`|
|`time`, `db`, `websocket`, `fetch`|not started|need native runtime support (clock, SQLite/Awldb, sockets and TLS), not expressible in Awl source yet|

`examples-next/packages-demo` installs copies of all three and uses `env` and `json`.

## Not implemented

dependency resolution between packages, `awl add/install`, lockfiles, a user-wide package directory, packages importing other packages from their own `packages/`, the registry and the `Awldb`/`envman` naming and publication.

## current merge qualification

these are development-source features, the received complete0.26 SDK predates this Package/ACC/spool work, its successful offline acceptance is not acceptance of the merged source as a shipped SDK

compiler collection name is Awl Compiler Collection (ACC), the source driver recognizes `acc`, `kcc` remains a compatibility executable/file name, `awl` is still the public toolkit command, future complete bundle builders include the `acc` alias, no server `add/install` command was added

`env.parse` accepts up to16384 UTF8 bytes and256total pairs, checks aligned keys/values and a result vector with at least2elements, accepts LF/CRLF and quoted newlines, comments retain the preceding pair, long keys/values aren't silently truncated, EOF empty values are empty, result code0means success, valid preceding pairs remain appended on a later error, this isn't an atomic parser, it doesn't mutate OS environment variables, `find/get` use the first matching duplicate key, bare-CR line endings and variable expansion aren't promised

14 integration groups check both Package initializer flag positions and overwrite protection, created modules/aliases, missing/wrong-case/private/cyclic imports, malformed names/format/entry and duplicate aliases, native/sanitized env/json/fsp and real WASI env/json, fsp covers actual UTF8 file reads, missing files, invalid UTF8 and over16384-byte files, the manifest reader isn't a registry security boundary or dependency resolver

latest source evidence is `tests/package-import-checkpoint.json`, inherited release/editor/old-source reports remain historical rather than acceptance of different source bytes

map repairs during import are checked separately by `tests/map_model.py`,10000 independently modeled operations, non-power-of-two initial capacity, set zero-width storage, stale/quota traps and native/sanitized/WASI extraction surviving clear, maps charge owned text together with table storage against64MiB, immutable returned snapshots use the existing separate bounded process-lifetime string region, this isn't reclaimable text or mutation-safe/concurrent iteration

primary C interface validity reference, [POSIX2.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/functions/V2_chap02.html#tag_16_01_01), zero-width set storage must not pass a null pointer to a standard memory operation, tests caught this under UBSan and the runtime now skips zero-byte/null value operations

all15 compiler ASan/UBSan phases passed on the merged source, including865 targeted verifier corruptions, full historical564x3 legacy qualification was not rerun, workload score remains26.7%=12/45
