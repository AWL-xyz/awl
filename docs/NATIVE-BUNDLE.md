# Current engineering milestone: 0.22.0-dev

Complete merged Linux and Windows-native engineering bundles include their own
pinned backend/linker/libc/header/license resources. No base/update overlay or
end-user Python/SDK/compiler download is needed. Linux engineering acceptance and
Windows preview acceptance are separate; real Windows-host backend execution is
not established under Wine. See tests/files-release-acceptance.json for exact
artifact status when present, and FILES.md for new APIs/apps.

# Awl-only Linux bundle — current complete native distribution

## What now works

The previously unmet download-only workflow is implemented and locally validated for the **Linux x86-64 engineering bundle on kernel 6.1.189**:

```sh
tar -xJf Awl-0.22.0-dev-linux-x86_64.tar.xz
cd Awl
./bin/kcc run examples/hello.aw
./bin/kcc build examples/results.aw -o results -O 2
./results
```

The installed path requires no Python, host C/C++ compiler, separately installed linker, SDK, development headers or network downloads. The bundle includes a static native KCC plus native code-generation/linking/runtime resources. It is relocatable and usable without administrator privileges. This is not a production-safety certification or a claim of support for every Linux kernel/distro/CPU.

See [BUNDLE-README.md](../BUNDLE-README.md) for end-user commands, baseline/filesystem requirements, disk/cache cost and limitations. The implemented subset now includes modules, bounded resource/ownership rules,
vectors, strict text arguments, regular files and native GUI/CLI examples.
Generics, richer aggregates, networking/concurrency, browser integration and a
production toolkit remain future work. Windows has a native engineering preview;
ARM is not implemented.

## Backend decision

The transitional C11 emitter is retained, but its consumer is now **shipped inside Awl**, not selected from the OS:

1. Native C++ scanner/parser/checker/independent verifier retain native arenas.
2. The verified native emitter produces bounded C11 in a private temporary directory.
3. KCC invokes its own `libexec/zig/zig cc` by absolute prefix-relative path.
4. Pinned Zig **0.15.2** supplies integrated Clang/LLVM/LLD **20.1.2**, musl/startup sources, headers and compiler-runtime resources.
5. The output targets static `x86_64-linux-musl`, baseline CPU, selected O0–O3; preview binaries have no debug symbols.

KCC itself is built with the same bundled toolchain and static musl/libc++, avoiding host glibc/libstdc++ redistribution/runtime dependencies. The official Zig executable is also static. No external clang/ld/ar, shell script or Python interpreter is installed or needed in the product path.

This chooses a larger but complete upstream bundle over prematurely implementing a custom ELF linker or borrowing host sysroots. It reuses tested C emission and mature native codegen while a direct Awl-to-LLVM IR backend remains unimplemented. Awl is not self-hosted: C++ implementation and native operation are distinct from implementation in Awl.

## Driver guarantees and boundaries

`compiler/native/kbuild.cpp` locates resources from the running executable, not the working directory or PATH. It supplies an explicit Zig library directory and a restricted child environment, ignoring host `CC`, header/library paths and Zig resource overrides. Missing shipped resources fail; there is no host-tool fallback or runtime download. Compiler subprocess affinity is capped to four available CPUs in this preview.

Temporary directories are private. Generated C and staging files are cleaned up; output is staged in the destination directory and atomically renamed only after successful linking. Source overwrites are rejected, including canonical-path/hard-link aliases. Native run propagates exits and maps signals to `128 + signal`. These are tested behaviors, not a formal filesystem/security proof. Trusted installation resources and normal user cache/temp permissions are assumed. Backend wall/memory controls, cancellation/descendant cleanup, inherited-descriptor closure and bounded static ELF checks are implemented. These operational controls are not a sandbox; see [process limits and boundaries](PROCESS-LIMITS.md).

## Clean-root, offline acceptance evidence

`tests/bundle_isolation.py` prepares a filesystem containing only:

