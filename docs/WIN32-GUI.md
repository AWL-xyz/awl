# Native Win32 framebuffer runtime (0.21 engineering preview)

The window_open/width/height/set_pixel/present/poll/key/mouse/close/title APIs now
have a native Windows USER32/GDI implementation as well as the Linux local-X11
client. No SDL/Xlib/Python toolkit or external SDK is used by Awl programs.
Windows GUI programs require a functioning Windows desktop; Linux GUI programs
require the supported local TrueColor X11 server. Headless window_open may fail.

## Architecture and limits

One GUI thread;16windows;1..2048client pixels per dimension;64MiB combined allocated
32-bit framebuffer payload. OS surfaces, window manager and metadata cost extra.
Handles are monotonically increasing opaque integers, not pointers. Invalid/stale
handles and pixel bounds trap. Opening fails with0 on resource/OS/allocation error.
Windows links standard OS user32/gdi32; the native driver supplies the link flags.

A stable table slot is associated with HWND via WM_NCCREATE/GWLP_USERDATA. Creation
min/max sizing is handled even before WM_NCCREATE, preserving tiny client sizes.
Callbacks never call Awl functions or reallocate pixel storage. WM_SIZE queues a
resize; framebuffer replacement happens only when that window consumes the resize
in window_poll. This avoids callback reentrancy invalidating a blit buffer. New
resize storage is zeroed; the application redraws. Failed/over-limit resizing
closes the logical window while retaining its old allocation until window_close.
Minimizing retains the framebuffer; restore does not imply a zero-sized surface.

window_present uses a top-down32-bit BI_RGB DIB. WM_PAINT redraws retained pixels
and reports expose. No GPU, vsync, high-performance rendering or precise frame-time
claim. window_poll pumps at most1024thread messages, then returns one event for
its requested window. Per-window64event rings coalesce consecutive expose/resize/
pointer-motion events. Discrete input is not silently overwritten: overflow closes
that logical window. Close/quit is sticky, present/title then fail; close releases
native window and framebuffer. There is no hidden asynchronous worker thread.
Native callback failures and event pressure are not exceptions in user Awl code.

Events remain0none,1close,2expose,3resize,4/5key down/up,6motion,7/8button down/up.
Buttons1left/2middle/3right. Coordinates are signed client pixels; dragging may
report positions outside the canvas, so applications must check before indexing.
Windows key values are virtual-key codes; Linux values remain X11 physical
keycodes. They are NOT interchangeable or a text-input API. Key events on Windows
retain the most recently consumed pointer coordinates. Standard Alt-F4 handling
is retained. UTF-8 titles: <=1024bytes, no embedded NUL, empty permitted, strict
UTF8→UTF16 conversion. No IME/Unicode text events/fonts/widgets/DPI/clipboard yet.

## Application and evidence

examples/apps/pixelboard is an actual Awl-only two-module in-memory paint app.
Its384cells live in a scoped int_vector; synchronous borrowed helper functions
paint/clear/render. Left button paints/drags; right button cycles four brush
colors; any key clears; resize redraws the same canvas; OS close exits normally.
No persistence, undo, text/toolbars, packaged assets or production toolkit claim.
The pyramid example now relies on OS close, not an X11-only Escape keycode.

Contributor gates use real USER32/GDI windows and programmatic input, not simulated
API stubs. Wine execution is qualified emulation, NOT real Windows-machine proof.
The separate Windows compiler backend remains blocked by upstream self-path
resolution under Wine; GUI tests cross-compile emitted C with a separate Linux
contributor compiler and execute Windows PE programs. This is NOT concealed as an
installed Windows-host compiler pass. Real Windows CI includes the GUI gate but
has not been run remotely here. See tests/win32-* and WINDOWS.md.

Local0.21 development gates:531methods EACH reference/native-parser/native-frontend,
zero skips;247resource +14platform sanitizer methods; native C++ frontend/project/
verifier sanitizer passes325targeted+10000structural mutations; Win32 runtime17
groups + actual Pixelboard4probe checks under Wine. Windows frontend/private
mutation tests also execute as PE under Wine. Full-build warmed Linux Pixelboard
median390.754ms across7samples; not Windows-host build performance. Exact archive
acceptance and final hashes are external reports (not self-referential embeds).

##0.23 Pixelboard update
The shared Awl app now has native-file drawing persistence; see
PIXELBOARD-FILES.md. Current qualified tests additionally exercise save, clear/
load, overwrite refusal, process restart and save-as; Wine remains not a native
Windows host. Historical0.21 counts above are not current artifact acceptance.
