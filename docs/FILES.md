# Regular files and strict external text — 0.22 engineering API

Awl programs can copy arbitrary binary files and inspect UTF-8 text without a
Python helper, system SDK or external runtime. This synchronous, single-threaded
API targets Linux x86-64 and Windows x86-64. It is **not** a filesystem sandbox,
network API, atomic save API or general owned-string facility

new linux stdin/stdout/stderr byte-stream and environment APIs are documented in
[STREAMS.md](STREAMS.md), the regular-file api itself still only opens regular files

## File handles

| Call | Result |
|---|---|
| `file_open(path:string, mode:i64)` | positive i64 handle, or negative error |
| `file_valid(handle:i64)` | bool; false for errors, stale handles and other domains |
| `file_close(handle:i64)` | 0, or negative error; handle is invalidated either way |
| `file_size(handle:i64)` | current byte size, or negative error; does not seek |
| `file_seek(handle:i64, offset:i64)` | 0, or negative error; absolute byte offset |
| `file_read(file:i64, buffer:i64, offset:i64, count:i64)` | bytes read, 0 EOF, negative error |
| `file_write(file:i64, buffer:i64, offset:i64, count:i64)` | bytes written, negative error |
| `file_flush(handle:i64)` | 0, or negative error; writable file only |

Open mode **0** reads an existing file; **1** exclusively creates a new writable
file and refuses overwrite; **2** creates or explicitly truncates a writable file.
There is no read/write combined mode. Read/write may return **short counts**:
callers must loop, advance the buffer offset and detect lack of progress. A zero
count does no I/O but still validates handles, range and access mode. Size is not
a snapshot. Seek may move past EOF; a later write may make a sparse file.

32 simultaneously open files; monotonically increasing IDs begin at 2^62 and
are never reused. OS descriptors/pointers do not escape. Buffer, window and file
IDs occupy disjoint domains. Handles are manually managed aliases, not an owned
resource kind: copying an i64 does not duplicate the OS handle. Forged/stale file
handles or invalid buffer handles/ranges **trap**, rather than return an OS error.
`file_valid` is a nontrapping probe. Existing buffer limits still apply: 64 slots,
16 MiB per buffer, 64 MiB combined payload. There is no arbitrary pointer access.

`defer file_close(f)` closes at lexical scope exit, including return and loop
cleanup, and intentionally **discards the close status**. Check explicit close
for output errors; do not explicitly close a handle also scheduled for deferred
close. Other deferred releases still require their existing exact unit-returning
allowlist. Normal process exit also attempts to close still-live files. Aborts,
traps, termination and crashes do not provide user-level cleanup guarantees.

### Recoverable error codes

- -1 other OS I/O failure
- -2 not found / missing parent
- -3 already exists
- -4 permission, sharing conflict, read-only media
- -5 invalid path, mode, seek or access operation; insufficient text-write space
- -6 unsupported file type / final symlink or reparse point
- -7 file-handle limit or OS descriptor exhaustion
- -8 disk space, quota or file-size limit
- -9 OS/allocation failure

Normalization is best effort: an OS may reject a directory/reparse point with
access/I/O failure before type inspection. Invalid paths are recoverable; invalid
handle/range use is a program bug. No filesystem deletion/rename, directory
listing, append, locking, cancellation or wall-clock io bound exists here,
stdin/stdout streaming is now a separate linux api in STREAMS.md Flush requests fsync/FlushFileBuffers, **not** directory sync or
an unconditional hardware/power-loss guarantee. Close failures are not retried.

### Paths and safety limits

Paths must be nonempty strict UTF-8, without NUL, at most 4095 UTF-8 bytes. POSIX
uses CLOEXEC, NOFOLLOW and NONBLOCK, verifies a regular file before mode-2
truncation, and creates with permission 0600 subject to umask. Windows converts
UTF-8 to UTF-16 and uses CreateFileW, verifies disk/non-directory/non-reparse type
before truncation, rejects device namespace prefixes and alternate data streams.
Windows extended-length namespaces are intentionally unsupported; ordinary OS
path-length limits still apply. Parent symlinks, mount points, relative paths,
hardlinks and ordinary UNC paths are not sandboxed. An attacker can still race
parent-directory changes; no claim of secure capability-based path resolution.
Windows file handles are non-inheritable. Sharing permits other processes to read,
write, rename or delete; a copy is not a stable snapshot of a concurrently edited
source. Mode 2 is destructive and **not atomic replacement**.

## Strict text arguments

`arg_count()` excludes the executable name; indexes are zero-based.
`arg_text_valid(index:i64)->bool` probes strict external text.
`arg_text(index:i64)->string` validates and makes an immutable copy; invalid text
or index traps with an argument diagnostic. On Linux the probe rejects malformed
UTF-8 and arguments above 1 MiB. On Windows the runtime uses
CommandLineToArgvW/GetCommandLineW and strict UTF-16-to-UTF-8 conversion, not the
lossy narrow CRT argument bytes. The backend links shell32 for this operation.
Existing signed-integer argv APIs retain strict ASCII integer parsing.

## Buffer/text bridge

- `buffer_text_valid(buffer, offset, count)->bool`: strict UTF-8 probe.
- `buffer_text(buffer, offset, count)->string`: validated immutable copy;
  malformed UTF-8 traps. Freeing/mutating the buffer cannot change the string.
- `buffer_write_text(buffer, offset, text:string)->i64`: copies UTF-8 bytes;
  returns byte count, or -5 if remaining capacity is insufficient. On capacity
  failure, no bytes are written. Invalid handles/offsets still trap.

All numeric parameters are i64. Empty text and embedded NUL are valid text data,
although NUL is forbidden in file paths. Validation rejects stray continuation
bytes, truncated sequences, overlong encodings, surrogate scalars and values
above U+10FFFF. Unicode noncharacters are valid scalars. `string_length` counts
Unicode scalars, not graphemes or display cells. Dynamic strings remain a bounded
process-lifetime region (64 MiB and 65536 allocations), not a general reclaimable
heap; repeated snapshots can exhaust it even after local variables leave scope.

## Actual Awl applications

```
kcc build examples/apps/kcopy/main.aw -o kcopy
./kcopy input.bin new-output.bin
kcc build examples/apps/textinfo/main.aw -o textinfo
./textinfo notes.txt
```

Use `.exe` output names and Windows invocation syntax on Windows. `kcopy` is a
two-module streaming binary copy: one 64 KiB buffer, short-write loop, checked
flush and destination close, exclusive creation. It never intentionally replaces
an existing destination. A failed copy may leave a **partial destination**;
there is no automatic deletion/rollback or atomic commit. `textinfo` accepts up
to 8 MiB, probes an extra byte to reject growth, reports bytes and Unicode scalars,
and rejects malformed UTF-8. Shrinkage is accepted as the actual bytes read.
Pixelboard is still **in-memory only**; GUI persistence awaits safe-save design.

Validation results and platform qualifications belong to `tests/files-*` reports;
Wine execution is not native Windows-host backend acceptance.
