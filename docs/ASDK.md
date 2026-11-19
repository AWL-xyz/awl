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
awl init Demo
awl add /path/to/awl/packages/time/time.awpkg
awl check
awl build Demo
awl build path/main.aw -o program
awl run path/main.aw -- --name "Ada Lovelace"
```

- Bare `awl` displays help. `init Demo` creates `Demo.awproj` and, only if absent, `main.aw` in the current directory. `init Greeting --pkg` or `init --pkg Greeting` creates `Greeting.awpkg` and a Package starter. Initialization never overwrites existing files.
- `add FILE.awpkg` copies a local Package into the sole project in the current directory, under `packages/` beside its entry file. It does not fetch packages, resolve dependencies, or overwrite an existing installation. See [Package layout and limits](PACKAGES.md).
- `check`, `build`, and `run` use the same target selection: omit the target for the sole `.awproj` in the current directory, give a project name to search immediate child directories for the exact manifest name, or give a `.aw` file including project-local imports.
- `check` parses, type-checks and verifies the project without a C backend or executable. Source errors exit with status `1`.
- `build` keeps the executable. Project outputs default to `<project>/build/<manifest-name>`, single-file outputs default to `<cwd>/<source-stem>`, and default Windows executable names end in `.exe`.
- `run` builds a temporary executable, forwards arguments after `--` to it, and returns its exit status. It inherits the caller's working directory and standard streams. Use redirected input with supervised `run`; for interactive terminal input, build and run the executable directly. Process supervision is not a security sandbox; run only trusted code.

`awl` command-name and verb casing are ASCII-insensitive; project names, paths, Package names and aliases remain case-sensitive.

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
| `--syntax aesop` | check, build, run | explicit assertion of the only supported syntax |
| `--diagnostic-format text\|json` | check, build, run | source diagnostic format on stderr; default `text` |
| `-o FILE` | build | executable destination, relative to the caller's working directory |
| `-O 0\|1\|2\|3` | build, run | optimization level, default `2` |
| `--cc ABSOLUTE_PATH` | build, run | opt in to a host C compiler on Linux x86-64 |
| `--build-timeout 1..3600` | build, run | backend timeout in seconds, default `120` |
| `--build-memory-mib 512..16384` | build, run | backend memory bound, default `4096` |
| `--run-timeout 0..86400` | run | program timeout in seconds, default `0` (unlimited) |
| `-- ARG ...` | run | pass the remaining arguments to the program, unchanged |

Options follow the optional target. `-o` and `-O` are different options. The driver returns `124` when a backend or program exceeds its wall-time limit. Registry publishing and server-based `add`/`install` are not implemented.

omitting a function result requests body-based inference, see [Aesop return inference](AESOP.md#return-type-inference), owned resource results remain explicit

## language and evidence

- [Aesop syntax reference](AESOP.md)
- [built-in API and conversions](API.md)
- [capability assessment](CAPABILITY-ASSESSMENT.md)
- [current source gates](../tests/README.md), including `tests/toolkit.py` for Linux source builds without a bundled backend
- older checkpoints bind their recorded compiler/source hashes, not the current source by implication

`tests/sdk-source-current.json` records a complete Linux SDK built at an earlier source checkpoint. It does not qualify the new toolkit commands in an SDK archive. Exact-archive and native Windows qualification remain separate release work.

## frontend embedding

the scanner/parser C ABI is version 2, source-byte and filesystem entry points both use Aesop, dialect-selecting exports were removed, integrations must rebuild against the current headers rather than loading a version-1 frontend by accident
