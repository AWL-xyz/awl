# historical syntax milestones

this record predates the Aesop-only grammar, see [Aesop](docs/AESOP.md) for current syntax and `tests/aesop-native.json.gz` for current native validation

# mutable borrows and recovery diagnostics, unreleased

`func grow :: @m row:Row { row.weight: row.weight + 1; };` borrows a caller struct in place, the parameter is an alias so field writes land in the caller's value, the argument must be an existing local, field or element, temporaries are rejected

the checker keeps the narrow contract, `@m` only accepts struct types, one local cannot be borrowed twice in a single call, a by-value parameter and an `@m` borrow of the same struct coexist, there is still no alias proof or lifetime inference

`return;` now works in unit functions and runs scope cleanup first, unknown field/function/local/module-variable/enum-variant errors append a closest-match suggestion, earlier module lowering handles `mut_param` types so imported structs work

verified by real build and run of examples/structs including the borrow section, tests/next_features.py compares exact stdout, tests/next_examples.py checks 38 sources, knext_test and kverify_test still pass

# structs, loops and hash containers, unreleased

`struct` is a value type now, braced fields with colon types, positional construction, `row.weight: 4;` mutation through nested paths, `@r struct` in `exports{ ... };` lets an importer name and construct the type, structs also live in fixed arrays

loops gained `for i in 0..n { ... };` and `for value in collection { ... };` over vectors, views, int_vectors, arrays, map keys and set elements, `break;`/`continue;` unwind the scopes they leave so `@s` owners inside a skipped body are still released

`map<K,V>` and `set<T>` are 8-byte handles over one open-addressing runtime, text keys and text values are owned copies, `map.get` traps on a missing key, iteration is hash order, `map.keys`/`map.values`/`set.values` return an owned vector, containers are `@s` owners with automatic cleanup

verified by real builds and runs, `tests/next_features.py` builds and executes the three new examples with the bundled SDK and compares exact stdout, `tests/next_examples.py` structurally checks all38 example sources, knext_test and kverify_test still pass

no score change, 26.7%=12/45, language surface alone doesn't earn a workload stage

# structural checker repair, unreleased

the checker used to reject real programs, `while i < vector.length(values)` looked like a generic call, `case lib.Ticket.Id(n)` and `[10,20,30]` did not parse, `file.Issue` field types failed, a `"-"` literal was read as unary minus and imports had to be passed in dependency order on the command line

now `at()` ignores literal token kinds, generic calls need `<type>(`, dotted chains and patterns are loops, types accept `alias.Name`, `use` loads from disk with a cycle guard, one file is enough

`tests/next_examples.py` runs the checker over all 34 examples sources each as a single argument, report tests/next-examples.json, `demos/next-syntax/run-demo.sh` exits 0 again, no capability change

# published0.26 successor, function declaration revision

next functions are declared `func size[i64] :: @b values[i64], etc[i64] { ... };`, parameterless ones use `func main[i64] { ... };`, parenthesized parameter lists and function `end;` bodies are rejected, enums and matches keep `end;`

`::` is scanned as one token, the parser refuses `(...)`, empty `::`, a missing `{` and a missing trailing `;`, the starter written by `awl init` follows the new shape

47 sources migrated with `compiler/migrate_next.py`,21 entry programs still emit byte-identical C, focused native/sanitized fixtures and the standalone `compiler/next/syntax.cpp` structural checker follow the revision

`editor/awl-editor.html` ships as the current single-file next-syntax editor with the static owl mark, `editor/Awl-studio.html` remains the older legacy-subset playground

complete Awl-0.26.0-dev-linux-x86_64.tar.xz published, resources inherited byte-for-byte from0.25 and re-verified,0.25 retired only after the exact successor passed, evidence in tests/successor-checkpoint.json, tests/successor-0.26.json and tests/awl-editor.json, capability26.7%=12/45 unchanged

# historical development notes

current Awl qualification is in tests/rename-checkpoint.json and RELEASE-0.24.md, the notes below predate this migration, immutable originals are in history/pre-rename-evidence.tar.xz

# current checkpoint,20.0% =9/45

useful bounded native valueserve now earns backend stage2, see docs/VALUE-SERVE.md and the final section below, the network-only details below remain historical

# native networking foundation, historical17.8% checkpoint

real linux TCP listeners and byte streams now run through the native compiler, plus a two-file Awl service with health and stateful counter JSON routes

```sh
awl build
./build/serve 0 32
```

first stdout line is the ephemeral loopback port, GET /health reports status, GET /counter reads state, POST /counter increments it, real clients exercise the actual native program, no Python server or external HTTP framework substitutes for Awl

## scope and safety

- loopback IPv4 only,32 shared manual socket slots, monotonic non-reused ids, nonblocking/close-on-exec descriptors
- tcp.listenloopback, tcp.valid, tcp.port, tcp.accept, tcp.read, tcp.write and tcp.close, normal lexical deferred close supported
- short reads/writes, eof, per-call absolute monotonic deadlines, timeout0 attempts one nonblocking operation
- EINTR/readiness retries don't reset deadlines, invalid/stale handles and bad ranges trap, OS/argument/limit failures return negative errors
- MSG_NOSIGNAL applies only to socket sends, existing process-wide SIGPIPE and stdout/pipe policy remain unchanged
- bind/listen failure closes unpublished descriptors, close EINTR retires the Linux handle without retry

