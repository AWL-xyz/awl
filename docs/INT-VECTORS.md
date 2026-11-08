# Growable integer vectors and a native CLI (0.19)

`int_vector` is a native-project opaque growable **i64** container, not a generic
Vector[T], slice, pointer or reference type. Example:

```
scoped values:int_vector=int_vector_new(0)
if not int_vector_valid(values) then return 3 end
if not int_vector_push(values,42) then return 3 end
print(int_vector_get(values,0))
```

## API and failure contract

| Intrinsic | Result / meaning |
|---|---|
| int_vector_new(capacity:i64) | int_vector; unavailable handle on negative/over-limit capacity, table/payload limit, ID exhaustion or allocation failure |
| int_vector_valid(v) | bool; false for unavailable or released handles |
| int_vector_length(v), int_vector_capacity(v) | i64 |
| int_vector_reserve(v,capacity) | bool; never shrinks; negative/over-limit or allocation failure returns false |
| int_vector_push(v,value:i64) | bool; append with geometric growth |
| int_vector_insert(v,index,value) | bool; shift right and insert, index in [0,length] |
| int_vector_get(v,index) | i64 copy; index in [0,length) |
| int_vector_set(v,index,value) | unit; index in [0,length) |
| int_vector_pop(v) | i64; requires nonempty vector |
| int_vector_remove(v,index) | i64 removed value; shifts left, index in [0,length) |
| int_vector_clear(v) | unit; length becomes zero, capacity reused |
| int_vector_free(v) | unit; manual release, not for scoped/borrowed owners |

Except valid, operations require a live handle. Stale/unavailable handles and bad
indices/empty pop trap before accessing data. **Failed growth preserves length,
capacity and every existing element**, including insert. Invalid indices trap,
not a recoverable false result. Check validity before operating on new handles.

Capacity starts as requested, automatic growth doubles (zero starts at8), capped
at1,048,576 elements per vector.64live identities;64MiB combined allocated element
capacity, independent of the builder/buffer budgets. Metadata/allocator overhead
is additional. Growth can fail before the element cap due to combined budget or
allocator failure. Reserve never shrinks; clear retains capacity; free releases
payload to allocator, not necessarily to the OS/RSS. ID values never wrap/reuse.
Single-threaded runtime. Process-exit fallback cleanup is not trap unwinding.

Push is amortized O(1) under successful geometric growth; explicit reserve may
copy O(n); get/set/pop O(1), insert/remove O(n). Identity lookup scans at most64
slots. No pointers/views escape, so realloc does not invalidate the identity.
Manual descriptor copies alias; they are not deep copies or independent owners.

## Ownership

Existing scoped/borrow/own/move/owned-return/refill/if/match/loop rules now cover
both spool and int_vector with exact resource-type checking. Mixed-resource
calls work; a builder cannot masquerade as a vector. A scoped vector cannot be
copied, manually freed, stored in an aggregate, passed to an ordinary by-value
parameter or returned as an ordinary result. Synchronous borrowed operations may
mutate/grow it; these are NOT exclusive Rust-style borrows. No async retaining use.

Use an explicit owning result to return a vector factory. Consume with move;
refill only a definitely-empty binding. Entry-preserving loops retain their prior
proof obligations. All release registrations share existing64/scope,256/project
budgets. Ordinary manual arrays/structs of descriptors still alias and do NOT gain
aggregate ownership. Manual defer int_vector_free captures a descriptor once.

## Integer command-line input

`arg_count()->i64` counts user arguments, excluding executable name.
`arg_i64_valid(index:i64)->bool` checks zero-based index and strict signed decimal
i64; `arg_i64(index)->i64` traps on invalid index/text/overflow. Optional +/-, ASCII
digits and leading zeroes accepted; whitespace, empty/sign-only strings, Unicode
digits and overflow rejected. INT64_MIN/MAX supported without signed overflow.
No argv pointer escapes; no string allocations required. This is NOT a general
process/file/stream/UTF8-argument API. Build then invoke the executable; the compiler
run command has not gained argument-forwarding syntax.

## Application: intstats

```
kcc build examples/apps/intstats/main.aw -o intstats
./intstats 42 -7 19 0 42 -9223372036854775808 9223372036854775807
```

The Awl-only modular application validates external data, grows a scoped vector,
heap-sorts via a borrowed helper in O(n log n), and prints count/min/max/sorted
values. Exit0 success,2usage/invalid argument,3allocation/growth failure. It neither
loads files nor implements network services/browser applications. OS argument-size
limits apply; this is a small useful CLI/data-tool example, not general app readiness.
