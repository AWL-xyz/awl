#!/usr/bin/env python3
import argparse,hashlib,json,os,signal,subprocess,tempfile,time
from pathlib import Path
from PIL import ImageGrab
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);a=p.parse_args();sdk=a.sdk.resolve();out=Path(__file__).resolve().parent
 display=next(':'+str(n) for n in range(91,120) if not Path('/tmp/.X11-unix/X'+str(n)).exists())
 xvfb=subprocess.Popen(['Xvfb',display,'-screen','0','1280x880x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 terminal=None
 try:
  with tempfile.TemporaryDirectory(prefix='Awl-actual-terminal-',dir='/var/tmp') as td:
   work=Path(td);ready=work/'ready';script=work/'session.sh';transcript=work/'transcript.txt'
   script.write_text('''#!/bin/bash
set -eu
cd "$AWL_CAPTURE_WORK"
export PATH="$AWL_CAPTURE_SDK/bin:/usr/bin:/bin"
export XDG_CACHE_HOME=/var/tmp/Awl-capture-cache
PS4='$ '
printf 'Awl / native SDK, real compilation and execution\\n\\n'
set -x
awl --version
AwL InIt Demo
set +x
cat > Lib.aw <<'SOURCE'
exports(@r func answer()->i64 return 42; end;);
SOURCE
cat > main.aw <<'SOURCE'
use Lib.aw;
func main()->i64 print(Lib.answer()); return 0; end;
SOURCE
set -x
cat Lib.aw main.aw
AWL BuIlD
./build/Demo
awl build main.aw -o single
./single
ls Demo.awproj main.aw Lib.aw
set +x
printf '\\nall shown commands ran against the complete bundled backend\\nproject and import names retained their exact case\\n'
touch "$AWL_CAPTURE_READY"
sleep 120
''')
   env={**os.environ,'DISPLAY':display,'AWL_CAPTURE_WORK':str(work),'AWL_CAPTURE_SDK':str(sdk),'AWL_CAPTURE_READY':str(ready),'LC_ALL':'C.UTF-8'};time.sleep(.3)
   terminal=subprocess.Popen(['xterm','-title','Awl Software Development Kit','-geometry','114x34+18+18','-fa','DejaVu Sans Mono','-fs','13','-bg','#101820','-fg','#d2e5e1','-e','/usr/bin/script','-q','-f','-c','/bin/bash '+str(script),str(transcript)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
   limit=time.monotonic()+90
   while not ready.exists():
    if terminal.poll() is not None:raise RuntimeError('terminal exited: '+(transcript.read_text(errors='replace') if transcript.exists() else 'no transcript'))
    if time.monotonic()>limit:raise RuntimeError('terminal compilation deadline exceeded')
    time.sleep(.1)
   time.sleep(.3);image=out/'Awl-sdk.png';ImageGrab.grab(xdisplay=display).save(image,optimize=True);(out/'transcript.txt').write_bytes(transcript.read_bytes());report={'status':'PASS','method':'actual Xvfb/Xterm display capture, genuine shell/compiler/program output, no generated/mock terminal content','compiler_sha256':sha(sdk/'bin/kcc'),'image_sha256':sha(image),'transcript_sha256':sha(out/'transcript.txt'),'source_sha256':{'Lib.aw':sha(work/'Lib.aw'),'main.aw':sha(work/'main.aw'),'Demo.awproj':sha(work/'Demo.awproj')},'harness_sha256':sha(Path(__file__))};(out/'capture.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS genuine Awl SDK terminal capture')
 finally:
  if terminal is not None:
   try:os.killpg(terminal.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   terminal.wait(timeout=10)
  xvfb.terminate();xvfb.wait(timeout=10)
if __name__=='__main__':main()
