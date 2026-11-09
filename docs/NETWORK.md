# native local tcp foundation

linux development source, synchronous IPv4 loopback listeners and connected streams, not general internet networking or a published release

| call | result |
|---|---|
| `tcp_listen_loopback(port,backlog)` | positive opaque i64 handle, negative error, port0 requests an ephemeral port, backlog1..128 |
| `tcp_valid(handle)` | bool, false for invalid/stale/unavailable handles |
| `tcp_port(listener)` | assigned port, connected handles return -5 |
| `tcp_accept(listener,timeout_ms)` | positive connected handle or negative error |
| `tcp_read(connection,buffer,offset,count,timeout_ms)` | short byte count, eof0, negative error |
| `tcp_write(connection,buffer,offset,count,timeout_ms)` | short byte count or negative error, not a peer-delivery guarantee |
| `tcp_close(handle)` | 0 or negative error, always retires a live linux handle |

all numeric arguments are i64, sockets are runtime-checked manual handles, not new statically owned resource types, `defer tcp_close(handle)` works, don't combine explicit close with deferred close on the same handle, aliases can become stale

## bounds and failure contract

32 shared listener/connection slots, ids start at2^61 and never repeat, exhaustion fails closed before accepting or allocating another socket, listen binds only127.0.0.1, never0.0.0.0, IPv6/outbound connect/DNS/UDP aren't implemented

invalid/stale/foreign handles and invalid buffer ranges trap, even for zero count, live but wrong-kind sockets and invalid timeout arguments return -5, zero-count io returns0 after handle/range/kind/timeout checks

timeouts0..3600000ms, not hard real-time guarantees under OS scheduling, zero attempts one nonblocking syscall, positive timeouts use a monotonic per-call deadline, EINTR/readiness retries recompute the remaining budget, they don't restart the timeout, partial progress returns immediately, callers implementing a multi-call operation need their own overall deadline

sockets and accepted descriptors are nonblocking and close-on-exec, failed bind/listen closes the descriptor without publishing a handle, normal process exit closes remaining sockets, close isn't retried on Linux EINTR because the fd has been released

- -1 other os error
- -3 address already in use
- -4 permission denied
- -5 argument/kind error
- -6 unsupported platform
- -7 slot/id/os descriptor limit
- -9 memory/socket-buffer allocation failure
- -10 would-block/deadline/timeout
- -11 disconnected/reset/broken pipe

non-linux constructors return -6 for otherwise valid arguments, the fallback was compiled on Linux with the platform branch disabled, this isn't native windows evidence

socket sends use MSG_NOSIGNAL, EPIPE returns -11 without changing process-wide SIGPIPE behaviour, existing stdout/pipe policy is unchanged, operations aren't thread-safe, asynchronous tasks/cancellation aren't implemented

## kserve, a real bounded service

`examples/apps/kserve` is a two-file manifest project implemented in Awl, build using the native toolkit, run `./build/kserve [PORT [MAX_CONNECTIONS]]`, default port0 and32connections, explicit maximum1..256, first stdout line is the assigned port and is explicitly flushed

- GET /health returns a JSON status object
- GET /counter reads in-process state
- POST /counter increments and returns state
- unknown route404, unsupported route method405 with Allow
- malformed headers400, oversized headers431, incomplete stalled headers408

read/write budgets500ms each for the complete request/response phase, idle accept5seconds, one request per connection with Connection: close, no persistent connections or pipelined execution, trailing bytes are not processed as a second request

headers<=8192bytes/32fields, target<=256bytes, field names<=64bytes, visible ASCII plus CRLF only, exactly one nonempty Host required, field-name matching ignores ASCII case, obs-fold, controls, transfer encodings, nonzero/duplicate Content-Length are rejected

this is deliberately a bodyless HTTP request subset, not a complete RFC9112 implementation, no chunked decoding, request bodies, general JSON parser, URL decoding/query routing, locale, TLS, authentication, CORS, durable state or concurrency, don't put it behind a proxy or expose it as a production service, loopback isn't an authentication boundary

counter changes commit before the response write, a failed response doesn't undo a POST, there's no idempotency/retry guarantee, the bounded process lifetime also bounds use of the existing unreclaimable text region

## evidence and research

45 actual bundled-backend cases and the same45 strict-warning generated-C ASan/UBSan cases, wire-level binary echo/eof, malformed/fragmented/oversized/slow requests, stateful routing, reset survival, slot limits, bad handles/ranges and signatures

fault harness tests EINTR absolute budgets, short sends, per-call SIGPIPE without global mutation, bind rollback, close EINTR, listener/accepted fd flags and id exhaustion, independent verifier checks all seven new signatures and deferred close, broader gates are bound by tests/net-checkpoint.json

actual terminal capture demos/network/native-http.png, whole-command measurements benchmarks/network-latest.json, no throughput or production-load claim

primary sources fetched2026-11-06
- https://man7.org/linux/man-pages/man2/accept.2.html
- https://man7.org/linux/man-pages/man2/poll.2.html
- https://man7.org/linux/man-pages/man2/send.2.html
- https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3

these informed nonblocking accepted descriptors, deadline-preserving retries, per-call SIGPIPE control and explicit response framing, Awl's intentionally restricted request subset doesn't imply full standards conformance
