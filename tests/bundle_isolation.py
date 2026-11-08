#!/usr/bin/env python3
"""Linux acceptance test: Awl-only chroot, private PID/mount/network namespaces.
Host Python/sudo/unshare/chroot set up the test; NONE is installed inside it.
Requires passwordless sudo and namespace/mount privileges on the test host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time
import tarfile
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'build/Awl-linux-x86_64'

def main():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path);parser.add_argument('--overlay',type=Path);parser.add_argument('--scratch',type=Path,default=Path('/var/tmp/Awl-distribution-tests'));args=parser.parse_args()
    if args.overlay and not args.archive:parser.error('--overlay requires base --archive')
    root=args.scratch.resolve()/('archive-isolation-root' if args.archive else 'bundle-isolation-root')
    if root.exists():shutil.rmtree(root)
    root.mkdir(parents=True)
    if args.archive:
        with tarfile.open(args.archive) as archive:archive.extractall(root,filter='data')
    else:shutil.copytree(PACKAGE,root/'Awl',symlinks=True)
    if args.overlay:
        with tarfile.open(args.overlay) as archive:archive.extractall(root/'Awl',filter='data')
    for name in ['proc','work','tmp','cache','dev']:
        (root/name).mkdir();(root/name).chmod(0o777)
    subprocess.run(['sudo','-n','mknod',str(root/'dev/null'),'c','1','3'],check=True)
    subprocess.run(['sudo','-n','chmod','666',str(root/'dev/null')],check=True)
    assert not any((root/p).exists() for p in ['usr','bin','sbin','lib','lib64','etc'])
    assert not list((root/'cache').iterdir())
    prefix=['sudo','-n','/usr/bin/env','-i','HOME=/work','XDG_CACHE_HOME=/cache','TMPDIR=/tmp','PATH=/no-host-tools','LC_ALL=C',
        '/usr/bin/unshare','--mount','--pid','--fork','--net','--mount-proc='+str(root/'proc'),
        '/usr/sbin/chroot','--userspec='+str(os.getuid())+':'+str(os.getgid()),str(root)]
    records=[]
    def invoke(args,code=0,stdout=None,stderr_part=None):
        start=time.perf_counter();r=subprocess.run(prefix+args,capture_output=True,text=True,timeout=180)
        assert r.returncode==code,(args,r.returncode,r.stdout,r.stderr)
        if stdout is not None:assert r.stdout==stdout,(args,r.stdout,stdout)
        if stderr_part is not None:assert stderr_part in r.stderr,(args,r.stderr)
        records.append({'argv':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.perf_counter()-start})
        return r
    invoke(['/Awl/bin/AwL','InIt','Demo'])
    (root/'Lib.aw').write_text('exports(@r func answer()->i64 return 42; end;);')
    (root/'main.aw').write_text('use Lib.aw; func main()->i64 print(Lib.answer()); return 0; end;')
    for alias in ['awl','awL','aWl','aWL','Awl','AwL','AWl','AWL']:
        r=invoke(['/Awl/bin/'+alias,'--HeLp']);assert 'Awl Software Development Kit' in r.stdout
        invoke(['/Awl/bin/'+alias,'BuIlD'],stdout='/build/Demo\n')
        invoke(['/build/Demo'],stdout='42\n')
    source=root/'work/first.aw';source.write_text('function main()->i64 print(40+2) return 0 end')
    invoke(['/Awl/bin/kcc','build','/work/first.aw','-o','/work/first'],stdout='/work/first\n')
    invoke(['/work/first'],stdout='42\n')
    example_outputs=json.loads((ROOT/'tests/example-outputs.json').read_text())
    for path in sorted((ROOT/'examples').glob('*.aw')):
        shutil.copy2(path,root/'work'/path.name)
        invoke(['/Awl/bin/kcc','run','/work/'+path.name],stdout=example_outputs[path.name])
    # New experimental runtime must also work without host libraries/display.
    manifest=json.loads((root/'Awl/manifest.json').read_text())
    if any(manifest.get('version','').startswith(v) for v in ['0.8.','0.9.','0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.']):
        shutil.copy2(ROOT/'examples/platform/buffers.aw',root/'work/buffers.aw')
        invoke(['/Awl/bin/kcc','run','/work/buffers.aw'],stdout='4\n0\n255\n42\n0\n')
        (root/'work/no-display.aw').write_text('function main()->i64 print(window_open(32,32)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/no-display.aw'],stdout='0\n')
        (root/'work/buffer-trap.aw').write_text('function main()->i64 local b:i64=buffer_new(1) print(buffer_get(b,1)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/buffer-trap.aw'],code=134,stderr_part='Awl resource trap')
    if any(manifest.get('version','').startswith(v) for v in ['0.8.1','0.8.2','0.8.3','0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0']):
        shutil.copytree(ROOT/'examples/modules',root/'work/modules')
        invoke(['/Awl/bin/kcc','run','/work/modules/main.aw'],stdout='10\n15\n3\n')
        invoke(['/Awl/bin/kcc','build','/work/modules/main.aw','-o','/work/modules/geometry/points.aw'],code=2,stderr_part='refusing to overwrite source')
        (root/'work/cycle.aw').write_text('import cycle function main()->i64 return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/cycle.aw'],code=1,stderr_part='E301')
    if any(manifest.get('version','').startswith(v) for v in ['0.8.2','0.8.3','0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0']):
        shutil.copy2(ROOT/'examples/strings/main.aw',root/'work/strings.aw')
        invoke(['/Awl/bin/kcc','run','/work/strings.aw'],stdout='Hello, Awl 🚀!\n5\n8\n🚀\ntrue\nAnswer: 42\n')
        (root/'work/string-trap.aw').write_text('function main()->i64 print(string_slice("é",1,1)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/string-trap.aw'],code=134,stderr_part='Awl string trap')
        (root/'work/bad-escape.aw').write_text('function main()->i64 print("\\u{d800}") return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/bad-escape.aw'],code=1,stderr_part='E102')
    if any(manifest.get('version','').startswith(v) for v in ['0.8.3','0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0']):
        shutil.copytree(ROOT/'examples/builders',root/'work/builders')
        invoke(['/Awl/bin/kcc','run','/work/builders/main.aw'],stdout='Awl café | 42\n13\n14\nInvalid scalar: recovered\nframe=99999\n100000 updates, one reusable builder\n')
        (root/'work/builder-stale.aw').write_text('function main()->i64 local b:spool=spool_new(8) spool_free(b) spool_clear(b) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/builder-stale.aw'],code=134,stderr_part='Awl text builder trap')
        (root/'work/builder-type.aw').write_text('function main()->i64 buffer_free(spool_new(8)) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/builder-type.aw'],code=1,stderr_part='E200')
    if any(manifest.get('version','').startswith(v) for v in ['0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0']):
        shutil.copy2(ROOT/'examples/cleanup/main.aw',root/'work/cleanup.aw')
        invoke(['/Awl/bin/kcc','run','/work/cleanup.aw'],stdout='frame=99999\n100000 calls: scoped cleanup on every return\ncafé\nInner scope released before this line\n')
        (root/'work/bad-defer.aw').write_text('function main()->i64 defer print(1) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/bad-defer.aw'],code=1,stderr_part='E200')
    if manifest.get('version','').startswith(('0.9.','0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copy2(ROOT/'examples/arrays/main.aw',root/'work/arrays.aw')
        invoke(['/Awl/bin/kcc','run','/work/arrays.aw'],stdout='Typed arrays: original / doubled\n3\n6\n7\n14\n11\n22\n15\n30\nNested update\n42\nValue copies preserve the original\ntrue\n')
        (root/'work/array-trap.aw').write_text('function main()->i64 local a:[i64;2]=[1,2] print(a[2]) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/array-trap.aw'],code=134,stderr_part='Awl array bounds trap')
        (root/'work/array-type.aw').write_text('function main()->i64 local a:[i64;2]=[1,true] return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/array-type.aw'],code=1,stderr_part='E200')
    if manifest.get('version','').startswith(('0.9.1','0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copy2(ROOT/'examples/repeat/main.aw',root/'work/repeat.aw')
        invoke(['/Awl/bin/kcc','run','/work/repeat.aw'],stdout='Compact fixed arrays\nSeed evaluated once\n1024\n7168\nIndependent rows after copy\n0\n42\n0\n')
        (root/'work/repeat-invalid.aw').write_text('function main()->i64 local a:[i64;2]=[1;0] return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/repeat-invalid.aw'],code=1,stderr_part='E100')
    if manifest.get('version','').startswith(('0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copy2(ROOT/'examples/scoped-owner/main.aw',root/'work/scoped-owner.aw')
        invoke(['/Awl/bin/kcc','run','/work/scoped-owner.aw'],stdout='frame=99999\n100000 scoped builders: automatic release\n1088890\nUnavailable allocation is safe to leave scope\nfalse\n')
        (root/'work/scoped-escape.aw').write_text('function f()->spool scoped b:spool=spool_new(8) return b end function main()->i64 return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/scoped-escape.aw'],code=1,stderr_part='E220')
        (root/'work/scoped-free.aw').write_text('function main()->i64 scoped b:spool=spool_new(8) spool_free(b) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/scoped-free.aw'],code=1,stderr_part='E220')
    if manifest.get('version','').startswith(('0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/borrows',root/'work/borrows')
        invoke(['/Awl/bin/kcc','run','/work/borrows/main.aw'],stdout='frame=99999\n100000 helper calls: one scoped builder\n1088890\ntrue\n')
        (root/'work/borrow-escape.aw').write_text('function f(borrow b:spool)->spool return b end function main()->i64 return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/borrow-escape.aw'],code=1,stderr_part='E220')
        (root/'work/borrow-free.aw').write_text('function f(borrow b:spool)->unit spool_free(b) end function main()->i64 return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/borrow-free.aw'],code=1,stderr_part='E220')
    if manifest.get('version','').startswith(('0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copy2(ROOT/'examples/moves/main.aw',root/'work/moves.aw')
        invoke(['/Awl/bin/kcc','run','/work/moves.aw'],stdout='frame=99999 / moved\n100000 local moves: one release per owner\n1888890\nMoved unavailable descriptor remains unavailable\nfalse\n')
        (root/'work/use-after-move.aw').write_text('function main()->i64 scoped a:spool=spool_new(8) scoped b:spool=move a print(spool_valid(a)) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/use-after-move.aw'],code=1,stderr_part='E221')
        (root/'work/cross-block-move.aw').write_text('function main()->i64 scoped a:spool=spool_new(8) while false do if true then scoped a:spool=move a end end return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/cross-block-move.aw'],code=1,stderr_part='E225' if manifest.get('version','').startswith(('0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')) else 'E221')
    if manifest.get('version','').startswith(('0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/own-params',root/'work/own-params')
        invoke(['/Awl/bin/kcc','run','/work/own-params/main.aw'],stdout='frame=99999\n100000 owning calls: callee releases builders\n1088890\nUnavailable handles transfer safely\nfalse\n')
        (root/'work/own-use.aw').write_text('function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool_new(8) take(move a) print(spool_valid(a)) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/own-use.aw'],code=1,stderr_part='E221')
        (root/'work/own-alias.aw').write_text('function take(borrow a:spool,own b:spool)->unit end function main()->i64 scoped a:spool=spool_new(8) take(a,move a) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/own-alias.aw'],code=1,stderr_part='E222')
    if manifest.get('version','').startswith(('0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/owned-results',root/'work/owned-results')
        invoke(['/Awl/bin/kcc','run','/work/owned-results/main.aw'],stdout='frame=99999 / returned\n100000 factory -> transform -> caller pipelines\n2188890\n')
        header='function make()->own spool scoped b:spool=spool_new(8) return move b end '
        for label,body in [('drop','make()'),('manual','local b:spool=make()')]:
            (root/('work/result-'+label+'.aw')).write_text(header+'function main()->i64 '+body+' return 0 end')
            invoke(['/Awl/bin/kcc','check','/work/result-'+label+'.aw'],code=1,stderr_part='E223')
    if manifest.get('version','').startswith(('0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/branch-joins',root/'work/branch-joins')
        invoke(['/Awl/bin/kcc','run','/work/branch-joins/main.aw'],stdout='frame=99999 / odd\n100000 conditional handoffs: one owner per path\n1738890\n')
        (root/'work/join-use.aw').write_text('function main()->i64 scoped a:spool=spool_new(8) if true then scoped b:spool=move a end spool_print(a) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/join-use.aw'],code=1,stderr_part='E221')
        (root/'work/join-shadow.aw').write_text('function main()->i64 scoped a:spool=spool_new(8) if false then scoped b:spool=move a local a:i64=1 end spool_print(a) return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/join-shadow.aw'],code=1,stderr_part='E221')
    if manifest.get('version','').startswith(('0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/match-joins',root/'work/match-joins')
        invoke(['/Awl/bin/kcc','run','/work/match-joins/main.aw'],stdout='frame=99999 / draw\n100000 match routes: moved or retained, one cleanup\n1555559\n')
        header='union Route One(n:i64) Two() end function main()->i64 scoped a:spool=spool_new(8) local r:Route=Route.One(1) '
        for label,body in [('use','scoped b:spool=move a'),('shadow','scoped b:spool=move a local a:i64=1')]:
            (root/('work/match-'+label+'.aw')).write_text(header+'match r then case Route.One(n) then '+body+' case Route.Two() then end spool_print(a) return 0 end')
            invoke(['/Awl/bin/kcc','check','/work/match-'+label+'.aw'],code=1,stderr_part='E221')
    if manifest.get('version','').startswith(('0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/reinit',root/'work/reinit')
        invoke(['/Awl/bin/kcc','run','/work/reinit/main.aw'],stdout='restored=99999\n100000 owner reinitializations: original cleanup slot\n2477780\n')
        header='function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool_new(8) '
        for label,body,diagnostic in [('maybe','if true then take(move a) end a=spool_new(8)','E224'),('live','a=spool_new(8)','E220')]:
            (root/('work/reinit-'+label+'.aw')).write_text(header+body+' return 0 end')
            invoke(['/Awl/bin/kcc','check','/work/reinit-'+label+'.aw'],code=1,stderr_part=diagnostic)
    if manifest.get('version','').startswith(('0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/loop-owners',root/'work/loop-owners')
        invoke(['/Awl/bin/kcc','run','/work/loop-owners/main.aw'],stdout='frame=99999\n100000 loop-carried owners: state restored on every backedge\n1088890\nFinal owner remains live\nframe=100000\n')
        header='function take(own b:spool)->unit end function main()->i64 scoped a:spool=spool_new(8) '
        for label,body in [('live','while false do take(move a) end'),('empty','take(move a) while false do a=spool_new(8) end')]:
            (root/('work/loop-'+label+'.aw')).write_text(header+body+' return 0 end')
            invoke(['/Awl/bin/kcc','check','/work/loop-'+label+'.aw'],code=1,stderr_part='E225')
    if manifest.get('version','').startswith(('0.19.','0.20.','0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/apps/intstats',root/'work/intstats')
        invoke(['/Awl/bin/kcc','build','/work/intstats/main.aw','-o','/work/intstats-tool'],stdout='/work/intstats-tool\n')
        invoke(['/work/intstats-tool','42','-7','19','0','42','-9223372036854775808','9223372036854775807'],stdout='count\n7\nminimum\n-9223372036854775808\nmaximum\n9223372036854775807\nsorted\n-9223372036854775808\n-7\n0\n19\n42\n42\n9223372036854775807\n')
        invoke(['/work/intstats-tool','9223372036854775808'],code=2,stdout='invalid signed 64-bit integer argument\n')
        invoke(['/work/intstats-tool'],code=2,stdout='usage: intstats INTEGER [INTEGER ...]\n')
        (root/'work/vector-trap.aw').write_text('function main()->i64 scoped v:int_vector=int_vector_new(0) print(int_vector_pop(v)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/vector-trap.aw'],code=134,stderr_part='Awl int vector trap')
        (root/'work/vector-copy.aw').write_text('function main()->i64 scoped v:int_vector=int_vector_new(0) local alias:int_vector=v return 0 end')
        invoke(['/Awl/bin/kcc','check','/work/vector-copy.aw'],code=1,stderr_part='E220')
    if manifest.get('version','').startswith(('0.21.','0.22.','0.23.','0.24.')):
        shutil.copytree(ROOT/'examples/apps/pixelboard',root/'work/pixelboard')
        invoke(['/Awl/bin/kcc','check','/work/pixelboard/main.aw'],stdout='/work/pixelboard/main.aw: checked (native frontend)\n')
        invoke(['/Awl/bin/kcc','build','/work/pixelboard/main.aw','-o','/work/pixelboard-tool'],stdout='/work/pixelboard-tool\n')
        # This intentionally headless rootfs has no X server: clean unavailable exit.
        invoke(['/work/pixelboard-tool'],code=3,stdout='')
    if manifest.get('version','').startswith(('0.22.','0.23.','0.24.')):
        for app in ['kcopy','textinfo']:
            shutil.copytree(ROOT/'examples/apps'/app,root/'work'/app)
            invoke(['/Awl/bin/kcc','build','/work/'+app+'/main.aw','-o','/work/'+app+'-tool'],stdout='/work/'+app+'-tool\n')
        payload=bytes(range(256))*513
        (root/'work/input.bin').write_bytes(payload)
        invoke(['/work/kcopy-tool','/work/input.bin','/work/copy é.bin'],stdout='bytes copied\n'+str(len(payload))+'\n')
        assert (root/'work/copy é.bin').read_bytes()==payload
        invoke(['/work/kcopy-tool','/work/input.bin','/work/copy é.bin'],code=4,stdout='cannot create destination\n-3\n')
        assert (root/'work/copy é.bin').read_bytes()==payload
        (root/'work/text.txt').write_bytes('café🙂'.encode())
        invoke(['/work/textinfo-tool','/work/text.txt'],stdout='bytes\n9\nUnicode scalars\n5\n')
        (root/'work/text.txt').write_bytes(b'\xff')
        invoke(['/work/textinfo-tool','/work/text.txt'],code=5,stdout='invalid UTF-8\n')
        (root/'work/file-trap.aw').write_text('function main()->i64 print(file_size(0)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/file-trap.aw'],code=134,stderr_part='Awl resource trap')
    if manifest.get('version','').startswith('0.23.'):
        import zlib
        shutil.copy2(ROOT/'examples/apps/pixelboard/storage.aw',root/'work/storage.aw')
        (root/'work/drawing.aw').write_text('import storage function main()->i64 scoped cells:int_vector=int_vector_new(384) local i:i64=0 while i<384 do int_vector_push(cells,i*1234567%16777216) i=i+1 end print(platform_kind()) print(storage.save_new(cells,"/work/drawing.kpb")) print(storage.save_new(cells,"/work/drawing.kpb")) int_vector_set(cells,0,42) print(storage.load(cells,"/work/drawing.kpb")) print(int_vector_get(cells,0)) return 0 end')
        invoke(['/Awl/bin/kcc','run','/work/drawing.aw'],stdout='1\n0\n-3\n0\n0\n')
        payload=(root/'work/drawing.kpb').read_bytes()
        expected=b'KPBOARD1'+b''.join((i*1234567%16777216).to_bytes(3,'big') for i in range(384))
        assert payload==expected+zlib.adler32(expected).to_bytes(4,'big')
    # All integer widths and 64 conversion pairs, oracle generated outside root.
    import sys
    sys.path.insert(0,str(ROOT/'compiler'));import kcc
    lines=[];expected=[]
    for ty in kcc.INTEGERS:
        lo,hi=kcc.bounds(ty)
        for v in sorted({lo,0,1,hi}):
            for op,rhs in [('+',0),('-',0),('*',1),('/',1),('%',1)]:
                lines.append(f'print(({v}{ty}){op}{rhs}{ty})');expected.append(str(0 if op=='%' else v))
    for src in kcc.INTEGERS:
        for dst in kcc.INTEGERS:
            lo=max(kcc.bounds(src)[0],kcc.bounds(dst)[0]);hi=min(kcc.bounds(src)[1],kcc.bounds(dst)[1])
            for v in sorted({lo,0,1,hi}):lines.append(f'print({dst}({v}{src}))');expected.append(str(v))
    assert len(expected)==348
    (root/'work/integers-matrix.aw').write_text('function main()->i64 '+' '.join(lines)+' return 0 end')
    invoke(['/Awl/bin/kcc','run','/work/integers-matrix.aw'],stdout='\n'.join(expected)+'\n')
    for i,expression in enumerate(['127i8+1i8','0u8-1u8','-128i8/-1i8','9223372036854775807+1','i64(18446744073709551615u64)']):
        (root/f'work/trap{i}.aw').write_text('function main()->i64 print('+expression+') return 0 end')
        invoke(['/Awl/bin/kcc','run',f'/work/trap{i}.aw'],code=134,stderr_part='Awl arithmetic trap')
    (root/'work/exit.aw').write_text('function main()->i64 return 37 end')
    invoke(['/Awl/bin/kcc','run','/work/exit.aw'],code=37,stdout='')
    (root/'work/infinite.aw').write_text('function main()->i64 while true do end return 0 end')
    invoke(['/Awl/bin/kcc','run','/work/infinite.aw','--run-timeout','1'],code=124,stderr_part='program wall-time limit exceeded')
    invoke(['/Awl/bin/kcc','build','/work/first.aw','--build-timeout','0'],code=2,stderr_part='invalid option')
    # Frontend rejection and preservation of a previously built artifact.
    before=hashlib.sha256((root/'work/first').read_bytes()).hexdigest()
    (root/'work/bad.aw').write_text('function main()->i64 return true end')
    invoke(['/Awl/bin/kcc','build','/work/bad.aw','-o','/work/first','--diagnostic-format','json'],code=1,stderr_part='E200')
    assert hashlib.sha256((root/'work/first').read_bytes()).hexdigest()==before
    invoke(['/Awl/bin/kcc','build','/work/first.aw','-o','/work/first.aw'],code=2,stderr_part='refusing to overwrite source')
    # Removing shipped resources must fail, never search the OS for replacements.
    lib=root/'Awl/libexec/zig/lib';hidden=lib.with_name('lib.hidden');lib.rename(hidden)
    try:invoke(['/Awl/bin/kcc','build','/work/first.aw','-o','/work/first'],code=2,stderr_part='bundled toolchain missing')
    finally:hidden.rename(lib)
    assert hashlib.sha256((root/'work/first').read_bytes()).hexdigest()==before
    # Relocate the WHOLE prefix into a directory containing a space.
    (root/'Awl').rename(root/'relocated Awl')
    invoke(['/relocated Awl/bin/kcc','run','/work/first.aw'],stdout='42\n')
    headers=subprocess.check_output(['readelf','-l',str(root/'work/first')],text=True)
    assert 'INTERP' not in headers
    report={'status':'passed','harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'test_host_kernel':os.uname().release,'rootfs_initial_directories':['Awl','work','tmp','cache','proc','dev'],
        'host_development_tools_in_rootfs':False,'python_or_shell_in_rootfs':False,'network':'private network namespace, no configured external interfaces',
        'pid_and_mount_namespaces':'private; proc mounted inside root','run_uid':os.getuid(),'cache_initially_empty':True,
        'host_tools_used_for_test_setup_only':['Python','sudo','env','unshare','chroot','mknod','chmod','readelf'],
        'compiler_inside_rootfs':'only Awl bin/kcc and its shipped libexec/zig bundle','integer_matrix_checks':348,'trap_cases':5,'resource_trap_cases':int(any(manifest.get('version','').startswith(v) for v in ['0.8.','0.9.','0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.'])),'string_trap_cases':int(any(manifest.get('version','').startswith(v) for v in ['0.8.2','0.8.3','0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0'])),'builder_trap_cases':int(any(manifest.get('version','').startswith(v) for v in ['0.8.3','0.8.4','0.9.0','0.9.1','0.10.0','0.11.0','0.12.0','0.13.0','0.14.0','0.15.0','0.16.0','0.17.0','0.18.0','0.19.0','0.20.0','0.21.0','0.22.0','0.23.0','0.24.0'])),
        'array_trap_cases':int(manifest.get('version','').startswith(('0.9.','0.10.','0.11.','0.12.','0.13.','0.14.','0.15.','0.16.','0.17.','0.18.','0.19.','0.20.','0.21.','0.22.','0.23.','0.24.'))),'generated_executable_has_ELF_interpreter':False,'manifest':json.loads((root/'relocated Awl/manifest.json').read_text()),'commands':records,
        'scope':'Linux x86-64 on recorded kernel only; not a full VM/distro matrix, sandbox/security proof or production-safety certification.'}
    if args.archive:report['tested_archive']={'path':str(args.archive.resolve()),'sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'bytes':args.archive.stat().st_size}
    if args.overlay:report['tested_overlay']={'path':str(args.overlay.resolve()),'sha256':hashlib.sha256(args.overlay.read_bytes()).hexdigest(),'bytes':args.overlay.stat().st_size}
    (ROOT/(('tests/repeat-overlay-validation.json' if report['manifest'].get('version','').startswith('0.9.1') else 'tests/arrays-overlay-validation.json' if report['manifest'].get('version','').startswith('0.9.') else 'tests/cleanup-overlay-validation.json' if report['manifest'].get('version','').startswith('0.8.4') else 'tests/builders-overlay-validation.json' if report['manifest'].get('version','').startswith('0.8.3') else 'tests/strings-overlay-validation.json' if report['manifest'].get('version','').startswith('0.8.2') else 'tests/modules-overlay-validation.json' if report['manifest'].get('version','').startswith('0.8.1') else 'tests/platform-overlay-validation.json') if args.overlay else 'tests/bundle-archive-validation.json' if args.archive else 'tests/bundle-isolation.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('Awl-only offline isolation PASSED:',len(records),'commands, 348 integer checks, 5 traps, relocation, missing-resource failure')
if __name__=='__main__':main()
