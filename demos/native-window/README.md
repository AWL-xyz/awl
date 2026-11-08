# Actual native Awl window recording

`native-window-pyramid-5s.mp4` records a real Awl-owned X11 window.
The Awl program computes all scene pixels, opens its window, handles events,
presents through a server pixmap, and exits on WM_DELETE_WINDOW.

Source: `../../examples/platform/window_pyramid.aw`.

This is **not** the earlier stdout-to-video demo. `record.py` reads pixels from
the display server and encodes H.264; the native application itself does not
use Python/Xlib/SDL. Recording/test tools are contributor-only dependencies.

The MP4 is150captureframes at30fps (5seconds),480×480. There were57distinct
captured native frames: recording rate is NOT a30fps renderer performance claim.
Final video decoded150frames; native application exited0 on the close request.
See recording-validation.json for hashes and checks.

Local display validation is Xvfb, not a physical desktop/Wayland/Windows matrix.
See ../../docs/NATIVE-WINDOWS.md for actual API, requirements and limitations.