- the Awl bundle;
- source/output files and initially empty cache/temp directories;
- `/proc` in a private PID/mount namespace and `/dev/null`.

There is **no `/usr`, `/bin`, `/lib`, `/lib64`, `/etc`, Python interpreter, shell, host compiler/linker, system headers or libraries** inside the root. The compiler runs as UID 1000 in a private network namespace, not as root. Host Python/sudo/unshare/chroot utilities perform test setup outside this filesystem; none is a compiler dependency inside it.

The acceptance run passes **20 commands**: a cold-cache build and independent execution of its static output, all five examples with explicit output oracles, 348 integer/conversion checks, five arithmetic traps, exit status 37, frontend rejection preserving an existing binary, source-overwrite rejection, missing-resource failure without fallback, relocating the whole prefix into a path containing a space, a real generated-program timeout, and invalid-option rejection.

This is a namespace/chroot test on the recorded host kernel, not a booted VM/distro compatibility matrix or adversarial sandbox certification. Evidence: `tests/bundle-isolation.json`; the actual downloadable archive also passes the same test; its hash and commands are in `tests/bundle-archive-validation.json`.

## Other executed validation

- **266 distinct unit-test methods** pass under each of three configurations: reference defaults, native lexer/parser, and native semantic regression bridge. The nine existing bundle tests and nine new driver-hardening tests use the packaged native compiler in every configuration, not Python adapters. These are repeated configurations, not 798 distinct tests.
- Native bundled codegen produces **1,262 oracle-matched outputs at each of O0 and O3**: 912 generated scalar expressions, 200 exact-width arithmetic cases and 150 union matches. Report: `tests/bundle-runtime.json`.
- New native CLI/process/staging code passes separate ASan/UBSan checks (`tests/bundle-driver-sanitizer.json`). Existing unchanged frontend/verifier/emitter sanitizer evidence remains separate; upstream Zig/LLVM is not instrumented by these tests.
- Previous native-emitted C sanitizer matrices and IR-corruption checks remain finite evidence for the components, not proofs of soundness or security.

CI now includes a separate Linux bundle job, but **remote CI (including system-Clang and Windows matrix jobs) has not run; bundled Clang/LLD 20.1.2 was executed locally**.

## Actual full-build measurements

`benchmarks/bundled-build-latest.json` measures complete source-to-static-executable builds, including startup, frontend, verification, C emission, machine-code generation, runtime resources and linking. It compares the native bundle against a contributor Python reference worker using the **same bundled backend and flags**, not historical GCC timings.

On this host, the latest run measured roughly **35–40 ms warm-cache native builds** for four small examples, versus **100–109 ms** for the reference worker. The first empty-cache native build took **18.1 seconds**, compiling shipped libc/startup/compiler-runtime resources. Nothing was downloaded. The cache reached roughly 87 MiB during the broader isolation run.

Both the cold cost and warm conditions matter. These four small programs are not a representative large-project benchmark. Sampling order alternates; backend affinity is capped, but parent scheduling/frequency/load are uncontrolled. This is not a general speed guarantee or a generated-program speedup claim. Earlier scanner/frontend-only measurements remain historical, not substitutes for this full-build record.

## Packaging and provenance

Contributor entry point:

```sh
# Only contributor packaging may download, and only with this explicit flag.
python3 compiler/package_linux.py --download-toolchain
```

The original upstream archive URL, size and SHA-256 are locked in `compiler/toolchain-lock.json`; the builder verifies them before extraction. It preserves the complete upstream distribution, including source resources and notices, embeds compiler source hashes/build flags, copies validation evidence, normalizes archive metadata and writes a separate SHA-256 file. Normalized metadata does not imply bit-reproducible binaries or a signed release.

Awl's original source is MIT licensed. The bundle retains Zig, LLVM/Clang/LLD, musl, libc++/ABI/unwind and Unicode notices and original upstream resource licenses. This is an engineering preview, not a legal/security audit. Download integrity/provenance are recorded; release signing, reproducibility, broader host testing and hardening remain next steps.
