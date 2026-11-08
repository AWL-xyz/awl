# rust-competitive performance direction

Awl is intended to compete with rust as a native systems language, outperforming optimized C++ and rust on useful workloads is a goal, not a claim that every Awl program is faster or that rust-level breadth/safety is already complete

performance claims need measured equivalent work, consumed results and reproducible optimized builds, safety checks aren't disabled to manufacture wins, all wins and losses belong in the report

## measurement provenance

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

| native ksort, 10000 lines | before, ms | after, ms |
|---|---:|---:|
| sort | 8.704 | 7.552 |
| unique | 9.098 | 7.163 |

source and raw measurements are in `benchmarks/vector_competition.py` and `benchmarks/vector-competition.json`, the earlier index-only experiment is retained losslessly in `vector-competition-indexed.json.gz`

these are7shuffled warm whole-process samples after an excluded warmup, the stress case performs5million indexed updates over4096values, a Python oracle verifies the checksum, input is consumed from argv so the measured result isn't a discarded constant expression

slot-pressure cases expose Awl's resource-table overhead, C++/rust ballast may be optimized away, this isn't a representative ranking of languages, the additional real ksort measurement checks10000seeded lines and unique output byte-for-byte

Awl before/after use the same bundled backend with baseline x86-64, static musl and-O3, C++ uses GCC-O3/std::vector::at, rust uses opt-level3 with both default release arithmetic and explicit overflow checks, bounds checks may be optimized away when proven redundant, default C++/rust arithmetic semantics differ from Awl's checked arithmetic

compiler versions, CPU, affinity, flags and every sample are recorded, different backends/libcs and this one machine limit the comparison, rust1.85.1 here isn't a claim about the newest rust compiler, no universal faster-than claim or release acceptance follows from these results

## new collection operations

`vector_swap(v,first,second)` exchanges two elements without heap allocation, both indices are validated before mutation, equal valid indices are a no-op, invalid indices/handles trap

`vector_truncate(v,length)->bool` shrinks without reallocating, negative lengths and attempts to grow return false without changing contents/length/capacity, equal length succeeds, removed scalar/text slots require no destructor, retained capacity can be reused

both operations support the existing11scalar/text element types, see `examples-next/collections`, no resource-element or arbitrary generic support is implied

35focused operation/layout/identity cases and440078runtime oracle assertions pass under native ASan/UBSan,12WASI cases cover every element type and the same runtime oracle, the oracle explicitly refuses NDEBUG so release compilation can't silently discard its assertions

old browser workbench bytes remain unchanged and bind to the older WASM checkpoint, new vector APIs were executed through the current compiler in Node WASI, not newly qualified in the general editor's browser interpreter

## next work

prove and lower stable borrow views, hoist redundant bounds/identity checks only with lifetime/alias evidence, broaden allocation/string lifetime control, and expand representative application benchmarks, these are future work rather than completed optimizations

workload capability remains22.2%=10/45, faster existing workloads and two collection methods don't earn another domain stage

benchmark methodology reference, [rust black_box documentation](https://doc.rust-lang.org/std/hint/fn.black_box.html), consumed outputs and runtime-dependent data prevent dead-work timing here rather than adding asymmetric barriers to one language

## checked views, source candidate measurement

current source implements32-byte runtime-checked nonallocating vector views, the range-scan microbenchmark and exact limits are in [VECTOR-VIEWS.md](VECTOR-VIEWS.md) and benchmarks/vector-views.json, small-window view paths improved in this run,1024-element candidate copying regressed about5.3% versus the published compiler, shared-host/process noise applies, no universal or Rust/C++ speed claim

identity/epoch/range checks remain enabled, proving safe check hoisting and broader application-level performance remain future work, current workload score is24.4%=11/45, prior22.2% sections are historical
