# compiled browser foundation

`web/Awl-json-workbench.html` is a standalone offline browser app, open it directly, enter JSON and a JSON Pointer, inspect the selected value, there are no external scripts, resources or services

this is different from the experimental interpreter in `editor/Awl-studio.html`, the workbench runs the production compiler's checked C output compiled to wasm32-wasi by the bundled backend, Awl code performs strict JSON parsing, tokenization and pointer selection, javascript supplies the controls, argv/stdout bridge and safe text rendering

large numbers remain exact text, including9223372036854775807, strings support the parser's UTF-8 and surrogate handling, malformed JSON reports byte offsets, duplicate matching keys and malformed pointers report explicit selection errors, container selections display their kind and total document token count rather than claiming a general DOM

## boundaries and lifetime

each operation gets a fresh worker and wasm instance, completion/cancellation terminates the worker, a5second watchdog handles noncompletion, the module's declared linear-memory ceiling is64MiB, this isn't a limit on all browser/worker/JIT memory

existing parser bounds remain16KiB input,16levels,512tokens and4096decoded string bytes, the host caps argv at64KiB/256arguments and output at1MiB, raw NUL/unpaired UTF-16 surrogate arguments are rejected before entering the C argv ABI, escaped JSON NUL values work

the small WASI host only admits the implemented argv, stdout/stderr, descriptor-probe and exit imports, unknown imports fail closed, no filesystem/network capability is granted, this isn't a complete WASI implementation or a general sandbox for arbitrary uploaded wasm

immutable text still uses its bounded process-lifetime region, discarding each instance reclaims browser workload state, that doesn't solve reclaimable native strings

## compiler/runtime change

string byte/scalar counts now use explicit uint64 fields, the existing24byte/8byte-aligned string ABI is preserved on native64bit targets and wasm32, the C compiler supplies pointer padding on wasm32, static assertions remain active, no generated-C patching or verifier bypass is used

this is an experimental contributor build path, public ASDK remains init/build without a new browser target flag, the offline app needs no compiler, SDK, python or host service

rebuild with a complete development SDK containing the current compiler

```sh
python3 web/build.py --sdk /path/to/Awl --report /tmp/browser-build.json
```

`--entry` can select another compatible source program, the reusable compiler path was also exercised with the associated-enum calculator, UI controls are specific to JSON rather than a general application framework

## executed acceptance

- 437 JSON/root/pointer cases checked against an independent Python oracle and native execution, exact output parity in Node webassembly and Chromium worker UI
- 444 signed-i64 boundary/random enum-calculator oracle cases in webassembly
- 8 host rejection cases, cancellation, deliberately stalled-worker timeout and execution inside an opaque `sandbox="allow-scripts"` iframe
- no external requests during offline browser execution, actual Chromium screenshot in `demos/wasm/browser-workbench.png`
- current native runtime regression and source hashes recorded in `tests/wasm-checkpoint.json`, old checkpoints remain historical

`tests/wasm-browser.json` includes whole UI automation latency, not parser-only throughput or a speedup claim, only the recorded Chromium and Node versions are qualified, other browsers/mobile/accessibility/general DOM integration aren't accepted

## capability review

browser/frontend stage0→1 is justified by an executed native-compiler-to-webassembly foundation and an interactive offline document inspection workload, important blockers remain, including general DOM/event interop, browser-target tooling, browser compilation, wider APIs and full-stack integration

all other stages remain unchanged,10/45=22.2% rounded, no full browser platform,3D renderer, updated complete SDK distribution or native windows acceptance is claimed

references, [WASI snapshot ABI](https://raw.githubusercontent.com/WebAssembly/WASI/snapshot-01/phases/snapshot/docs.md) and [WebAssembly instantiation](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/JavaScript_interface/instantiate_static)
