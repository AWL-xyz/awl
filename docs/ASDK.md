# Awl Software Development Kit

## current source and older releases

the current source accepts only Aesop syntax, older distributed binaries predate this grammar, a source build is not a complete SDK and must not be presented as one

native Windows-host acceptance is deferred, cross-compilation and Wine execution do not establish it

## contributor build

```sh
python3 compiler/build_native.py --standalone --strip
compiler/native/bin/awl check examples/collections/main.aw
compiler/native/bin/awl run examples/collections/main.aw --cc "$(command -v cc)"
```

On Linux x86-64, `--cc` runs the compiler at the supplied absolute path (e.g. `/usr/bin/cc`) with its normal host environment. Use a trusted GCC or Clang installation with C headers, linker tools and `libm`. Output targets the build host and may be dynamically linked. The default remains the bundled backend; Awl does not silently search `PATH` or use the `CC` environment variable. A complete, matching SDK needs neither a host compiler nor Python to build Awl programs.

`acc` is the Awl Compiler Collection driver. `acc check` and `acc emit-c` require no backend. For a manual C11 build, use:

```sh
compiler/native/bin/acc emit-c examples/collections/main.aw > /tmp/collections.c
cc -std=c11 -O2 /tmp/collections.c -lm -o /tmp/collections
/tmp/collections
```

## public toolkit

```sh
awl
awl new Demo
awl check Demo
awl test Demo --list
awl test Demo --check
awl build Demo
cd Demo
awl add /path/to/awl/packages/time/time.awpkg
awl build path/main.aw -o program
awl run path/main.aw -- --name "Ada Lovelace"
```

- Bare `awl` displays help. `new Demo` creates a fresh `Demo/` directory containing `Demo.awproj`, `main.aw`, a shared `App.aw` module, `Smoke.test.aw`, and `.gitignore` for `/build/`. It refuses any existing destination, including a symlink, and removes the starter files it created if a write fails.
- To work in an existing directory, use `init Demo`. It creates `Demo.awproj` and, only if absent, `main.aw`. `init Greeting --pkg` or `init --pkg Greeting` creates `Greeting.awpkg` and a Package starter. Initialization never overwrites existing files. Names for `new` and `init` are 1–64 ASCII letters, digits, underscores or hyphens, start alphanumeric, and cannot be reserved device names.
- `add FILE.awpkg` copies a local Package into the sole project in the current directory, under `packages/` beside its entry file. It does not fetch packages, resolve dependencies, or overwrite an existing installation. See [Package layout and limits](PACKAGES.md).
- `check`, `build`, `run`, and `test` use the same target selection: omit the target for the sole `.awproj` in the current directory, give a project name to search immediate child directories for the exact manifest name, or give a `.aw` file including project-local imports.
- `check` parses, type-checks and verifies the project without a C backend or executable. Source errors exit with status `1`.
- `build` keeps the executable. Project outputs default to `<project>/build/<manifest-name>`, single-file outputs default to `<cwd>/<source-stem>`, and default Windows executable names end in `.exe`. It refuses to replace the selected project manifest, any loaded source or Package manifest, or a filesystem link to one of those inputs.
- `run` builds a temporary executable, forwards arguments after `--` to it, and returns its exit status. It inherits the caller's working directory and standard streams. Use redirected input with supervised `run`; for interactive terminal input, build and run the executable directly. Process supervision is not a security sandbox; run only trusted code.

`awl` command-name and verb casing are ASCII-insensitive; project names, paths, Package names and aliases remain case-sensitive.

## formatting source

```sh
awl fmt main.aw                         # preview on stdout, no file writes
awl fmt --check main.aw Smoke.test.aw   # fail if either file would change
awl fmt --write main.aw Smoke.test.aw   # apply on Unix
awl fmt - < main.aw                      # read source from stdin
```

The formatter uses the Aesop parser, but does not load imports, resolve names, type-check, or invoke a C backend. It indents braces, enum variants, match arms, and parenthesis/bracket continuations with four spaces per level. It removes trailing layout whitespace, uses LF (including a final LF for nonempty input), and keeps blank lines. It does not wrap lines or rewrite tokens, literals, import paths, interior spacing, or comment text other than trailing whitespace.

Pass explicit `.aw` files, not a project name. Stdout mode and `-` require one input; `--check` and `--write` accept up to 64 files. Each input and formatted output is limited to 1 MiB. Use `--` before a filename starting with `-`. Symlinks and non-regular source files are refused in all modes.

On Unix, `--write` stages each changed file next to its original and replaces it atomically. It requires owned, writable sources and refuses hard-linked files. It retains ordinary permission bits, not the original inode or extended metadata. Unchanged files are not rewritten. A multi-file invocation is not a transaction across files; syntax errors leave that file untouched. Do not run `--write` while editing the same file. Windows preview supports stdout and `--check`, not `--write`.

