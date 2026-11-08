#!/usr/bin/env python3
"""Capture a REAL Awl window; no rendering/scene math in this helper.
Contributor recording tools: python-xlib, Pillow, imageio-ffmpeg, running X11.
"""
from pathlib import Path
import json
import os
import subprocess
import time
import hashlib
from Xlib import X, display, protocol
from PIL import Image
import imageio_ffmpeg

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    binary=ROOT/'build/window-pyramid'
    subprocess.run([str(ROOT/'build/Awl-linux-x86_64/bin/kcc'),'build',str(ROOT/'examples/platform/window_pyramid.aw'),'-O','3','-o',str(binary)],check=True)
    d=display.Display()
    existing={w.id for w in d.screen().root.query_tree().children}
    output=HERE/'native-window-pyramid-5s.mp4'
    process=subprocess.Popen([str(binary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    encoder=None
    try:
        w=None
        for _ in range(150):
            candidates=[w for w in d.screen().root.query_tree().children if w.id not in existing]
            if candidates:w=candidates[0];break
            if process.poll() is not None:raise RuntimeError(process.communicate())
            time.sleep(.02)
        if w is None:raise RuntimeError('Native window did not appear')
        # Read back from the X server, NOT the renderer's stdout or buffers.
        time.sleep(.15)
        encoder=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','480x480','-r','30','-i','-','-an','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
        start=time.monotonic();hashes=[]
        for frame in range(150):
            remaining=start+frame/30-time.monotonic()
            if remaining>0:time.sleep(remaining)
            raw=w.get_image(0,0,480,480,X.ZPixmap,0xffffffff)
            im=Image.frombytes('RGB',(480,480),raw.data,'raw','BGRX')
            payload=im.tobytes();hashes.append(hashlib.sha256(payload).hexdigest());encoder.stdin.write(payload)
            if frame==18:im.save(HERE/'native-window.png')
        encoder.stdin.close();assert encoder.wait(timeout=30)==0
        w.send_event(protocol.event.ClientMessage(window=w,client_type=d.intern_atom('WM_PROTOCOLS'),data=(32,[d.intern_atom('WM_DELETE_WINDOW'),0,0,0,0])),event_mask=0);d.flush()
        stdout,stderr=process.communicate(timeout=5)
        assert process.returncode==0,(stdout,stderr)
        assert len(set(hashes))>30,'No meaningful animation captured'
        # Decode final video to independently check frame count/resolution.
        decoded=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(output),'-f','rawvideo','-pix_fmt','rgb24','-'])
        assert len(decoded)==150*480*480*3
        report={'status':'passed','capture':'X11 server GetImage of actual Awl-owned window','native_renderer_and_window':'compiled examples/platform/window_pyramid.aw; no Python/Xlib/SDL application dependency',
                'recording_helper':'Python/Xlib reads display pixels; ffmpeg encodes H.264 only','frames':150,'fps':30,'duration_seconds':5,'resolution':[480,480],
                'distinct_captured_frames':len(set(hashes)),'decoded_frames_verified':150,'native_exit_on_WM_DELETE_WINDOW':process.returncode,
                'display':os.environ.get('DISPLAY'),'video_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                'source_sha256':hashlib.sha256((ROOT/'examples/platform/window_pyramid.aw').read_bytes()).hexdigest()}
        (HERE/'recording-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        if process.poll() is None:process.kill();process.communicate()
        if encoder is not None and encoder.poll() is None:encoder.kill();encoder.wait()
        d.close()
if __name__=='__main__':main()
