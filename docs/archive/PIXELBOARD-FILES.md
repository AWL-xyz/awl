# Pixelboard drawings — 0.23 engineering milestone

Pixelboard now loads and saves real drawings using Awl's native file API. Its
renderer, storage codec, validation and GUI event logic are Awl source modules.
No Python renderer or persistence helper is part of the application.

## Use

```
kcc build examples/apps/pixelboard/main.aw -o pixelboard
./pixelboard new-drawing.kpb
./pixelboard another-new-drawing.kpb existing-drawing.kpb
```

`examples/apps/pixelboard/sample.kpb` is a drawing saved by the actual native
application; use it as the second argument with a fresh output path, then L.

Use `.exe` and Windows invocation syntax on Windows. Arguments are optional:
`pixelboard [NEW_SAVE_PATH [LOAD_PATH]]`. The default path is `pixelboard.kpb`;
load defaults to the save path. Loading is explicit, not automatic on launch.
- Left click/drag paints; right button cycles four brush colors.
- **S** saves to a **new** file; an existing destination is refused.
- **L** validates and loads the selected input into the canvas.
- Other keys retain the existing clear-canvas behavior; resize retains cells.
- The window title reports saved, loaded, refused-overwrite or failure status.

To edit an existing drawing into a new file, launch with both paths, press L,
paint, then S. There is no file dialog, filename editing widget, overwrite,
autosave, undo or atomic-replacement operation. Keyboard shortcuts use Windows
virtual S/L keys or Linux X11 US physical S/L keycodes; they are **not** a
keyboard-layout-independent text/IME interface. `platform.kind()->i64` reports
1 Linux, 2 Windows, 0 other; it only selects these backend-specific key codes.

## Format: KPBOARD1 (`.kpb`)

Exactly **1164 bytes**, independent of host byte order:

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 8 | ASCII `KPBOARD1`, format/version magic |
| 8 | 1152 | 384 RGB triples: 24 columns × 16 rows, row-major; R then G then B |
| 1160 | 4 | Adler-32 over bytes 0..1159, big-endian |

Every RGB channel is an unsigned byte. All RGB24 colors are valid, including
black/white, not just the current brush palette. Other dimensions/versions,
truncated or trailing data, bad magic and checksum mismatches are rejected.
Adler-32 detects some accidental corruption; it is **not authentication**, and
malicious modifications with a recomputed checksum can be valid drawings.
The format is not PNG, a general image loader or compressed zlib data.

The checksum follows RFC1950's Adler formula. This fixed1160-byte input allows
modular reduction after accumulation: worst-case a<=295801 and b<=171713060,
well below checked i64 limits. It does not justify postponing reductions for
arbitrarily long inputs. An independent zlib.adler32 oracle checks emitted files.
No zlib library is required by the Awl application.

## Failure and resource contracts

Saving validates model length and every RGB value, encodes into one1164-byte
buffer, THEN exclusively creates the path, loops short writes, flushes and checks
output close. Existing files are not intentionally replaced or truncated. A
failed save can leave a **partial new file**, which must not be mistaken for a
successful save. Flush is the OS request, not directory sync or guaranteed
power-loss durability. This is **not atomic replacement**, rollback, a stable
filesystem snapshot or a path-security sandbox. Concurrent processes can modify
files, and underlying filesystem/OS semantics still apply.

Loading reads into a1165-byte staging buffer (the extra byte detects growth),
checks exact length, magic and checksum, then changes cells only after all checks
pass. Ordinary read/format/allocation errors leave every existing cell unchanged.
The commit performs only fixed-length element assignments, with no allocations
or I/O. Invalid/stale vector handles remain programming traps, not load errors.
Source close is deferred; output close is explicit. No buffer or file is kept
open between operations; repeated loads do not consume handle slots.

Storage calls `storage.save_new(borrow cells, path)` / `storage.load(borrow cells,
path)` return0 on success, negative file/allocation errors, or-5 for invalid
model/format. These are application-module functions, not new compiler intrinsics.
Internal codec helpers assume the fixed buffer sizes documented in their source.

## Evidence and limitations

`tests/persistence-*` contains development/exact gates when run, independent binary
oracles, GUI save/clear/load/restart and malformed-file rollback checks. Wine PE
execution is not real Windows-host backend acceptance. The existing Windows Zig
self-path blocker under Wine remains separately tracked. These are engineering
features of a small bounded paint app, not a production desktop toolkit or a 3D
renderer. Full3D/model/lighting/shadow support remains unimplemented.

Primary references: https://www.rfc-editor.org/rfc/rfc1950 (Adler-32);
https://man7.org/linux/man-pages/man2/open.2.html (exclusive creation);
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
(Windows creation disposition). Research informs tests, not a blanket filesystem
safety/performance guarantee.
