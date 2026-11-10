# native streams and environment reads

linux development source only, not yet in the protected downloads, windows work's deferred until the language is fully developed

these are native compiler intrinsics, available without a Package import, the checker and independent verifier enforce their signatures, emitted programs don't require python or a host compiler

## byte streams

| call | result |
|---|---|
| `stdin.read(buffer:i64, offset:i64, count:i64)` | bytes read, `0` for eof, negative error |
| `stdout.write(buffer:i64, offset:i64, count:i64)` | bytes written, negative error |
| `stderr.write(buffer:i64, offset:i64, count:i64)` | bytes written, negative error |
| `stdout.flush()` | `0` or negative error |
| `stderr.flush()` | `0` or negative error |

all results are `i64`, these functions use existing checked byte buffers, no pointer or os descriptor escapes

- reads and writes can be short, callers must advance offsets and loop, a short positive read isn't eof
- interrupted `read` and `write` calls retry only when no bytes were transferred and the os reports `EINTR`
- a zero count validates the buffer and range, then returns `0` without touching the os stream
- invalid, stale, forged or out-of-range buffer access traps, it's a programming error, not an io status
- stdout and stderr are separate byte streams, arbitrary bytes and embedded nul are preserved, nothing adds a newline or decodes utf-8
- a raw write first flushes pending `print` output on that stream, preserving single-threaded program order
- flush drains the c library's user-space output buffer, it isn't `fsync`, persistent storage, or a guarantee that another process consumed the bytes
- streams are borrowed process resources, these functions don't close them or allocate file-handle slots
- operations are synchronous and may block, there's no async scheduler, deadline or cancellation api yet

most errors follow the existing file status mapping, including `-1` for other io failures, `-4` for access failures, `-5` for invalid operations, `-8` for space/quota failures and `-9` for allocation failures

additional stream statuses are `-10` for would-block and `-11` for a broken pipe when the process survives `SIGPIPE`

the runtime doesn't change signal dispositions, on linux a write to a pipe whose reader has closed can terminate the program with the usual `SIGPIPE`, if the launching environment ignores or blocks that signal, the call can return `-11`, this distinction's tested with real pipes, not hidden behind a blanket recoverable-error claim

## environment configuration

| call | result |
|---|---|
| `env.size(name:text)` | value's byte length, or negative error |
| `env.read(name:text, buffer:i64, offset:i64, count:i64)` | copied byte count, or negative error |

names must be nonempty, at most 4095 utf-8 bytes, without nul or `=`, linux lookup's case-sensitive, values remain raw bytes until explicitly validated or converted with `buffer.textvalid` / `buffer.text`

- `-2` means the name's missing, a present empty value returns `0`
- `-5` means an invalid name, a value exceeding the 1 mib lookup bound, or insufficient destination capacity
- `-4` means linux secure-execution mode refuses environment access, this isn't permission to trust environment configuration in privileged software
- the buffer and destination range are checked even if the variable's missing
- the full value must fit, capacity errors don't partially copy or change the buffer
- `env.size` doesn't allocate, `env.read` copies directly into caller-owned buffer storage, no borrowed environment pointer escapes
- these are separate lookups, not a transactional snapshot, future foreign calls or threads that mutate the environment would need additional synchronization
- there's no environment mutation, dotenv parser, Package installation, secret store or automatic configuration loader

on non-linux targets, nonzero stream io, stream flush and valid environment lookups return `-6` for unsupported, zero-length io still performs its normal checked no-op, no new windows capability's claimed

## useful native pipeline

[`examples/apps/pipe`](../examples/apps/pipe/main.aw) is a complete Aesop-syntax project, it's a binary-safe streaming copy/filter with bounded memory, checked short-write loops and separate error/report output

```sh
cd examples/apps/pipe
awl build
printf 'hello, Awl!\n' | KPIPE_MODE=upper KPIPE_REPORT=1 ./build/pipe
```

stdout is `HELLO, Awl!` with its original newline, stderr is `bytes processed: 13` with a newline

`KPIPE_MODE` accepts `copy`, `upper` or `lower`, default's `copy`, upper/lower change only ascii letters, they aren't unicode case conversion, non-ascii and binary bytes are untouched

`KPIPE_REPORT=1` enables the byte-count report on stderr, any other present value is an error, invalid configuration's rejected before input's consumed, ordinary input uses one reusable 64 kib buffer rather than buffering the whole stream

```sh
producer | ./build/pipe | consumer
KPIPE_MODE=lower ./build/pipe < input.bin > output.bin
```

output redirection's the shell's operation, it may truncate an existing destination, this isn't an atomic-save api

## evidence and trade-offs

- `tests/streams-linux.json` exercises real bundled-backend programs and byte-exact pipeline oracles
- `tests/streams-sanitized.json` repeats those cases with generated c under asan/ubsan
- `tests/streams-faults.json` covers short io, interrupted calls, zero progress, os errors, flush failure, secure execution, oversized environment and genuine closed/nonblocking/broken pipes
- `tests/streams-native-sanitized.json` includes the independent stream-call corruption verifier and existing native scanner/frontend/verifier/project gates
- the browser editor includes this source for browsing, its experimental browser runtime doesn't emulate these native os apis

primary references, checked before implementation

- [linux read semantics](https://man7.org/linux/man-pages/man2/read.2.html)
- [linux write semantics and pipe signals](https://man7.org/linux/man-pages/man2/write.2.html)
- [environment pointer lifetime and secure execution](https://man7.org/linux/man-pages/man3/getenv.3.html)
- [stdio flush semantics](https://man7.org/linux/man-pages/man3/fflush.3.html)

there's deliberately no per-byte syscall wrapper or forced whole-stream allocation, short-count loops live in normal Awl code, the next work's broader collections, reusable parsing/configuration and recoverable structured errors, then networking and concurrency

## contributor reproduction

restore the complete linux backend from the protected archive into a disposable
prefix, overlay the current `compiler/native/bin/kcc`, and make `bin/Awl` a
relative symlink to `kcc`, keep that sdk outside the persisted workspace budget

```sh
python3 tests/streams.py --kcc /path/to/prefix/bin/kcc --report tests/streams-linux.json
python3 tests/streams.py --kcc /path/to/prefix/bin/kcc --sanitize-c --report tests/streams-sanitized.json
python3 tests/streams_faults.py --kcc /path/to/prefix/bin/kcc
python3 tests/streams_native.py
```

legacy regression uses `build/Awl-linux-x86_64` as its contributor prefix, which
can be a temporary symlink to that complete prefix, `tests/streams_regression.py`
accepts `--python /usr/bin/python3` for an interpreter with the xlib/pillow display
fixtures installed, those dependencies aren't required by installed Awl

one initial native sanitizer compile was killed under concurrent regression
load and a large ram-backed temporary sdk, that attempt's retained in
`tests/streams-native-resource-attempt.txt`, moving the sdk/cache to disk and
running the gates without that contention produced a full seven-phase pass
