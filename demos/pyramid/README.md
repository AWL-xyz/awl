# Spinning pyramid — real Awl-rendered output

`spinning-pyramid-5s.mp4`: 150 frames at30fps, five seconds, H.264,640×640.
The Awl renderer computes320×320 pixels; the encoder upscales with Lanczos.

Renderer source: `../../examples/graphics/spinning_pyramid.aw`.

All scene computations execute in compiled Awl: fixed-point perspective rays,
Y-axis rotation, five-plane square-pyramid intersection, camera-relative key light,
view-facing shading, floor shadow rays, atmospheric floor and RGB values.
Bhaskara's rational sine approximation avoids unsupported floats/trigonometry.
The fixed camera is elevated and looks down at the origin.

Awl0.7.1 has no window, string/file, image or video API. This demo emits packed
RGB integers through its existing print primitive. `record.py` transports these
pixels into ffmpeg and encodes a video; it does not implement the renderer.
This is an offline frame recording, not a recording of a native Awl GUI/window.
No compiler or language feature was changed to make the demo.

From the repository root, with the full native Awl prefix available:

```sh
build/Awl-linux-x86_64/bin/kcc build examples/graphics/spinning_pyramid.aw -o demos/pyramid/spinning-pyramid -O 3
# Recording helper only, not a dependency of the Awl renderer/compiler:
python3 -m pip install numpy Pillow imageio-ffmpeg
python3 demos/pyramid/record.py
```

Recording validation: `recording-validation.json`. The final MP4 was decoded
successfully into150 frames; frame0 and frame18 differ, confirming animation.
The delivered0.7.1 compiler archive remains unchanged; this new source is separate.
