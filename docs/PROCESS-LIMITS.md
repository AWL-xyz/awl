# Native process/resource hardening — 0.7.1 engineering preview

This increment hardens the native Linux build/run driver. It adds no language constructs and does not replace the self-contained Zig/LLVM/musl bundle with host tools.

## User controls

```sh
./bin/kcc build program.aw -o program --build-timeout 120 --build-memory-mib 4096
./bin/kcc run program.aw --run-timeout 5
```

| Control | Default | Accepted range / scope |
|---|---:|---|
| `--build-timeout` | 120 seconds | 1–3600; backend subprocess wall time, not frontend/filesystem setup |
| `--build-memory-mib` | 4096 MiB | 512–16384; per-process virtual address space, inherited by backend descendants |
| `--run-timeout` | 0 (unlimited) | 0–86400; run only; applies after compilation |
| Backend file size | 256 MiB | Fixed per-file `RLIMIT_FSIZE`, not total disk/cache usage |
| Backend open descriptors | hard cap 32768 | Existing lower hard limits remain effective |
| Child core dumps | disabled | Backend and generated program |

Memory/file/core limits do not raise inherited soft/hard limits. Descriptor handling is intentionally different: the inherited soft descriptor limit is preserved, but Zig may raise it within the capped hard limit, just as it ordinarily does. An initial attempt to hard-cap descriptors at a shell's usual 1024 broke cold libc compilation; fresh-cache testing caught it. The corrected 32768 cap passes offline cold compilation. Existing lower host hard limits can still prevent builds.

A timeout exits **124**. SIGINT/SIGTERM/SIGHUP/SIGQUIT handled during subprocess supervision exit `128 + signal`. Normal program exit codes are propagated, so a program itself can also return those numbers; explicit timeout/interruption diagnostics distinguish the cases. Backend/setup/output validation failures exit 2. Source errors exit 1. Runtime defaults remain unbounded except for disabled core dumps; no run-memory cap is claimed.

## Process lifecycle

Implementation: `compiler/native/kbuild.cpp` and `kbuild.h`.

- Each backend or generated program starts in its own process group. Child signal dispositions/masks are reset; backend environment remains restricted and compiler lookup remains prefix-relative.
- The parent supervises with a monotonic deadline, `waitid` and `sigtimedwait`, not shell utilities or polling helper programs.
- Interruption/deadline expiration signals the group, allows a 500 ms grace period, then sends SIGKILL. A child becoming unresponsive to SIGTERM cannot indefinitely defeat this normal-process timeout.
- KCC temporarily acts as a Linux child subreaper. Remaining group descendants are killed/reaped even if the root child exits first.
- Group signals are sent while the root's PID is still reserved using `WNOWAIT`, avoiding a signal-after-PID-reuse race. Handlers, masks and subreaper state are restored afterward.
- `PR_SET_PDEATHSIG` gives the direct child a best-effort SIGKILL on parent death. This is not a guarantee for all descendants after unhandleable parent termination.
- Linux `close_range` closes inherited descriptors above stderr before exec, including the source stream and caller-owned descriptors. Denial/unavailability fails closed; the tested kernel is 6.1.189.

Private temporary and output-staging files are removed after handled failure/timeout/interruption. Existing output is preserved when compilation fails or cancellation is observed before publication. A build that has already atomically committed is not rolled back if cancellation races with completion.

## Output checks and permissions

Successful tool exit is no longer sufficient to publish an artifact. The driver checks a bounded ELF64 little-endian x86-64 executable header/program table, load-segment ranges and executable entry mapping, and rejects dynamic/interpreter program headers. Empty, malformed, wrong-machine and symlinked outputs fail without replacing the previous executable. This is a sanity check, not a full ELF/security verifier or proof of generated-program correctness.

Built executables respect the caller's umask rather than always being made world-readable/executable. Temporary run artifacts are owner-only executable inside a private directory. Trusted installation resources and normal output-directory permissions are assumed; this is not a defense against a malicious same-user writer racing filesystem operations.

## Executed evidence

Nine new unit-test methods cover:

- a hung three-process backend tree that ignores termination signals;
- SIGINT/SIGTERM/SIGHUP/SIGQUIT cancellation and descendant reaping;
- root exit with surviving descendants;
- actual address-space limit enforcement using mmap, observed file/core/descriptor limits, and inherited FD 200 closure;
- empty/symlinked output and seven ELF metadata corruptions;
- umask behavior and invalid option bounds;
- timeout of an actual generated infinite Awl program.

The same failure-probe suite passes against an **ASan/UBSan-instrumented native driver**. Tests substitute a native probe only inside private fixtures; the product exposes no fault-injection or mutation interface. Reports: `tests/driver-limits.txt`, `driver-limits-sanitized.txt`, `bundle-driver-sanitizer.json`.

All **266 distinct methods** pass in each regression configuration. The offline, unprivileged, no-host-tools isolation test now covers **20 commands**, including a real run timeout and option rejection, in addition to the existing 348 integer checks, traps, relocation and missing-resource checks. The bundled LLVM/musl runtime oracle still passes 1,262 outputs at each O0/O3.

## Limits of these limits

These are operational controls, **not a sandbox or safety proof**. Address-space limits apply to each process, not aggregate process-tree memory. File size is per file, not an aggregate cache quota. Descendants that deliberately escape the process group are not contained. Unhandleable parent signals, kernel-uninterruptible I/O, restrictive syscall policies and privileged/malicious native tools are not covered by a universal cleanup/deadline guarantee. Frontend input budgets remain separate; generated programs still lack ownership checking.

Cgroup-level aggregate budgets, cache eviction/integrity, broader kernel/CPU/distro/Windows validation, signing/reproducibility and security review remain open. No general build-speed or generated-program performance improvement is claimed for this hardening increment.
