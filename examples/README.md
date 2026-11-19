# examples

Examples use the current Aesop source syntax. After [building the toolkit](../README.md#quick-start-from-source), use `awl check PATH` to check an example and `awl run PATH --cc "$(command -v cc)"` to run it on Linux x86-64 without a bundled SDK. Omit `--cc` if you have a complete matching SDK. Examples that need arguments take them after `--`.

## language tour

- [`tour/`](tour/) broad syntax and runtime tour
- [`collections/`](collections/), [`containers/`](containers/), [`loops/`](loops/), [`structs/`](structs/), [`enums/`](enums/)
- [`exports/`](exports/), [`modules/`](modules/), [`resource-structs/`](resource-structs/)
- [`numeric/`](numeric/), [`parsing/`](parsing/), [`native/`](native/)
- [`testing/`](testing/) a project and test program that share a local module, runnable with `awl test`

## Packages

- [`packages-demo/`](packages-demo/) installs and uses `env`, `fsp` and `json`
- [`time-demo/`](time-demo/) installs and uses [`time`](../docs/TIME.md)
- [`csv-demo/`](csv-demo/) parses quoted CSV from stdin, totals an integer column, and tests round-trip encoding

## applications

- [`apps/colorlab/`](apps/colorlab/) framebuffer application
- [`apps/sort/`](apps/sort/) bounded UTF-8 line sorting, with checked byte search and batched output
- [`apps/pipe/`](apps/pipe/), [`apps/save/`](apps/save/), [`apps/serve/`](apps/serve/), [`apps/valueserve/`](apps/valueserve/) other bounded native utilities
- [`../apps/taskrun/`](../apps/taskrun/) subprocess supervisor
- [`../apps/logwindow/`](../apps/logwindow/) bounded UTF-8 log processing
- [`../apps/board/`](../apps/board/) persistent taskboard with native service and shared WebAssembly filter

legacy example trees and overlays are not current sources, historical material is preserved in private capsules and archived evidence only
