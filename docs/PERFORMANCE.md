# rust-competitive performance direction

Awl is intended to compete with rust as a native systems language, outperforming optimized C++ and rust on useful workloads is a goal, not a claim that every Awl program is faster or that rust-level breadth/safety is already complete

performance claims need measured equivalent work, consumed results and reproducible optimized builds, safety checks aren't disabled to manufacture wins, all wins and losses belong in the report

## Current source: UTF-8 slicing and decimal arguments

A valid UTF-8 string whose byte and scalar counts are equal is ASCII, so `string.slice` and `string.codepoint` can index it directly. For mixed text, slicing finds the boundaries by skipping the largest of the prefix, slice and suffix; scalar lookup starts at the nearer end. Bounds checks, the 24-byte string ABI and allocation-free slicing are unchanged. The decimal parser now reads either a NUL-terminated argument or an explicitly bounded text slice in one pass, checks the magnitude before it can exceed `u64`, and checks the signed range once at the end.

[The benchmark](../benchmarks/text_runtime.py) builds the same Awl inputs with both compilers and verifies each run's checksum against Python. Medians are from 11 shuffled warm whole-process samples, pinned to CPU 0, Linux x86-64, GCC 12.2 `-O3`, excluding compilation:

| workload | before (`1db2f62`) | after |
| :--- | ---: | ---: |
| ASCII interior slice | 33.521 ms | 2.553 ms |
| Mixed UTF-8 tail slice | 60.131 ms | 3.530 ms |
| Mixed UTF-8 wide slice | 60.151 ms | 3.248 ms |
| Mixed UTF-8 front slice | 8.618 ms | 9.290 ms |
| 19-digit arguments | 135.312 ms | 84.813 ms |
| 1–3 digit arguments | 29.793 ms | 23.579 ms |

These stress tests show the benefit of avoiding long scans. Short slices near the front were about 8% slower on this run, where the new direction choice did not save any scanning. The decimal measurements repeatedly parse existing argv items; they are not end-to-end CSV or cross-language timings. See [the raw samples, input and compiler hashes](../benchmarks/text-runtime.json).

```sh
baseline=$(mktemp -d)
git archive 1db2f62 compiler | tar -x -C "$baseline"
(cd "$baseline" && python3 compiler/build_native.py --standalone --strip)
python3 compiler/build_native.py --standalone --strip
taskset -c 0 python3 benchmarks/text_runtime.py --before "$baseline/compiler/native/bin/acc" \
    --samples 11 --report /tmp/awl-text-runtime.json
```

## Current source: sorting UTF-8 lines

The [shipped sort utility](../examples/apps/sort/) uses `buffer.findbyte` to locate LF with a checked range search instead of reading one byte at a time. It reuses the input buffer to assemble the sorted output, then writes it in batches and retries short writes. The stable merge sort, UTF-8 validation, duplicate handling, and 1 MiB / 32,768-line limits are unchanged.

[The benchmark](../benchmarks/sort.py) runs the old and new applications with identical redirected input and checks every output byte. These are medians of 11 shuffled warm whole-process samples on Linux x86-64, GCC 12.2 `-O3`, with the host's two CPUs available and build time excluded:

| workload | before (`68713be`) | after | speedup |
| :--- | ---: | ---: | ---: |
| 10,000 log-like lines | 10.957 ms | 5.840 ms | 1.88× |
| Same input, `--unique` | 8.636 ms | 5.676 ms | 1.52× |
| Single 1 MiB line with no LF | 7.874 ms | 6.452 ms | 1.22× |

With the harness and child pinned to one CPU, the same cases measured 3.32×, 2.70×, and 1.18×, respectively. Pipe scheduling matters for an app that used to flush every row. These numbers describe the whole utility on this host, not a sort-algorithm speedup or a Rust/C++ comparison. Raw samples, input hashes, and binary hashes are in [the default-affinity report](../benchmarks/sort.json) and [the one-CPU report](../benchmarks/sort-single-cpu.json).

Reproduce from the repository root without switching branches:

```sh
baseline=$(mktemp -d)
git archive 68713be compiler examples/apps/sort | tar -x -C "$baseline"
(cd "$baseline" && python3 compiler/build_native.py --standalone --strip)
python3 compiler/build_native.py --standalone --strip
python3 benchmarks/sort.py --before-acc "$baseline/compiler/native/bin/acc" \
    --before-source "$baseline/examples/apps/sort/main.aw" --report /tmp/awl-sort.json
```