serve is intentionally limited, bodyless request subset,8192header bytes/32fields/256byte target, one request per connection,500ms complete header/response budgets,5second idle accept,32default/256maximum accepted connections, normal exit cleans up resources

malformed/oversized/slow requests return400/431/408, routes include404/405 with Allow, exactly one nonempty Host required, no obs-fold, controls, transfer encodings or nonzero/duplicate Content-Length, valid JSON responses have exact byte lengths

not a full RFC9112 implementation, no request bodies/chunked decoding/general JSON parser, URL decoding, TLS/auth/CORS, persistence, outbound connections/DNS/IPv6 or concurrency, no pipelined execution, loopback isn't authentication, don't expose this through a proxy or use it as a production service

accepted-peer resets are tested, other accept OS errors can stop this demonstration, POST commits before response delivery and isn't rolled back if the peer disappears

## validation

45 actual bundled-backend network cases and the same45 generated-C strict-warning ASan/UBSan cases passed, binary echo/eof, zero/range/kind/slot/timeout checks, malformed/fragmented/oversized/stalled requests, counter state and reset survival

fault harness verifies deadline budgets across EINTR, short sends, per-call SIGPIPE, bind rollback, close EINTR, listener/accepted descriptor flags and id exhaustion,31 dedicated independent verifier/emitter cases, all9 native sanitizer phases passed with693targeted+10000structural verifier corruptions

56 vector,37 stream,47 module/math,65 next/legacy,62 ASDK and2448numeric parser cases passed on the current compiler, parser cases also ran generated-C sanitizers

564tests EACH reference/native-parser/native-frontend passed with no skips, initial fixture attempt skipped7display cases because contributor fixtures were absent, that attempt is retained separately and excluded from acceptance, fixtures installed and all three modes rerun

## measured tradeoffs

whole-command warm-cache build median481.849ms, native process ready0.386ms,70local sequential connect/send/receive/close counter requests after warmup median0.050ms, concurrent regression work, not production load/throughput or a speedup comparison

optional --compact-shared retains the default O3 path but selects Os/LTO when explicitly requested, same-source shared library695504→432792bytes, warm in-process sort frontend pipeline2.780→3.356ms, slower on that workload in exchange for262712bytes saved, standalone stays O2/LTO, primary references and hashes are retained, no old archives/evidence deleted to fund this work

## capability review

**17.8% =8/45**, backend0→1 for an executed new domain-specific foundation, not another cli tool or function count, other eight stages unchanged, at that checkpoint stage2 was unearned, production backend/full-stack/concurrency remain unearned

actual Xvfb/Xterm photo demos/network/native-http.png was opened,56 sources embedded in the offline editor, JSON/script syntax checked, its browser runtime doesn't implement native networking

linux development source only, windows remains deferred, protected0.23downloads unchanged, no new complete distribution, see docs/NETWORK.md and tests/net-checkpoint.json for exact contracts/evidence, temporary SDK/caches/fixtures removed after gates, final whole-home audit is tests/net-workspace-audit.json

## bounded persistent backend checkpoint

`examples/apps/valueserve` adds native text PUT/GET/DELETE, strict body framing, JSON escaping, sorted text-map helpers and checksummed exclusive mutation segments with restart replay

192 native +192 strict sanitizer service cases,746 helper assertions per native/sanitized mode and15 storage fault checks passed, actual terminal capture in `demos/valueserve/native-kv.png`, contract and limits in [docs/VALUE-SERVE.md](docs/VALUE-SERVE.md)

current practical capability20.0% =9/45, backend1→2 for a useful bounded native workload, no other area rises, not production readiness, no new archive, windows remains deferred

## reusable structured JSON checkpoint

native `examples/parsing/Json.aw` now parses bounded nested JSON with decoded Unicode, exact number text, byte-offset diagnostics and transactional token publication, JSON Pointer lookup and the real `jget` configuration CLI are implemented

440 parser/pointer cases and28 CLI cases passed EACH native/strict sanitizer mode, actual display capture in `demos/json/native-json.png`, API/limits in [docs/JSON-PARSING.md](docs/JSON-PARSING.md)

capability remains20.0% =9/45, existing CLI/backend stage2 strengthened, no manufactured point, compiler/protected archives unchanged, no new distribution or windows/browser acceptance

## native source graphics checkpoint

`examples/apps/colorlab` adds a real native RGB/grayscale picker and reusable checked rectangles, lines, disks and scaled5x7 text on typed pixel surfaces, actual mouse/resize/close behavior is tested, screenshot in `demos/colorlab/native-colorlab.png`

275 cases/59503 pixel-status assertions plus17 real-window checks EACH native/sanitized, contract in [docs/GRAPHICS.md](docs/GRAPHICS.md), index remains20.0% =9/45, no extra desktop stage or3D claim, compiler/distributions unchanged

## native atomic-save checkpoint

new `file.replace(directory,temporary,target)` publishes a completed staging file through atomic same-directory rename, source and directory syncs are checked, status1 explicitly means published but durability uncertain, real native `save` handles binary stdin without truncating the old target

72API/CLI cases,14fault/reuse cases and all10native compiler sanitizer phases passed, rebuilt networking/JSON/jget/graphics regressions passed, contract in [docs/ATOMIC-SAVE.md](docs/ATOMIC-SAVE.md), actual capture in demos/replace/native-replace.png

compiler rebuilt to SHAa5bd2899…, older checkpoints remain historical, full3mode legacy wasn't rerun, index remains20.0%=9/45, no new archive or native Windows acceptance
