# Awl Software Development Kit

## current source and older releases

the current source accepts only Aesop syntax, older distributed binaries predate this grammar, a source build is not a complete SDK and must not be presented as one

native Windows-host acceptance is deferred, cross-compilation and Wine execution do not establish it

## contributor build

```sh
python3 compiler/build_native.py --standalone --strip
compiler/native/bin/acc check examples/collections/main.aw
compiler/native/bin/acc emit-c examples/collections/main.aw > /tmp/collections.c
cc -std=c11 -O2 /tmp/collections.c -lm -o /tmp/collections
/tmp/collections
```

Python and host compilers are contributor dependencies for these commands, installed complete SDKs are intended to contain their own backend/linker/resources without requiring those contributor dependencies

`acc` is the Awl Compiler Collection driver, its internal commands include `check`, `emit-ast`, `emit-checked-ast`, `emit-c`, `build` and `run`, backend-backed `build`/`run` require a matching complete resource layout

## public toolkit

```sh
awl
awl init Demo
awl init Greeting --pkg
awl build
awl build Demo
awl build path/main.aw -o program
```

- bare `awl` displays help, public beta verbs are `init` and `build`
- `init Demo` creates `Demo.awproj` and, only if absent, `main.aw` in the current directory
- `init Greeting --pkg` or `init --pkg Greeting` creates `Greeting.awpkg` and `Greeting.aw` in the current directory
- initialization never overwrites existing files, project and Package initialization are separate operations
- `build` selects the sole `.awproj` in the current directory
- `build Demo` searches immediate child folders for the exact `Demo.awproj`
- a `.aw` target compiles directly, including project-local imports
- project outputs default to `<project>/build/<manifest-name>`, single-file outputs default to the terminal working directory and source stem, Windows executable names have `.exe`

`awl` command-name casing and `init`/`build` verb casing are ASCII-insensitive, project names, paths, Package names and aliases remain case-sensitive

## project manifest

```text
format: 1
entry: main.aw
syntax: aesop
```

Aesop is also the default when the syntax key is omitted, `syntax: next` and `syntax: legacy` are rejected rather than silently interpreted as Aesop

see [Packages](PACKAGES.md) for the distinct `.awpkg` manifest and local import layout

## build options

| option | meaning |
| :--- | :--- |
| `-o FILE` | output executable, relative to the terminal working directory |
| `-O 0\|1\|2\|3` | optimization level, default `2` |
| `--syntax aesop` | explicit assertion of the only supported syntax |
| `--build-timeout 1..3600` | backend timeout in seconds, default `120` |
| `--build-memory-mib 512..16384` | backend memory bound, default `4096` |

`-o` and `-O` are different options, no public registry, server-based `add`/`install` or public `run` verb is claimed

omitting a function result requests body-based inference, see [Aesop return inference](AESOP.md#return-type-inference), owned resource results remain explicit

## language and evidence

- [Aesop syntax reference](AESOP.md)
- [capability assessment](CAPABILITY-ASSESSMENT.md)
- current source gates: `compiler/test_native.py`, `compiler/generate_runtime.py --check`, `compiler/generate_platform.py --check`, `tests/aesop.py`, `tests/aesop_time.py`
- older checkpoints bind their recorded compiler/source hashes, not the current source by implication

complete source-current SDK packaging, offline acceptance, relocation/backend-failure testing and native Windows qualification remain separate release work

## frontend embedding

the scanner/parser C ABI is version 2, source-byte and filesystem entry points both use Aesop, dialect-selecting exports were removed, integrations must rebuild against the current headers rather than loading a version-1 frontend by accident
