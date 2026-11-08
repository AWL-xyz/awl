## 0.21 update
Native Windows USER32/GDI now implements the framebuffer/event API too; see
[WIN32-GUI.md](WIN32-GUI.md) for platform-specific key codes, bounds and Wine-only
Windows validation. The details below describe the original Linux X11 backend.

# Native application primitives — 0.8.2-dev

**Implemented and locally tested, experimental. Not a full language or GUI toolkit.**

The native compiler recognizes the original17 platform/resource intrinsics plus0.8.2 `window_set_title` and9 string intrinsics. The independent arena verifier validates their exact signatures; native C emission embeds the runtime only when used. No general foreign-call escape hatch was added. Python's reference compiler does not implement these new intrinsics; it remains a contributor reference for the older value-language subset.

## A real window, not stdout graphics

```Awl
function main() -> i64
    local w: i64 = window_open(320,240)
    if w == 0 then return 1 end
    local running: bool = true
    while running do
        local event: i64 = window_poll(w)
        while event != 0 and running do
            if event == 1 then running = false end
            event = window_poll(w)
        end
        if running then
            window_set_pixel(w,10,10,16755200)
            running = window_present(w)
            sleep_millis(16)
        end
    end
    window_close(w)
    return 0
end
```

Run `examples/platform/window_pyramid.aw` for the actual shaded, rotating, resize-aware pyramid. Escape or a normal window-close request exits. Animation uses monotonic elapsed time, not recording frame count. All ray rendering and presentation occur in the native executable.

## Implemented API

| Function | Exact argument types → result |
|---|---|
| `buffer_new(size)` | i64 → i64 handle; zero on failure |
| `buffer_size(b)` | i64 → i64 |
| `buffer_get(b,index)` | i64,i64 → u8 |
| `buffer_set(b,index,value)` | i64,i64,u8 → unit |
| `buffer_free(b)` | i64 → unit |
| `clock_millis()` | → i64, monotonic milliseconds |
| `sleep_millis(ms)` | i64 → unit; 0–60000 |
| `window_open(width,height)` | i64,i64 → i64 handle; zero on failure |
| `window_width(w)`, `window_height(w)` | i64 → i64 |
| `window_set_pixel(w,x,y,rgb)` | i64,i64,i64,i64 → unit; RGB 0xRRGGBB represented as decimal integer |
| `window_present(w)` | i64 → bool; queues presentation, false on detected failure |
| `window_poll(w)` | i64 → i64 event code |
| `window_key(w)` | i64 → i64, last raw X11 keycode/button detail |
| `window_mouse_x(w)`, `window_mouse_y(w)` | i64 → i64, last input event's coordinates |
| `window_set_title(w,title)` | i64,string → bool; UTF-8, ≤1,024 bytes/no NUL; see STRINGS.md |
| `window_close(w)` | i64 → unit |

Event codes: 0 none, 1 close/disconnect/protocol failure, 2 expose, 3 resize, 4/5 key down/up, 6 motion, 7/8 button down/up. Drain events before drawing; a resize replaces/zeroes the framebuffer and updates dimensions. A close event does not free the handle: close it explicitly. Keycodes are physical X11 codes, **not** portable key names or text/IME input. The demo's Escape=9 is specific to the tested X11 mapping.

Handles are checked integers, not pointers. Copied handles alias the same resource. Invalid/stale/wrong-kind handles, bounds violations, invalid RGB values and invalid sleep intervals abort with `Awl resource trap`. This catches runtime misuse; it is **not compile-time ownership/borrow checking**. IDs are never reused within a process; exhaustion fails allocation rather than wrapping. Buffer/window ID ranges are disjoint. Double-free/double-close is an error, not an idempotent operation.

Buffers are zero-initialized byte storage: 64 live handles, 16 MiB per buffer, 64 MiB total buffer payload. Zero-size buffers are valid but cannot be indexed. Windows: 16 live handles, dimensions 1–2048, 64 MiB total client framebuffer payload. Server pixmaps consume additional display-server memory. Caps are separate, not an aggregate process-memory sandbox. Resources still live at process termination are reclaimed by the OS; applications should free/close explicitly. This is not yet generic arrays/slices or automatic lifetime management. Immutable strings were added in0.8.2-dev with separately bounded process-lifetime storage (STRINGS.md). Native source modules were added in0.8.1-dev; see MODULES.md.