## Current source: replacing text in UTF-8 records

`string.replace` previously made and retained a growing text allocation for each match. It now counts non-overlapping occurrences, checks the exact result size, and copies into one final allocation. If there is no change or the result is empty, it doesn't allocate a result. The same UTF-8 rules and text heap bounds still apply; only the unnecessary intermediate allocations went away.

[The reproducible workload](../benchmarks/text_replace.py) runs the same generated program before and after the change. It reads synthetic UTF-8 log records from stdin, replaces a field value, and writes the resulting text. Python checks the entire output including its byte and scalar lengths. Times below are nine shuffled warm whole-process samples on Linux x86-64, GCC 12.2 `-O3` (build time excluded):

| workload | before | after |
| :--- | ---: | ---: |
| 512 replacements | 8.055 ms | 2.231 ms |
| same input with no matches | 2.296 ms | 2.232 ms |

That is about **3.6× as fast** on the matching workload. A separate input with 8,192 matches is **not timed**: the old runtime hit the text heap limit, while the new runtime completed and matched the oracle. This comparison is against the previous Awl implementation only, not against Rust or C++. See the [raw measurements and toolchain hashes](../benchmarks/text-replace.json).

```sh
python3 compiler/build_native.py --standalone --strip
python3 tests/text_replace.py --sanitize
python3 benchmarks/text_replace.py --before /path/to/previous/acc --report /tmp/awl-text-replace.json
```

The recorded baseline is `b0b0d37`; build both ACC binaries with the same options. Substring search still does candidate byte comparisons, so this is an improvement in result construction, not a guarantee of linear-time substring matching for every pattern.

## Current source: checked 64-bit arithmetic

ACC emits feature-tested overflow intrinsics for `i64` and `u64` addition, subtraction and multiplication. A supporting C compiler can use the CPU's overflow or carry flag rather than separate range checks. Overflow still traps at every optimization level, including signed-minimum negation. The guarded C11 implementation remains the fallback when the intrinsics are unavailable. Compile emitted C with `-DAWL_PORTABLE_ARITHMETIC` to select that fallback explicitly without disabling checks. Division, remainder and other widths are unchanged.

[`benchmarks/checked_arithmetic.py`](../benchmarks/checked_arithmetic.py) compiles the [same signed arithmetic loop](../benchmarks/workloads/checked-arithmetic/) in Awl, C++ and (when `rustc` is installed) Rust, with equivalent checks in the timed loop. On one Linux x86-64 host with GCC 12.2, the median warm whole-process time for five million iterations was:

| implementation | median |
| :--- | ---: |
| Awl before (`20abab5`) | 28.40 ms |
| Awl with overflow intrinsics | 26.89 ms |
| Awl with the portable fallback forced | 28.22 ms |
| C++ with explicit overflow checks | 26.90 ms |
| Rust with overflow checks enabled | not measured (`rustc` not installed) |

That's about **5.3% less wall time** than the original Awl build and effectively tied with checked C++ on this workload. These are nine shuffled samples after warmup, with compilation excluded and both output values checked against a Python oracle on every run. See the [raw report](../benchmarks/checked-arithmetic.json). This is a microbenchmark, not a claim about application performance or relative Rust speed.

Reproduce from the repository root:

```sh
python3 compiler/build_native.py --standalone --strip
python3 tests/checked_arithmetic.py
python3 benchmarks/checked_arithmetic.py --report /tmp/awl-checked-arithmetic.json
```

Pass `--before /path/to/acc` to add a pre-optimization Aesop compiler to the comparison. The same harness includes checked Rust automatically if `rustc` is on `PATH`. The correctness gate covers signed/unsigned boundary and seeded cases at `-O0` and `-O3`, both default and forced portable, under UBSan.

## Historical measurement provenance

this table records the completed pre-rebrand performance experiment, original binaries, reports, source harnesses and photos are immutable in `history/pre-rename-evidence.tar.xz`, the current Awl SDK has fresh correctness/distribution qualification, these timings are not newly measured distribution benchmarks, renaming earns no workload point

## vector runtime improvements

both legacy int_vector and typed vector<T> previously searched up to64slots per access, handles now contain a58bit monotonic allocation serial and6bit slot index, lookup routes directly to one slot and checks the complete identity, typed vectors also check their element kind

