# Typed reusable UTF-8 builders — 0.8.3-dev

Implemented experimental native feature. A builder is **manually released,
copyable checked resource**, not an owning/linear/borrow-checked type.
It supports repetitive text construction without consuming immutable-string
region allocations, provided the loop does not create dynamic strings/snapshots.
This does NOT replace the existing string lifetime policy.

## Model and guarantees

`spool` is distinct from i64, buffers, windows and string. There is no
integer conversion, arithmetic, equality, field access or ordinary `print` for
this type. It can pass through modules/functions/structs/unions. The private C
representation is an eight-byte/alignment-eight identity wrapper, independently
accounted for by checker/verifier. Source programs cannot manufacture an identity
from an integer. Copying a descriptor aliases the same mutable builder; it does
not transfer ownership or copy the contents.

Builders have a fixed UTF-8 byte capacity. `clear` sets byte/scalar lengths tozero
without reallocating; release frees the payload immediately. No raw pointers,
mutable views or borrowed strings escape. Appending accepts valid immutable text,
checked Unicode scalars or decimal integers, preserving valid UTF-8 including
embedded NUL. Scalar counts are not grapheme counts; normalization is absent.
`clear`/release do not promise secure erasure of secrets.

Copies become stale after release. All operations except `valid` check the live
identity before accessing storage and trap on invalid/released identities, with
`Awl text builder trap`. Slot reuse never reuses an identity; exhaustion fails
allocation instead of wrapping. `valid` safely returnsfalse for unavailable or
released descriptors. This prevents stale aliases from reaching a new allocation,
but it is **runtime checking, not use-after-release rejection by the compiler**.
The allocator/table are single-threaded; safe concurrency is not implemented.

## API

| Intrinsic | Exact arguments → result | Behavior |
|---|---|---|
| `spool.new` | i64 → spool | Fixed byte capacity; unavailable descriptor on bad capacity/limit/OOM/cleanup-registration failure |
| `spool.valid` | spool → bool | Live-resource test; safely accepts unavailable/stale handles |
| `spool_free` | spool → unit | Immediate payload reclamation; invalid/double release traps |
| `spool.clear` | spool → unit | Keep capacity, reset content; no allocation |
| `spool.capacity` | spool → i64 | Capacity in bytes |
| `spool.bytes` | spool → i64 | Current UTF-8 bytes |
| `spool.length` | spool → i64 | Current Unicode scalars |
| `spool.append` | spool,string → i64 status | Append immutable text |
| `spool.codepoint` | spool,u32 → i64 status | Append one valid Unicode scalar |
| `spool.i64` | spool,i64 → i64 status | Exact signed base10, including minimum i64 |
| `spool.u64` | spool,u64 → i64 status | Exact unsigned base10, including maximum u64 |
| `spool_print` | spool → i64 status | Write bytes + newline and flush; preserve embedded NUL |
| `spool.snapshot` | spool → string | COPY into existing immutable string region; see warning below |

Statuses: 0 success,1 insufficient remaining capacity,2 invalid Unicode scalar,
3 stream/formatting failure. Invalid scalar takes precedence over capacity for
`codepoint`; invalid handle always traps first. Failed appends do not change
content or byte/scalar lengths. Printing can have partial external output on I/O
failure and does not promise transactional output or reset a failed stream.
Allocation failure is signalled through `valid`, not a status integer; its exact
cause is not distinguished yet. There is no hidden capacity growth.

The source module `examples/builders/text.aw` demonstrates ordinary Awl tagged
`Status`/`Created` results, including explicit unavailable allocation. It is an
example reusable module, not a built-in generic Result or complete standard library.
Calls may ignore statuses; no must-use/error-propagation analysis is claimed.

## Limits and complexity

At most64 live builders,16MiB capacity each,64MiB live total payload. Limits are
separate from string/buffer/window budgets and not a whole-process sandbox.
Zero capacity is valid (one allocator byte of overhead, empty text only). Table,
allocator metadata and temporary decimal buffers are additional. Payload is
returned to the allocator immediately on release, not necessarily to the OS/RSS.
Remaining builders are cleaned on normal exit. Abnormal exit relies on the OS.

Handle lookup is a bounded64-slot scan. Clear/query/release are independent of
text length after lookup. Append/snapshot cost O(bytes copied); scalar encoding
and64-bit integer formatting have bounded input sizes. Awl builder code performs no payload or string-region allocations
in append/scalar/decimal/clear/print after creation; libc stream/formatting
implementation buffering is outside that guarantee. New/release involve the system
allocator. There is no claim of lock freedom, real-time latency or bounded OS
allocator fragmentation.

**Snapshot warning:** a snapshot has separate backing storage, so it survives
builder mutation/release and cannot dangle, but each nonempty snapshot consumes
an allocation in the existing64MiB/65,536-allocation process-lifetime string
region. Ordinary string concatenation and integer-to-string calls still consume
that region too. Repeated snapshotting is NOT a constant-memory workload. For
repeated output, append numeric/scalar values directly and print the builder.
Safe general owned strings, containers and borrow/lifetime checking remain next.

## Example and actual evidence

Run `bin/kcc run examples/builders/main.aw`. It constructs UTF-8 text, handles an
invalid scalar via a tagged error, performs100,000 clear/append/integer updates
using one builder, prints the final result, then releases it.

`tests/test_builders.py` includes capacity/zero/NUL/Unicode/property tests, snapshot
lifetime/copy tests, static type separation, live table/payload recovery, stale
aliases, recoverable `/dev/full` failures,100,000 create/release cycles and one
million clear/reuse iterations at O0/O3. A test-only emitted-C translation unit
injects allocation/atexit failures and identity exhaustion, and directly verifies
live builder payload returns tozero and string-region counters remainzero through
reuse. This introspection is NOT an exported mutation API. Native frontend and
emitted-C sanitizer results, build/runtime samples and final artifact acceptance
are recorded separately; no formal safety proof or production heap is implied.

Subsequent0.8.4 supports scoped `defer spool_free(b)` on normal exits/returns (SCOPED-CLEANUP.md). Captures still alias; this is not static ownership and does not change snapshot/string storage rules.
