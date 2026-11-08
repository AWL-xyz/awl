#!/usr/bin/env python3
"""Encode Awl-rendered packed RGB stdout. No 3D math or scene rendering here.
Contributor/demo recording dependencies: numpy, Pillow, imageio-ffmpeg.
The Awl executable itself needs none of them.
"""
from pathlib import Path
import hashlib
import itertools
import json
import subprocess
import time
import numpy as np
import imageio_ffmpeg
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WIDTH = HEIGHT = 320
FRAMES = 150
FPS = 30

def main():
    output = HERE / 'spinning-pyramid-5s.mp4'
    encoder = subprocess.Popen([
        imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
        '-r', str(FPS), '-i', '-', '-an', '-vf', 'scale=640:640:flags=lanczos',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)
    ], stdin=subprocess.PIPE)
    start = time.perf_counter()
    process = subprocess.Popen([str(HERE / 'spinning-pyramid')], stdout=subprocess.PIPE)
    rendered_hash = hashlib.sha256()
    try:
        for frame in range(FRAMES):
            text = b''.join(itertools.islice(process.stdout, WIDTH * HEIGHT))
            pixels = np.fromstring(text, dtype=np.int64, sep='\n')
            assert pixels.size == WIDTH * HEIGHT, (frame, pixels.size)
            assert ((pixels >= 0) & (pixels <= 0xffffff)).all()
            rgb = np.stack(((pixels >> 16) & 255, (pixels >> 8) & 255, pixels & 255), axis=-1).astype(np.uint8).reshape(HEIGHT, WIDTH, 3)
            payload = rgb.tobytes()
            rendered_hash.update(payload)
            encoder.stdin.write(payload)
            if frame in (0, 37, 75):
                Image.fromarray(rgb).save(HERE / f'frame-{frame:03d}.png')
        assert process.stdout.read() == b'', 'Unexpected extra output'
        assert process.wait(timeout=10) == 0
        encoder.stdin.close()
        assert encoder.wait(timeout=60) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if encoder.poll() is None:
            encoder.kill()
            encoder.wait()
    report = {
        'status': 'passed', 'frames': FRAMES, 'fps': FPS,
        'duration_seconds': FRAMES / FPS, 'render_resolution': [WIDTH, HEIGHT],
        'encoded_resolution': [640, 640], 'renderer': 'examples/graphics/spinning_pyramid.aw compiled by native bundled KCC 0.7.1 at O3',
        'scene_computation': 'All rays, intersections, rotation, camera-relative lighting, shadow rays, floor and RGB colors computed in Awl',
        'helper_scope': 'Python parses packed RGB integers; ffmpeg rescales and encodes H.264. No scene rendering in helper.',
        'wall_seconds_render_transport_encode': time.perf_counter() - start,
        'raw_rgb_sha256': rendered_hash.hexdigest(),
        'video_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256((ROOT / 'examples/graphics/spinning_pyramid.aw').read_bytes()).hexdigest(),
        'executable_sha256': hashlib.sha256((HERE / 'spinning-pyramid').read_bytes()).hexdigest()
    }
    (HERE / 'recording-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