zero remains invalid, stale handles never revive after slot reuse, allocation failure doesn't consume a serial, exhaustion returns an invalid constructor result rather than wrapping, the theoretical serial limit is now2^58-1 successful allocations per runtime table

typed get/set wrappers now use fixed element-size copies, with explicit element-width validation before bounds-checked access, this removes variable-size memcpy overhead without removing kind, identity, layout or bounds checks, integer overflow checks remain active

this is still a bounded single-threaded runtime, not a concurrent handle table, arbitrary owned generics or a complete zero-cost ownership model

## executed comparisons

| live vectors | Awl before, ms | Awl after, ms | C++ .at, ms | rust release, ms | rust checked, ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 42.946 | 9.561 | 11.479 | 5.766 | 7.065 |
| 16 | 78.292 | 9.464 | 11.376 | 11.032 | 7.124 |
| 64 | 291.957 | 10.261 | 11.266 | 5.922 | 6.956 |

| native sort, 10000 lines | before, ms | after, ms |
|---|---:|---:|
| sort | 8.704 | 7.552 |
| unique | 9.098 | 7.163 |

source and raw measurements are in `benchmarks/vector_competition.py` and `benchmarks/vector-competition.json`, the earlier index-only experiment is retained losslessly in `vector-competition-indexed.json.gz`

these are7shuffled warm whole-process samples after an excluded warmup, the stress case performs5million indexed updates over4096values, a Python oracle verifies the checksum, input is consumed from argv so the measured result isn't a discarded constant expression

slot-pressure cases expose Awl's resource-table overhead, C++/rust ballast may be optimized away, this isn't a representative ranking of languages, the additional real sort measurement checks10000seeded lines and unique output byte-for-byte

Awl before/after use the same bundled backend with baseline x86-64, static musl and-O3, C++ uses GCC-O3/std::vector::at, rust uses opt-level3 with both default release arithmetic and explicit overflow checks, bounds checks may be optimized away when proven redundant, default C++/rust arithmetic semantics differ from Awl's checked arithmetic

compiler versions, CPU, affinity, flags and every sample are recorded, different backends/libcs and this one machine limit the comparison, rust1.85.1 here isn't a claim about the newest rust compiler, no universal faster-than claim or release acceptance follows from these results

## new collection operations

`vector.swap(v,first,second)` exchanges two elements without heap allocation, both indices are validated before mutation, equal valid indices are a no-op, invalid indices/handles trap

`vector.truncate(v,length)->bool` shrinks without reallocating, negative lengths and attempts to grow return false without changing contents/length/capacity, equal length succeeds, removed scalar/text slots require no destructor, retained capacity can be reused

both operations support the existing11scalar/text element types, see `examples/collections`, no resource-element or arbitrary generic support is implied

35focused operation/layout/identity cases and440078runtime oracle assertions pass under native ASan/UBSan,12WASI cases cover every element type and the same runtime oracle, the oracle explicitly refuses NDEBUG so release compilation can't silently discard its assertions

old browser workbench bytes remain unchanged and bind to the older WASM checkpoint, new vector APIs were executed through the current compiler in Node WASI, not newly qualified in the general editor's browser interpreter

## next work

prove and lower stable borrow views, hoist redundant bounds/identity checks only with lifetime/alias evidence, broaden allocation/string lifetime control, and expand representative application benchmarks, these are future work rather than completed optimizations

workload capability remains22.2%=10/45, faster existing workloads and two collection methods don't earn another domain stage

benchmark methodology reference, [rust black_box documentation](https://doc.rust-lang.org/std/hint/fn.black_box.html), consumed outputs and runtime-dependent data prevent dead-work timing here rather than adding asymmetric barriers to one language

## checked views, source candidate measurement

current source implements32-byte runtime-checked nonallocating vector views, the range-scan microbenchmark and exact limits are in [VECTOR-VIEWS.md](archive/VECTOR-VIEWS.md) and benchmarks/vector-views.json, small-window view paths improved in this run,1024-element candidate copying regressed about5.3% versus the published compiler, shared-host/process noise applies, no universal or Rust/C++ speed claim

identity/epoch/range checks remain enabled, proving safe check hoisting and broader application-level performance remain future work, current workload score is24.4%=11/45, prior22.2% sections are historical