## Native Linux backend

Implementation: `compiler/native/kplatform.c`, embedded deterministically by `compiler/generate_platform.py` into `kplatform.inc`. Signature schema: `kplatform-signatures.inc`.

The Linux x86-64 runtime speaks a narrow, bounded **X11 protocol subset over local Unix sockets**. It uses only the shipped musl/OS facilities; there is no Xlib/SDL shared-library dependency, Python helper, subprocess, downloaded library or host SDK in the application path. Frames upload to a server pixmap, then copy to the window; partial row uploads are not presented directly. This is software framebuffer presentation, not GPU acceleration, vsync or a latency guarantee.

Requirements/limits:

- A running local X server, accessible `/tmp/.X11-unix/XN`, `DISPLAY=:N` or `unix:N`, and screen zero. Remote/TCP display names and nonzero screens fail cleanly.
- Supported setup: little-endian images, 24/32-bit root depth, 32-bit pixels and standard TrueColor RGB masks. Other formats fail rather than guessing.
- Reads MIT-MAGIC-COOKIE-1 credentials from `XAUTHORITY` or `$HOME/.Xauthority`; no authentication bypass is implemented. No-auth servers also work if configured by their administrator.
- Connection/setup reads are bounded and timed; writes have socket timeouts. This is not a formally audited, hostile-display-server sandbox or a hard end-to-end deadline guarantee.
- Local validation used authenticated **Xvfb**, not a physical desktop/compositor matrix. Xwayland compatibility is plausible from the protocol, but not separately validated. Native Wayland, Windows and macOS window backends are unimplemented; unsupported OS window-open returns zero.
- No widgets, fonts, clipboard, DPI scaling, accessibility, Unicode input, gamepad, audio, GPU API, file dialogs or application packaging yet.

The Awl-only development-tool contract remains intact. A display server is an OS runtime facility, not a compiler/SDK dependency. A headless root can compile the GUI program but cannot open a window; `window_open` returns zero.

## Evidence and development delivery

- Ten new methods pass on the static bundled product and on ASan/UBSan-instrumented emitted C. Tests cover exact framebuffer readback, resize, key/mouse/button events, close, valid cookie authentication/rejection, malformed setup, resource limits and stale/bounds failures.
- Full 276-method suites pass in three configurations. These are repeated methods, not 828 distinct tests. The new intrinsics are tested through native KCC in every configuration, not emulated by Python.
- Native scanner/parser/verifier sanitizer harnesses pass; verifier coverage now includes 79 targeted corruptions plus 10,000 structural mutations.
- Reports: `tests/platform-tests.txt`, `platform-sanitized.txt`, `platform-frontend-sanitized.txt`, `platform-validation.json` and any final overlay acceptance report.

0.8.0-dev is an experimental development update, not a production release. The previous 0.7.1 archive remains immutable and does **not** contain these APIs. A compact native update, when delivered, requires that complete 0.7.1 Awl installation and reuses its pinned shipped toolchain. No Python or external development packages are needed to apply/run it. Building the compiler and running contributor display/sanitizer/recording tests have separate host-tool requirements.

The larger application-platform goal is in `APPLICATION-PLATFORM.md`. Native source modules now exist in0.8.1-dev. Next foundations include strings, typed buffers/arrays, explicit resource types/errors and ownership. Backend networking/HTTP/TLS, browser frontend compilation and production application tooling remain unfinished.

Subsequent0.8.3 adds13 typed builder intrinsics (SPOOLS.md), bringing the shared native schema to40 intrinsics. Builder-only programs do not embed or require the platform/window runtime.

##0.23 OS-family introspection
`platform_kind()->i64` returns1on Linux,2on Windows,0otherwise. It is a normal
builtin signature shared by native checking/verifying/emission. Pixelboard uses
it to choose backend-specific S/L shortcut codes; no normalized text/keyboard
layout, IME or richer window toolkit is implied. See PIXELBOARD-FILES.md.
