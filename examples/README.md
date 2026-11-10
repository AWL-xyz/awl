# examples

examples use the current Aesop source syntax, contributor builds use `acc check PATH` and `acc emit-c PATH`, `acc build` needs a complete matching SDK resource layout

## language tour

- [`tour/`](tour/) broad syntax and runtime tour
- [`collections/`](collections/), [`containers/`](containers/), [`loops/`](loops/), [`structs/`](structs/), [`enums/`](enums/)
- [`exports/`](exports/), [`modules/`](modules/), [`resource-structs/`](resource-structs/)
- [`numeric/`](numeric/), [`parsing/`](parsing/), [`native/`](native/)

## Packages

- [`packages-demo/`](packages-demo/) installs and uses `env`, `fsp` and `json`
- [`time-demo/`](time-demo/) installs and uses [`time`](../docs/TIME.md)

## applications

- [`apps/colorlab/`](apps/colorlab/) framebuffer application
- [`apps/pipe/`](apps/pipe/), [`apps/save/`](apps/save/), [`apps/serve/`](apps/serve/), [`apps/sort/`](apps/sort/), [`apps/valueserve/`](apps/valueserve/) bounded native utilities
- [`../apps/taskrun/`](../apps/taskrun/) subprocess supervisor
- [`../apps/logwindow/`](../apps/logwindow/) bounded UTF-8 log processing
- [`../apps/board/`](../apps/board/) persistent taskboard with native service and shared WebAssembly filter

legacy example trees and overlays are not current sources, historical material is preserved in private capsules and archived evidence only
