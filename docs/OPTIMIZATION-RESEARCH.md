# Optimization research log

Checked 2026-11-06. Research guides experiments; it is not proof of improvement.
Prefer primary specifications/vendor documentation over tips or search snippets.
Retain correctness, bounded resource use and Linux/Windows qualifications.

## File-copy candidates

1. Linux `copy_file_range`: can avoid a userspace round trip and may permit
   filesystem acceleration. The manual explicitly permits short copies, lists
   unsupported/cross-filesystem errors, warns about sparse-hole expansion, and
   documents historical false-success bugs. Therefore do not replace the
   portable streaming implementation blindly. A future fast path needs a
   carefully tested fallback after partial progress, error/offset tests, and
   filesystem-specific measurements. Not implemented in 0.22.
   Primary source: https://man7.org/linux/man-pages/man2/copy_file_range.2.html
   (man-pages 6.19; both chunks read).
2. Windows synchronous ReadFile: buffer lifetime must cover the operation, and
   callers must use the returned count. Awl's current synchronous, bounded
   read/write contract is intentional; overlapped I/O would require a different
   lifetime/cancellation/resource model rather than just another open flag.
   Primary source:
   https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile
3. Windows FILE_FLAG_SEQUENTIAL_SCAN: Microsoft describes potential sequential
   read benefits but cautions that random seeking may not give optimal caching.
   Awl's general file handles support seeking, so do not force a sequential
   hint into every file_open. A future explicit hint or copy-specialized path
   needs native Windows measurements. No native Windows performance claim.
   Primary source:
   [1](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
4. Portable buffer-size experiment: compare 16 KiB, baseline 64 KiB, 256 KiB and
   1 MiB in actual compiled Awl kcopy, checking bytes and preserving exclusive
   creation/flush/checked-close semantics. Randomize run order, separate build
   time, and report cache/filesystem limitations and memory trade-offs. Do not
   change the shipped baseline on one noisy or Linux-only result.

The existing seven-sample warmed full-build/copy benchmark is
`benchmarks/files-latest.json`. Further experiments belong in separate reports;
never silently overwrite a baseline with incomparable measurements.

## Executed buffer experiment

`benchmarks/copy-buffers-latest.json`: four actual compiled Awl variants,
three file sizes, seven timed samples each (84 timed copies plus12warmups),
randomized order and SHA256 byte checks. On this one warmed Linux host,32MiB
medians were49.835ms/46.767ms/46.120ms/51.020ms for16/64/256/1024KiB buffers.
The256KiB case used4x buffer memory for only a1.014 baseline/variant time ratio
in that workload; this is not a statistically established universal gain.
The1MiB buffer was slower here, illustrating why larger is not automatically
better. No native Windows experiment was performed. **Retain64KiB**; keep these
results separate from the prior benchmark and do not generalize warm-cache
filesystem results to cold disks or other hosts. This experiment changed only
temporary source copies, not release code or its acceptance-tested archives.

##0.23 bounded drawing persistence (2026-11-06)
Read RFC1950 section2.2 for the Adler-32 sums/byte order, Linux open(2), and
Microsoft CreateFileW. Exclusive create is the deliberate no-overwrite policy;
we do not infer atomic replacement or universal durability. A fixed1160-byte
checksum can defer modular reductions safely (a<=295801,b<=171713060); this is
not valid for arbitrary length without a new bound. Independent zlib oracles
and baseline-vs-tail-reduction measurements must accompany that optimization.
Sources: https://www.rfc-editor.org/rfc/rfc1950 ;
https://man7.org/linux/man-pages/man2/open.2.html ;
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew .

Also fetched the authoritative current zlib adler32.c implementation:
https://raw.githubusercontent.com/madler/zlib/master/adler32.c . Its NMAX5552
bound and once-per-block reductions corroborate the general deferred-reduction
strategy. Our code uses a stricter, independently calculated fixed1160-byte
initial-state bound and retains Awl checked buffer/integer operations. We did
not copy the C macros/unrolling or add zlib as a product dependency. No general
variable-length checksum API or universal performance benefit is inferred.

Executed `benchmarks/persistence.py`: randomized7samples/variant,1warmup each,
20000mutated1160-byte checksums/process. On this Linux host, per-byte reduction
median169.448316ms vs bounded-tail94.785101ms, ratio1.78771,44.06%less elapsed
in this micro-workload. Source matched totals and independentzlib file oracles.
No whole-save/fsync, GUI, Windows or universal throughput claim. Complete warmed
three-module Pixelboard compile median955.883546ms across7timed full commands
(`benchmarks/persistence-build-latest.json`), not comparable to smaller workloads.

## Requested language redesign research (2026-11-06)
Fetched the primary Rust Vec documentation, capacity/reallocation discussion:
https://doc.rust-lang.org/std/vec/struct.Vec.html . Distinguish length/capacity,
explicit reserve, amortized append and the invalidation hazard of live slices.
Do not freeze a growth factor on someone else's benchmark. General Awl slices,
generic arrays and concurrent runtime changes are PLANNED, not delivered by the
native structural/export checker. Graph deduplication in that prototype uses
canonical identities and a map; source reads are capped at1MiB+1 independent of
metadata so a growing file cannot cause an unbounded stream read. Test both
functional errors and sanitizer mutations before any production integration.

## Production noncapturing helper lowering (2026-11-06)
Re-read primary GCC documentation:
https://gcc.gnu.org/onlinedocs/gcc/Nested-Functions.html . GNU C nested functions
are an extension (not GNU C++), use lexical outer-variable access, and taking an
address may need trampolines; captured storage must not outlive its scope. Awl
therefore does NOT implement source helpers by emitting GNU nested C or executable
stack trampolines. This first production slice lifts only NONCAPTURING helpers to
ordinary typed functions, passes explicit arguments, keeps defining-module lookup,
and verifies lexical call permissions separately. This is a portability/lifetime
choice, NOT a measured closure performance win. Real captures need an explicit
environment/borrow/lifetime design; never replace them with importer names or
pointers to expired parent locals. Full compile measurements, not the separate
structural benchmark, belong in benchmarks/next-production-latest.json.

## f64 literal validation and module initialization (2026-11-06)
Primary C++ draft reference checked: https://eel.is/c++draft/charconv.from.chars .
from_chars uses the C-locale pattern, fixed formatting excludes exponents, and
reports range/invalid-argument without throwing. Awl first validates a bounded
plain-decimal grammar then requires full conversion and finite result, avoiding
locale-dependent strtod and preventing arbitrary text reaching generated C.
This is validation, not a claim to replace libm or provide exact decimal arithmetic.
Module init is explicit: canonical files dedup, dependency postorder, source-order
scalar initializers with read-before-init rejection; verifier rechecks metadata
order/coverage and permissions. No callbacks, ambient platform/user calls or
implicit zero-value reads in initializers. Performance must be measured separately
from the prior function-only compile benchmark; do not infer a speedup.

## ASDK Beta static executable footprint
Reviewed GCC optimization guidance and GNU ld driver-option/section elimination
documentation (https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html and
https://sourceware.org/binutils/docs/ld/Options.html). The contributor builder now
has an **optional Linux-only** `--gc-sections` setting for the standalone executable
(`-ffunction-sections -fdata-sections -Wl,--gc-sections`), not the shared library.
For identical ASDK source, static -O2/strip produced 2,692,400 bytes without it and
2,213,160 with it. This eliminates unused sections; it does not add a runtime
compiler dependency. Shared frontend library is byte-identical to the previous
checkpoint. 62 real CLI/backend cases and 62 native sanitizer cases, plus 47/65
normal regression cases, pass. Section layout/build cost may change; no runtime
speedup claim and no global default change. New Hello-project command timings are
in benchmarks/ASDK-beta-latest.json, not comparable to older two-file workloads.

## native stream and environment decisions

reviewed primary linux references before implementation

- https://man7.org/linux/man-pages/man2/read.2.html
- https://man7.org/linux/man-pages/man2/write.2.html
- https://man7.org/linux/man-pages/man3/getenv.3.html
- https://man7.org/linux/man-pages/man3/fflush.3.html

short positive reads aren't eof, short writes need a caller loop, only a failed
no-progress `EINTR` is retried by the runtime, would-block is explicit, not a busy
retry loop, default `SIGPIPE` remains unchanged rather than being silently
replaced with process-global signal policy

raw writes flush pending stdio output first, explicit stream flush only drains
user-space buffering, it isn't durable storage, environment reads copy into a
checked reusable buffer rather than exposing libc pointers or allocating a
process-lifetime string per chunk, missing and empty values stay distinct

`kpipe` uses one reusable 64 kib buffer and ordinary Awl short-write loops,
copy mode avoids per-byte work, ascii modes intentionally scan each byte,
whole build/process pipe timings are in benchmarks/streams-latest.json, they're
not pure syscall throughput or a speedup over an equivalent older program

short counts, interrupted calls, zero progress, flush failure and environment
bounds are injected into actual emitted c, genuine closed/nonblocking/broken
pipes are tested separately, linux is the active target, windows isn't claimed

## measured standalone lto, typed-vector checkpoint

GCC LTO overview, https://gcc.gnu.org/onlinedocs/gccint/LTO-Overview.html, explains cross-unit GIMPLE optimization and plugin linking, fetched2026-11-06

optional linux contributor --lto retains O2, strip and section gc, current compiler2254120 →2213160 bytes,40960 saved, enough to retain new source/evidence within the whole-home budget without deleting protected archives or old evidence

11 warm subprocess samples each, check3.710 →3.636ms, emit-c4.318 →4.001ms, exact output matched, tests/typed-vectors-lto.json records hashes, this tiny sequential noisy run is not a general speedup claim, gcc serialized11 LTRANS jobs, build time/toolchain compatibility remain trade-offs, not enabled by default or qualified on windows

## optional compact shared frontend

GCC optimization options, https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html, fetched2026-11-06, Os trades some execution speed for smaller code, no fast-math or unsafe semantic relaxations enabled

measured on identical pre-tcp sources, O3 shared695504bytes versus Os/LTO432792bytes,262712bytes saved, optional --compact-shared is linux-only and isn't default, no protected archives or historical evidence removed to fund new features

101 warm in-process ctypes ksort parse/check/verify/emit/free cycles,2.780ms →3.356ms median, identical emitted-C hash, this selected workload is slower, the tradeoff is footprint under the whole-home cap, not a speedup, standalone remains O2/LTO, new tcp code adds its own size, tests/net-compact.json retains original hashes

full parser/frontend ABI regressions qualify the selected compact library, native windows and other compilers aren't claimed
