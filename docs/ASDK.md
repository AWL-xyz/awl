# Awl Software Development Kit [Beta]

the normal native public command is **`awl`**, this beta implements **init/build only**, including project and single-file compilation through the real parser, checker, verifier, C emitter and complete bundled backend, no Python wrapper or host compiler is required

complete `0.24.0-dev` bundles use `.aw` source files and `.awproj` manifests, linux command-name aliases cover all eight ASCII casings, init/build and help/version verbs accept mixed case, project names and import paths are never case-folded, `-o` and `-O` remain distinct

linux qualification binds the exact published archive in `tests/rename-checkpoint.json`, the complete windows bundle is a cross-built resource-verified preview, **not native windows-host accepted**, native windows qualification remains deferred until language completion

## Commands

```sh
Awl                         # help, commands and argument syntax; exit 0
awl --help
awl --version
awl init MyApp              # initialize HERE, not in a new MyApp directory
awl build                   # build the sole .awproj file in this directory
awl build MyApp             # search immediate child folders for MyApp.awproj
awl build main.aw            # single source file, including its project imports
awl build path/to/file.aw
awl build path/to/old.aw --syntax legacy
awl build main.aw -o my-program -O 3
```

Yes: KCC already supported compiling a single `.aw` source. ASDK retains that
capability through **`awl build file.aw`**, including paths with spaces when quoted.
Direct-file builds default to the new dialect. Use `--syntax legacy` for existing
legacy `function`/`local` examples. Project builds read the dialect from their
manifest; `--syntax` explicitly overrides it. KCC's internal commands also default to next in the Linux0.25 SDK, use
`--syntax legacy` explicitly for legacy sources, there is no syntax autodetection.

### Initialization

`awl init MyApp` creates these files in the terminal's current directory:

**MyApp.awproj**

```text
format: 1
entry: main.aw
syntax: next
```

**main.aw**, only when absent:

```Awl
func main: i64 {
    print("Hello from Awl!");
    return 0;
};
```

An existing regular `main.aw` is preserved byte-for-byte. An existing manifest,
symlink or nonregular source is never overwritten. No nested project folder,
Packages directory, lockfile or hidden environment is created. Each new file uses
exclusive creation. The two-file initialization is not a filesystem transaction:
a write failure or concurrent initializer may leave one new file; inspect the
error/files before retrying. Existing sources are not rolled back or deleted.

Names are case-sensitive, 1–64 ASCII letters/digits/underscore/hyphen, starting
with a letter/digit. Path separators, whitespace, dots and reserved Windows device
names such as `CON` are rejected. These are project identifiers, not arbitrary paths.

### Manifest format and discovery

The `.awproj` file is a small UTF-8 line-based configuration, not a Awl script.
It identifies the starting script **for compilation**; it does not contain or
execute the application itself. Each line is `key: value`. Blank lines and whole
`#` comment lines are allowed. CRLF is accepted. Values are unquoted; spaces in
entry paths are preserved except leading/trailing whitespace.

- `format: 1` and `entry: relative/file.aw` are required.
- `syntax: next` or `syntax: legacy` is optional (default `next`).
- Unknown/duplicate keys, unsupported formats, NULs and files over 16 KiB fail.
- The entry must resolve to an existing regular `.aw` file within the manifest's
  directory tree. Absolute paths and symlink/`..` escapes are rejected.
- Manifests are regular, non-symlink files with the exact `.awproj` extension.

`awl build` requires exactly one manifest **in the current directory**, without
walking upward. Zero or multiple manifests produce actionable errors.

`awl build NAME` searches **immediate non-symlink child directories** for the
exact `NAME.awproj` filename. The folder itself need not be called NAME. It does not
pick the first match, recurse, or silently fall back to a different project.
Multiple matches are an error; enter the intended folder and use `awl build`.
Discovery is bounded to 4096 entries per scanned directory / 512 child folders.

