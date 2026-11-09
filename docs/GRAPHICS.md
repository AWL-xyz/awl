# native source graphics and color lab

`examples/apps/colorlab/Graphics.aw` supplies reusable CPU drawing on typed pixel vectors, the native Color Lab app uses it for a working RGB/grayscale picker, text and controls are rendered by Awl source, not a Python UI or host widget framework

## build and use

with the current complete development toolchain

```sh
cd examples/apps/colorlab
awl build
./build/colorlab
```

click or drag the red/green/blue bars, click the grayscale strip to select equal channels, close the native window to print the final `R G B` decimal values to stdout

initial RGB is78/166/224, layout is720x440, expose/resize events redraw against the actual window dimensions, smaller windows crop the fixed layout rather than relayout, this isn't a responsive widget toolkit

normal close exits0, arguments2, window/render/output failure3,2048-redraw budget exhaustion6, initial pixel-vector allocation failure9, no idle expiry, at most64 events are handled before yielding to drawing

the redraw cap keeps this app inside the current immutable-text allocation model, it isn't unrestricted long-running desktop software, dragging outside the window has no pointer-grab guarantee

## source helper contract

all public drawing functions return bool, bad sizes/colors/coordinates reject before changing pixel contents, valid offscreen geometry clips to the surface and can be a successful no-op

- `rgb(r,g,b)` and `gray(level)`, channels0..255, invalid returns-1
- `surface(borrow pixels,width,height,color)`, reserve before replacing the row-major `vector<i64>`,1..2048 dimensions, at most1048576 pixels, growth failure preserves old content
- `rect(...)`, filled half-open rectangle, extents0..65536
- `line(...)`, endpoint-inclusive integer rasterization in all octants, at most65536 logical steps, offscreen points are skipped rather than geometrically changing endpoints, half-way ties are direction-dependent
- `circle(...)`, filled integer disk, radius0..4096, clipped bounding-box scan with squared-distance coverage
- `draw_text(...,payload,scale,color)`, authored5x7 bitmap glyphs with6x8 advance, scales1..8 and at most512 codepoints, LF starts a new line
- `present(window,borrow pixels,width,height)`, checks dimensions and every color before native framebuffer writes, then presents

colors are packed24-bit RGB without alpha, positions/line endpoints must fit-32768..32767, geometry arithmetic stays in bounded i64 ranges, drawing requires an exact width*height vector length, invalid/stale resource handles still trap under runtime rules

text supports printable ASCII shapes, lowercase intentionally uses uppercase glyphs, unsupported codepoints use `?`, this isn't Unicode shaping, font loading, antialiasing, IME, accessibility, proportional fonts or a general text editor

caller owns the pixel vector and must preserve valid RGB elements when mutating it directly, surfaces aren't opaque types, present requires a valid live native window, arbitrary generic owned aggregates aren't added

## executed evidence

`tests/graphics.json`,275 cases and59503 pixel/status assertions EACH bundled native/strict generated-C ASan/UBSan, independent closed-form line and per-pixel rectangle/circle oracles, clipping, extreme endpoints, every printable ASCII glyph, scaling, fallback and invalid-input preservation

`tests/colorlab-gui.json`,17 checks EACH native/sanitized on real X11 windows, hover/click/drag/release, grayscale, resize, native font pixels, final RGB stdout and clean close, mouse input is injected by Xlib on Xvfb, not physical-device acceptance

`demos/colorlab/native-colorlab.png` is an actual native window captured by XGetImage, no generated/mock image, the GUI test script reproduces the capture

measured process times in the geometry report include printing verification pixels, GUI observed waits include10ms polling and the X server, neither is a parser-style throughput or physical input-latency benchmark

compiler/protected release archives are unchanged, current source isn't a newly published standalone bundle, native Windows and browser execution aren't qualified, the offline editor includes sources but doesn't implement typed vectors needed to run this app

capability remains20.0% =9/45, desktop was already stage2, reusable primitives and a useful color picker close a real UI gap but don't establish stage3 or a full3D renderer

## research and evidence storage

https://www.x.org/releases/current/doc/libX11/libX11/libX11.html is the primary reference for X11 window/event/image concepts, actual existing native event codes and framebuffer bounds were checked against `compiler/native/kplatform.c`, line design was reviewed against Bresenham's integer error formulation and tested against a separate closed-form oracle

authored glyph rows are preserved in `tests/font5x7.json`, font fixtures share the glyph designs but independently check bit packing/raster placement, no third-party font asset is embedded

historical `tests/win32-gui.json` was losslessly archived as `.json.gz` for workspace headroom, decompressed SHA256 remains `9ebfb73feb31347782ce5476d955b08d37c7449c9d46b134eb286816f99235a8`, no evidence or protected distribution was discarded
