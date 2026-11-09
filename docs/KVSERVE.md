# bounded native key/value service

`examples/apps/kvserve` is a real Awl backend for a small trusted local text store, it accepts HTTP requests directly through the native tcp runtime, stores immutable mutation segments, and reconstructs state after a process restart

linux source checkpoint, not a newly published standalone distribution, protected 0.23 downloads don't include these features, windows qualification follows language development

## build and use

with the current complete development toolchain

```sh
cd examples/apps/kvserve
awl build
mkdir -p /var/tmp/Awl-notes
./build/kvserve /var/tmp/Awl-notes/store 0 128
```

the first stdout line is the selected loopback port, arguments are storage prefix, optional port, optional maximum accepted connections, defaults are ephemeral port and128 connections, accepted maximum is1..256

```sh
curl -X PUT -H 'Content-Type: text/plain' --data-binary 'hello Awl' http://127.0.0.1:PORT/kv/note
curl http://127.0.0.1:PORT/kv/note
curl -X DELETE http://127.0.0.1:PORT/kv/note
```

curl's default form content type isn't accepted, raw clients can omit Content-Type

| request | result |
|---|---|
| GET /health | status, current key count and store revision |
| PUT /kv/KEY | raw UTF-8 text body,201 when created or200 when replaced, revision advances |
| GET /kv/KEY | JSON key/value/revision,404 if absent |
| DELETE /kv/KEY |200 and new revision,404 without a mutation if absent |

keys are case-sensitive1..64 ASCII letters/digits/underscore/hyphen, no URL decoding or arbitrary filesystem paths, values are0..1024 bytes of valid UTF-8 including embedded NUL, JSON output escapes quotes/backslashes and every control scalar, Unicode remains text

## bounded HTTP contract

one HTTP/1.1 request per connection, then close, exactly one nonempty Host, ASCII CRLF headers, at most8192 header bytes/32 fields/64-byte field names/256-byte targets

PUT requires exactly one decimal Content-Length, missing411, duplicate/invalid400, more than1024 bytes413, malformed UTF-8 body422, GET/DELETE reject nonzero bodies, transfer encodings are rejected, this isn't a complete RFC9112 implementation or a general JSON parser

Content-Type is optional, if supplied only case-insensitive `text/plain` or `text/plain; charset=utf-8` is accepted, other media types415, duplicate type fields400, arbitrary MIME parameter spacing isn't implemented

header and body share a500ms monotonic receive budget, responses have a separate500ms budget, partial reads/writes loop, premature EOF400 and receive timeout408, extra pipelined bytes aren't another request or mutation, idle accept exits after5s

128 live keys,256 lifetime mutations per storage prefix, capacity exhaustion507 before persistence, replacement is allowed at the key cap, reads still work at the mutation cap, a process accepts at most256 connections because immutable text uses a bounded process-lifetime region

## persistence and failure semantics

single writer and a trusted existing storage directory are required, there's no lock, filesystem sandbox, compaction, directory enumeration, rename, atomic replacement, automatic repair or authentication

`PREFIX.SEQUENCE.kvs`, canonical sequence1..256, exclusive creation never truncates an existing segment, header/payload are written with short-transfer handling, then file fsync and checked close, only afterward does the live map change and the response get sent

a storage failure sends503 when possible and exits5, it doesn't continue serving potentially questionable state, a complete valid record can survive an fsync/close error or a lost response, so a mutation not acknowledged to the client may appear after restart, there are no exactly-once request IDs or rollback guarantees

partial/corrupt segments fail startup closed with exit4 before a listener is opened, replay builds a temporary sorted map, only validated complete replay is published, no malformed tail is silently skipped, manual inspection/repair may be required, preserve files before attempting recovery

startup probes canonical names1..257, holes followed by a canonical record or any257th segment fail closed, arbitrary filenames, alternate number spellings and higher indexes aren't scanned, external modification while serving isn't supported

file fsync isn't directory fsync, the containing directory entry isn't separately synchronized, **no power-loss durability or hardware-failure guarantee**, restart testing covers process interruption and checked syscall failures, not a production database

### KVS1 binary format

| byte range | encoding |
|---|---|
|0..3 | ASCII KVS1 |
|4 | operation1 put /2 delete |
|5 | key byte length1..64 |
|6..7 | big-endian value byte length0..1024, delete requires0 |
|8..9 | big-endian canonical sequence1..256 |
|10..11 | zero reserved bytes |
|12 onward | ASCII key followed by UTF-8 value |
|last4 | big-endian Adler32 of all previous bytes |

record length17..1104, checksum isn't cryptographic or an authentication boundary, replay also validates sequence/magic/reserved/op/length/key/UTF-8, deletes must reference a present key and reconstructed live keys must fit the cap

## reusable source helpers

- `TextMap.aw`, sorted alternating key/value `vector<text>`, binary-search lookup, reserve-before-insert, replacement/removal, caller must preserve the even-length sorted unique-key invariant, find returns value index or-1 absent/-2 odd length, not a builtin generic map or opaque type
- `Json.aw`, recoverable bounded JSON string generation into an output text vector, not a parser, failed builder operations don't append output
- `Journal.aw`, append/replay and key validation, caller owns a valid byte buffer, append needs at least1104 bytes and load1105, undersized buffers fail normally, invalid handles still trap under runtime rules
- `Http.aw`, bounded framing and responses, receive needs a valid buffer of at least9216 bytes and an empty output vector, service uses16384 bytes

these helpers don't add arbitrary generics, reclaimable strings, owned aggregates or fully recoverable process-wide text allocation

## executed evidence

- `tests/kv-linux.json`,192 native wire/restart/record/corruption/capacity cases through the bundled backend
- `tests/kv-sanitized.json`, the same192 cases with strict generated-C ASan/UBSan
- `tests/kv-helpers.json`,746 independent-oracle assertions per native/sanitized mode, randomized map replacement/removal/order, controls/Unicode JSON and error preservation
- `tests/kv-faults.json`,15 checks under strict sanitizers, short reads/writes, EINTR, zero write, partial ENOSPC, fsync failure and checked-close failure, exact independent record bytes and restart outcomes
- `benchmarks/kv-latest.json`, measured warm build/startup/real sequential HTTP workload, not a production throughput claim
- `demos/kvserve/native-kv.png`, actual Xvfb/Xterm display showing native toolkit build, HTTP operations and restart recovery

compiler bytes are unchanged from the network checkpoint, existing compiler acceptance remains historical evidence for those exact bytes, the new workload has its own source-bound acceptance

## research informing the implementation

- https://www.rfc-editor.org/rfc/rfc8259.html — JSON string control/quote/backslash escaping and Unicode
- https://www.rfc-editor.org/rfc/rfc9112.html — framing rules, this deliberately restricted server doesn't implement chunked transfer encoding
- https://man7.org/linux/man-pages/man2/open.2.html — exclusive creation rather than truncating an existing record
- https://man7.org/linux/man-pages/man2/fsync.2.html — checked sync and the separate containing-directory durability caveat
