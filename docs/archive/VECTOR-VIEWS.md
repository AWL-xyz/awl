# checked vector views, source candidate

this implementation is in compiler source, not the published Linux0.25 SDK or older Windows preview, the retained release binaries and archives are unchanged, contributor qualification uses an externally staged candidate compiler

## API

```text
func first(values:view<text>): text
    return view.get(values, 0);
end;
func main(): i64
    @s values vector<text>: vector.new<text>(2);
    if not vector.valid(values) { return 9; };
    if not vector.push(values, "hello") { return 9; };
    @p window: vector.view(values, 0, 1);
    print(first(window));
    vector.set(values, 0, "owl");
    print(view.get(window, 0));
    vector.clear(values);
    print(view.valid(window));
    return 0;
end;
```

`text` aliases the internal `string` element type, all11 existing vector elements work, i8/i16/i32/i64/u8/u16/u32/u64/bool/f64/text

| operation | result | behavior |
|---|---|---|
| `vector.view(owner,start,count)` | `view<T>` | checked, nonallocating range over an existing typed vector |
| `view.valid(window)` | `bool` | false for an expired owner, changed structural epoch, wrong kind or malformed range |
| `view.length(window)` | `i64` | validates the descriptor before returning its fixed range length |
| `view.get(window,index)` | `T` | validates owner/epoch/kind/range and index, then copies one scalar/text value |
| `view.slice(window,start,count)` | `view<T>` | checked, nonallocating subview relative to the existing range |

indices/counts are i64, negative or out-of-range construction, subviews and element access trap, empty ranges at the end are valid, there is no `view_set` or `view_free`

views are copyable values, arguments/results and fixed arrays may contain them, borrowed vector parameters can return views, moving an owner without destruction or structural mutation preserves its views, returning a descriptor does not retain its owner

## live data, conservative invalidation

`vector.set` and `vector.swap` remain visible through live views without invalidation, views are read-only access paths, not immutable snapshots

successful push/pop/insert/remove, a shrinking truncate, clearing nonempty storage, actual reserve growth and owner destruction invalidate every prior view of that owner, invalidation also applies to subviews and descriptor copies, even when their particular range would otherwise remain in bounds

failed allocations/reserves and other failed operations preserve existing views, equal-length truncate, empty clear and reserve without growth preserve them too, generation wrap traps rather than reviving stale identities

`view.valid` returns false on stale descriptors, other operations trap before touching stale storage, there is no static lifetime inference, borrow checker, mutation-through-view, concurrent-access safety or implicit ownership extension, do not validate once and assume later structural changes are harmless

## representation and cost

one descriptor is32bytes, owner identity, structural epoch, range offset and range length, all four fields use64-bit storage on native and WASI, compile-time C assertions check size/alignment, there is no escaped data pointer

validation and descriptor creation/subdivision are O(1), vector handles already encode a direct64-slot lookup plus monotonically unique allocation identity, an additional per-slot epoch detects structural changes, access still performs kind, epoch, range, index and width checks

view creation/subdivision uses no heap allocation or vector slot, element reads copy one scalar or immutable text descriptor, the owner remains within the existing64-vector/1M-elements-per-vector/64MiB payload limits, text retains the existing process-arena lifetime limits

this adds a constant epoch-update cost to structural vector operations, it does not hoist checks, prove aliasing/lifetimes or support resource/nested/arbitrary generic elements

## executed qualification

- `tests/vector_views.py`,31 checks,11 types, live set/swap, no-op/failure preservation, all invalidators, descriptor copying/returning/arrays, borrowed vector parameters, owner transfer/destruction,400-step independent state model
-981 expected output lines each under native, ASan+UBSan and real Node WASI, plus11 native sanitizer range/stale traps and4 real WASI traps
- `compiler/native/view_test.cpp`,12 independent read-only verifier cases, corrupt element/result/arity/intrinsic/ownership metadata rejected
- `tests/vector_views_runtime.c`,100000 subviews with allocation disabled and no allocator calls, forced allocation-failure rollback, forged descriptor predicates,10000 owner-slot reuses, stale/width/range/epoch-wrap traps under sanitizers
- `apps/logwindow`, real multi-file native file reader, line index and read-only window renderer,104 normal/sanitized tests, bounded to16384 input bytes,4096 lines and4096 bytes per line, UTF-8 plus LF/CRLF/CR handling, unsupported terminal controls rejected
- regressions,62 default syntax cases,187 exported result/config checks,56 strict sanitized typed-vector cases,35 operation/identity cases, full native compiler sanitizer phases are bound by `tests/vector-views-checkpoint.json`

file I/O in logwindow is native-only qualification, this is not a claim that the bounded WASI host supports general file access, the general offline editor's JavaScript interpreter is unchanged

## measurement, not a general speed claim

`benchmarks/vector-views.json` compares consumed runtime-parameterized range scans, same bundled Zig backend and Linux-musl `-O2`, one warmup and five rotating process-inclusive runs,20000 windows per run

| window elements | published0.25 copying median ms | candidate copying median ms | candidate view median ms |
|---|---:|---:|---:|
|16|6.3656|6.3405|0.6561|
|1024|25.6061|26.9529|20.4955|

checksums are independently computed, the tiny-window timing is particularly sensitive to process startup and optimizer transformations, the shared sandbox has visible outliers, candidate copying regressed about5.3% in the1024-element case, don't infer universal gains or Rust/C++ competitiveness from this microbenchmark

## design reference

[C++ working draft, span](https://eel.is/c++draft/views.span), non-owning contiguous ranges and constant-time descriptor operations informed the design, no implementation was copied, Awl deliberately adds checked owner identity/epochs and invalidates more conservatively than C++ span, this is not its unchecked lifetime model
