# typed growable vectors, native Aesop syntax

restricted scalar/text collections are implemented in the development compiler, not arbitrary user generics, not a published release

```Awl
func main(): i64
    @s values vector<f64>: vector.new<f64>(0);
    if not vector.valid(values) { return 9; };
    if not vector.push(values, 1) { return 9; };
    @s copy vector<f64>: vector.slice(values, 0, 1);
    if not vector.valid(copy) { return 9; };
    vector.set(values, 0, 2);
    print(vector.get(copy, 0));
    return 0;
end;
```

copy still contains 1, the source and destination own independent vector payloads

## types and operations

`vector<T>` accepts i8/i16/i32/i64, u8/u16/u32/u64, bool, f64 and text, string is the existing internal spelling of text

| operation | result and contract |
|---|---|
| `vector.new<T>(capacity)` | vector<T>, unavailable handle on invalid capacity, slot exhaustion or allocation failure |
| `vector.valid(v)` | bool, false for unavailable/stale handles |
| `vector.length(v)`, `vector.capacity(v)` | i64, logical elements vs allocated elements |
| `vector.reserve(v,capacity)` | bool, never shrinks, failure preserves contents/length/capacity |
| `vector.push(v,value)` | bool, amortized growth, false leaves the vector unchanged |
| `vector.insert(v,index,value)` | bool, insertion index includes length, failed growth preserves state |
| `vector.get(v,index)` | T, checked element access |
| `vector.set(v,index,value)` | unit, checked replacement |
| `vector.pop(v)` | T, removes the last element |
| `vector.remove(v,index)` | T, removes and shifts subsequent elements |
| `vector.clear(v)` | unit, sets length to zero, retains capacity |
| `vector.slice(v,start,count)` | vector<T>, independent copied payload, unavailable on allocation failure |
| `vector_free(v)` | unit, explicit release for manual handles only |

invalid/stale/type-mismatched handles and invalid indices/ranges trap, empty pop/remove trap, check length before access, zero-count slices still validate the source and range

value inputs require the exact element type, f64 accepts compatible unquoted integer literals, typed integer variables and explicitly suffixed integers aren't silently converted, use explicit conversions

## ownership and limits

explicit `@p scoped name vector<T>:` registers validity-guarded automatic normal-exit cleanup, fresh constructors and slice copies are admissible, existing borrow/own parameters, move, owned returns via move, and definitely-empty owner refill work with vectors

scoped handles can't be copied, manually freed or deferred for a second release, borrows are synchronous shared mutable access, not exclusive references, manual explicitly typed handles retain runtime-checked alias semantics and can use `defer vector_free(v)`

all typed specializations share 64 slots and 64 MiB of reserved payload, each vector holds at most 1048576 elements, growth starts at 8 and doubles up to that cap, ids aren't reused, exhaustion fails closed

text elements copy immutable string descriptors, strings use the existing process-lifetime text storage, freeing/clearing a vector doesn't reclaim those strings, this isn't reclaimable owned text, trap unwinding, nested/resource-element generics or borrowed slices

fixed arrays and the older i64-only int_vector remain supported, the browser editor runtime doesn't implement typed vectors, linux native is tested, windows qualification remains deferred

## useful workload

`examples/apps/ksort` is a real two-file manifest project, stable bytewise UTF-8 line sorting and optional `--unique`, bottom-up merge sort uses a detached vector scratch copy, private module helpers retain their defining-file context

input is bounded to 1 MiB and 32768 lines, LF separates lines, CR and NUL remain data, an unterminated final line is accepted, empty input yields no output, output normalizes each line to a final LF, this isn't locale-aware collation, an external-memory sorter or a reusable parser Package

allocation/input/argument failures exit nonzero, existing print failures can trap, SIGPIPE policy remains unchanged, no transactional output guarantee

## research and evidence

Rust Vec documentation distinguishes length/capacity and borrowed slices, Awl's slice operation deliberately copies instead, malloc/realloc documentation requires checked allocation sizing and preservation of the old allocation on failure

- https://doc.rust-lang.org/std/vec/struct.Vec.html
- https://man7.org/linux/man-pages/man3/malloc.3.html
- tests/typed_vectors.py, tests/vectors_faults.c and compiler/native/kgeneric_test.cpp
- tests/typed-vectors-checkpoint.json, current binary/source/evidence binding
- benchmarks/typed-vectors-latest.json, whole-command timings, not pure allocator throughput

## checked fast access and in-place operations

vector handles now route in O(1) while retaining complete identity/kind checks, typed get/set additionally validate element width and use fixed-size copies, no stale/bounds/overflow checks were disabled

`vector.swap(v,first,second)` validates both indices before swapping without heap allocation, equal valid indices do nothing, invalid indices trap

`vector.truncate(v,length)->bool` keeps capacity, invalid negative/growing lengths return false unchanged, equal/shrinking lengths succeed, this applies only to the existing scalar/text element set, see [performance and benchmark limits](PERFORMANCE.md)

## checked non-owning views, source candidate

`vector.slice` still allocates and copies, the separate `vector.view` and `view<T>` API provides runtime-checked zero-copy read-only live ranges in current compiler source, not the published SDK, see [VECTOR-VIEWS.md](VECTOR-VIEWS.md) for invalidation, tests, costs and limits
