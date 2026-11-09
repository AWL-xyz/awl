# awl. editor

`editor/awl-editor.html` is one self-contained offline file, no build step, no server, no external script or style dependency beyond the optional Google Fonts link, which degrades to system fonts offline

the header mark is the project owl, static, taken from `assets/branding/awl.svg` geometry, mask and cutouts, rendered in the light text colour instead of white on a dark bar

## what it does

- multi-file `.aw` editing with rename/delete, drag and drop, `.aw` download, and `localStorage` persistence under `awl-editor:v2`
- highlighting and a structural aid for the current `aesop` grammar, brackets, `end` blocks, statements missing `;` and the old `func name(...)`/function `end;` shapes are flagged, it is not the native checker
- `Run`/`Live` executes the supported subset in the page, `Ctrl+Enter` reruns, output, traps and a source line for each diagnostic are shown
- the framebuffer calls record frames and the Visual tab replays them, recording is capped at600frames and48MB

## supported subset

- top-level `use ... as ...;`, `exports{ @r|@w ... };`, `@p`/`@s` bindings, `func name :: params: type { ... };`, enums and `match ... end;`
- checked integer widths with traps on overflow, division by zero and out-of-range conversion, f64 math, `pi`/`tau`, text and `..` concatenation
- module state, `@r` read-only and `@w` writable access from the importing file, private defining-file context
- `print`, monotonic clock, wall clock and sleep, math helpers, string helpers, `window_open`/`window_set_pixel`/`window_present`/`window_title`/`window_close`

## not supported

vectors, views, structs, builders, files, processes, sockets, `defer` clean-up ordering, ownership checking, the legacy grammar, real OS windows and input events, 32-bit wrapping and the whole native type system, unsupported calls fail explicitly instead of pretending

`editor/Awl-studio.html` stays the older playground for the legacy-subset examples it bundles, it is not migrated to the current grammar

## verification

`tests/awl_editor.js` drives the interpreter outside a browser, `tests/awl_editor.py` runs it plus `kcc check` on every bundled example and records tests/awl-editor.json, no screenshot or visual comparison replaces those checks