Exit status is `0` on success, `1` on invalid syntax or when `--check` finds a change, and `2` on invalid options or I/O/budget errors. `--diagnostic-format json` emits one syntax report per invalid input on stderr. Do not redirect stdout back into the input file; use `--write` instead.

## testing a project

Place test files like `Totals.test.aw` next to the project's entry source. Each is an ordinary Awl program. Use the same local modules and Packages as the application, then return `0` from `main` on success or a status from `1` to `255` on failure. Printing a message before a failure return helps explain what went wrong.

From the repository root, try the [complete example](../examples/testing/) with a source-built toolkit on Linux x86-64:

```sh
(cd examples && awl test testing --cc "$(command -v cc)")
```

- Project tests run in case-sensitive filename order, from the directory containing the `.awproj`. Discovery is not recursive. It skips hidden files and the selected entry itself, rejects symlinks and other non-regular `.test.aw` files, and is bounded to 4,096 directory entries and 64 tests. No tests found is a configuration error, not a successful empty run.
- `awl test path/One.aw` runs just that file and keeps the caller's working directory. Each test builds a temporary executable with the same backend as `awl run`. Tests get EOF on stdin and no arguments; their stdout and stderr are visible.
- The runner reports `PASS`, `FAIL`, or `TIMEOUT` for each test. A compile error, nonzero program status, or timeout counts as a failure; by default the suite continues. It returns `0` if all selected tests pass, `1` on any failure, and `2` for invalid invocation or project configuration. Interrupting the runner stops the suite and returns the interruption status.
- The program timeout defaults to 30 seconds **per test**; use `--run-timeout` to change it. `--build-timeout` applies separately to each compilation. No executable is kept. Only run trusted tests: supervision is not a security sandbox.
- `--filter TEXT` matches a nonempty, case-sensitive substring of the filename, including its extension. Filtering happens **after** discovery and validation, so it cannot hide an invalid test path or bypass suite limits. No match exits with `2`.
- `--list` prints one selected filename per line, without parsing test sources. `--check` runs frontend checks and reports pass/fail without building or executing anything. Neither accepts backend or timeout flags. Use `--fail-fast` with checks or execution to stop after the first failure and count any remaining selected tests as skipped; it cannot be used with `--list`.

## project manifest

```text
format: 1
entry: main.aw
syntax: aesop
```

Aesop is also the default when the syntax key is omitted, `syntax: next` and `syntax: legacy` are rejected rather than silently interpreted as Aesop

see [Packages](PACKAGES.md) for the distinct `.awpkg` manifest and local import layout

## command options

| option | commands | meaning |
| :--- | :--- | :--- |
| `--syntax aesop` | check, build, run, test | explicit assertion of the only supported syntax |
| `--diagnostic-format text\|json` | check, build, run, test | source diagnostic format on stderr; default `text` |
| `-o FILE` | build | executable destination, relative to the caller's working directory |
| `-O 0\|1\|2\|3` | build, run, test | optimization level, default `2` |
| `--cc ABSOLUTE_PATH` | build, run, test | opt in to a host C compiler on Linux x86-64 |
| `--build-timeout 1..3600` | build, run, test | backend timeout in seconds, default `120` |
| `--build-memory-mib 512..16384` | build, run, test | backend memory bound, default `4096` |
| `--run-timeout 0..86400` | run, test | per-program timeout in seconds; `0` means unlimited, the default is `0` for `run` and `30` for `test` |
| `--filter TEXT` | test | select tests whose filenames contain a case-sensitive substring |
| `--list` | test | list selected filenames without compiling |
| `--check` | test | check selected sources without building or executing |
| `--fail-fast` | test | stop after the first failure |
| `-- ARG ...` | run | pass the remaining arguments to the program, unchanged |

Options follow the optional target. `-o` and `-O` are different options. `build` and `run` return `124` when a backend or program exceeds its wall-time limit. `test` counts each timeout as a failed test. With `--diagnostic-format json`, each source failure emits its own JSON report on stderr; this does not change the suite summary or test program output. Registry publishing and server-based `add`/`install` are not implemented.

omitting a function result requests body-based inference, see [Aesop return inference](AESOP.md#return-type-inference), owned resource results remain explicit

## language and evidence

- [Aesop syntax reference](AESOP.md)
- [built-in API and conversions](API.md)
- [capability assessment](CAPABILITY-ASSESSMENT.md)
- [current source gates](../tests/README.md), including `tests/toolkit.py` for Linux source builds and the `awl test` workflow without a bundled backend
- older checkpoints bind their recorded compiler/source hashes, not the current source by implication

`tests/sdk-source-current.json` records a complete Linux SDK built at an earlier source checkpoint. It does not qualify the new toolkit commands in an SDK archive. Exact-archive and native Windows qualification remain separate release work.

## frontend embedding

the scanner/parser C ABI is version 2, source-byte and filesystem entry points both use Aesop, dialect-selecting exports were removed, integrations must rebuild against the current headers rather than loading a version-1 frontend by accident
