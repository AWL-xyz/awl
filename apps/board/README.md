# Awl Board [Beta]

a useful, deliberately bounded local full-stack workload, native Awl owns HTTP parsing, validation, identifiers, revisions and atomic persistence, the same Awl schema and filtering code is compiled to WebAssembly for browser search, javascript supplies DOM/events and the narrow WASI host, not a replacement business-rules implementation

## run the standalone linux application

```sh
mkdir -p board-data
./awl-board ./board-data 8080
```

open `http://127.0.0.1:8080/`, or omit the port to choose an available port, the first stdout line reports the port, keep the terminal open, stop with Ctrl+C, restart with the same directory to restore your board

the application is one statically linked Linux x86-64 executable, it embeds the page, owl and compiled WASM, no Python, Node, host compiler, SDK, network asset or separate backend is needed to run it, use a current browser with WebAssembly, workers, `DecompressionStream` and `AbortSignal.timeout`, Chromium on Linux is qualified, other browsers and native Windows aren't accepted yet

## useful workflow

- create, edit, delete and move tasks between to do, in progress and done
- search titles and notes, case-insensitive for ASCII, exact Unicode otherwise
- keyboard-accessible labelled controls and a responsive single-column mobile layout
- export the current snapshot as JSON, restore manually only while the server is stopped, validate backups before replacing a working file
- independent tabs use a strong board-revision precondition, stale edits are rejected and their drafts stay intact, cancel and refresh before retrying
- storage failures don't acknowledge unpublished work, lost acknowledgements are explicitly uncertain, refresh before retrying
- an uncertain directory-sync outcome acknowledges that publication happened, disables further editing and stops the server, restart and inspect the saved board before continuing

## explicit bounds and trust model

32 tasks,160 UTF-8 bytes per title,256 per note,10000 revisions, monotonically increasing IDs below1000000,256 requests per process session,10 minutes of idle time before normal exit, request limits can be lowered by a third positional argument, restart extends a session without resetting data or revisions

HTTP/1.1 GET/PUT/DELETE subset,8192 header bytes/32 headers,1024 body bytes,1500ms total receive deadline,500ms response-write deadline, one request per connection, no chunking, pipelining, HTTP/2, TLS, remote users, authentication or concurrent request workers

run exactly one server per directory, this version has no interprocess lock, two browser tabs are protected within one server but two server processes are not, external edits, shared/network filesystems, hostile directory races and hardware power-loss durability aren't qualified, the directory must already exist and remain trusted

only loopback is bound, exact localhost/127.0.0.1 Host plus matching unsafe-method Origin are required, cross-site fetch mutations are refused, these checks and CSP are browser-origin defenses, not authentication against local processes, no CORS access is granted

`board.json` is validated before listening, malformed data fails closed without modification, `.board.tmp` is a replaceable same-directory staging file, symlink/nonregular file refusal and publication semantics come from the existing checked runtime, a stale staging file isn't an accepted snapshot

## build with the existing complete SDK

from this directory, with the SDK's bin directory on PATH

```sh
awl build main.aw -o awl-board -O 2
```

`Assets.aw` already contains the embedded, compiler-produced browser payload, this build needs no Python and uses only the existing complete SDK, the published0.24 SDK archives are unchanged, this application is a separate complete download, not an SDK overlay

contributors rebuilding the browser payload from the full repository can run

```sh
python3 apps/board/browser/build.py --sdk /path/to/Awl --output /var/tmp/awl-board --report /var/tmp/board-build.json
```

the contributor script uses the real compiler and bundled Zig backend, not a JavaScript reimplementation or a new public build target, `vendor/Json.aw` is the repository's bounded JSON parser with only its input ceiling raised from16384 to65536 for worst-case escaped snapshots,512-token/16-level/4096-byte decoded-string bounds remain, the builder verifies this exact provenance, other JSON consumers keep their previous bounds

## architecture and qualification

`Rules.aw` shares integer/text/status/search policy, `Store.aw` supplies staged JSON decoding, encoding and atomic snapshot publication, `Http.aw` is a separate application-specific derivative of the tested kvserve subset, `main.aw` applies mutations to candidate vectors before publication and advances live state only after publication, `filter.aw` is the same schema/search workload for native parity and browser WASM

GET `/api/tasks` and `/api/export` return the board and its strong revision token, PUT `/api/tasks/ID` creates the next ID or replaces an existing task, DELETE removes an existing task, unsafe requests require a single exact `If-Match: "vN"`, this is a deliberately narrow board-precondition policy, not complete HTTP conditional-header semantics, weak/list/wildcard validators aren't accepted, no-op replacement doesn't write or advance revisions

see `tests/board-*.json` for executable-bound evidence,198 HTTP/storage/model checks each normal, public-SDK and sanitizer builds,24 syscall-fault checks,80 native/79 WASM independent schema/filter oracles,6 worst-capacity/deadline checks each public and sanitizer builds,23 real-browser checks, the browser photo in `demos/board/Awl-board.png` is an actual Chromium capture

research used before implementation, HTTP semantics <https://www.rfc-editor.org/rfc/rfc9110.html>, conditional-request guidance <https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests>, exact strong/weak validator behavior <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-Match>, this app doesn't claim to implement the whole specification