A target ending in lowercase `.aw` selects direct-file compilation, not project-name
lookup. It may be relative or absolute. Its file imports use the compiler's normal
project resolution and privacy rules. Direct compilation needs no `.awproj` file.

### Output and options

| Build | Default executable |
|---|---|
| Current/named project | `<project>/build/<manifest-stem>` |
| Direct `.aw` file | `<terminal-current-directory>/<source-stem>` |
| Any build with `-o PATH` | Exactly PATH, relative to terminal cwd if not absolute |

Windows default outputs use `.exe` in its existing backend/project path logic;
Windows execution is not qualified for this beta. Explicit `-o` paths are literal.

The default project `build/` directory is created if needed and must not be a
symlink. Explicit output parent directories must already exist. Compilation
failure leaves a previous executable intact. Imported/entry sources and the
project manifest are protected against output overwrite. These checks are not a
hostile concurrent-filesystem sandbox.

Accepted build flags (each at most once):

```text
-o FILE
-O 0|1|2|3                  default 2
--syntax next|legacy
--build-timeout 1..3600      seconds, default 120
--build-memory-mib 512..16384 default 4096
```

Build prints the resulting executable path; it does **not** run it. To execute:

```sh
./build/MyApp
# or, after awl build file.aw:
./file
```

Help/version return 0. Source diagnostics return 1. Usage/discovery/manifest/backend
failures return 2, except the driver's existing timeout/cancellation statuses.
Internal compiler/backend diagnostics may still carry a `kcc:` prefix during beta.

## Installation and PATH

Keep the complete installation's `bin/` and `libexec/` together. The backend is
located relative to the actual executable, not through PATH. Do not copy just the
binary into a different prefix and expect the bundled SDK to follow it.

For a **future complete ASDK bundle**, extract it and add its `bin` directory to
PATH. Linux example (replace the path with your chosen install location):

```sh
export PATH="$HOME/tools/Awl/bin:$PATH"
Awl
```

Add that export to your shell startup file for persistence. A symlink named `awl`
in an already-on-PATH directory can instead point to the bundle's `bin/awl`.
On Windows, the corresponding future setup adds the installation's `bin` folder
to the user's PATH so `Awl.exe` is found. Windows validation is deferred, not
claimed complete.

Contributors can build the native executable using:

```sh
python3 compiler/build_native.py --standalone --static --strip --gc-sections
export PATH="$PWD/compiler/native/bin:$PATH"
Awl
```

`--gc-sections` is Linux-only and optional. Repository binaries can initialize
projects and show help, but compilation additionally needs the complete bundle's
`libexec/zig` resources at the installation prefix. Contributor Python/C++ tools
are not end-user runtime dependencies. `kcc` remains an internal compatibility name
for diagnostics/regression tooling; **new user-facing workflows use `awl`**.

## current evidence

current authority is `tests/rename-checkpoint.json`, the SDK source/API proof is `tests/rename-ASDK.json`,62cases with the real bundled backend and no host tools on PATH,45additional command/project cases cover every linux command-name casing, implicit imports, exact-case names and failure preservation

`tests/slots-regressions.json.gz` includes12groups, covering47module/math cases,65next-syntax cases and56typed-vector cases in the appropriate normal/sanitized modes, the full564-test compatibility suite passes in each of3modes with zero skips

`tests/rename-bundle-archive.json` records107commands against the exact complete Linux archive in an offline unprivileged clean root, including all eight public command casings, init/build and actual resulting program execution, no Python, shell or host compiler exists inside that root

`tests/rename-windows-integrity.json` verifies the complete Windows preview archive, source, PE imports and all18105pinned upstream resources, it is **not native Windows-host acceptance**, that work remains deferred until language completion

SDK validation snapshots prove the named feature/resource preparation runs, the exact archive's acceptance and checksums are published separately to avoid a self-hashing archive, older reports are immutable historical evidence in the indexed capsule, not acceptance of changed binaries
