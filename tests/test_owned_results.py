"""Explicit single-owner builder results; no implicit ownership adoption."""
import os,shutil,subprocess,unittest,json
from pathlib import Path
from native_features import supports_version
from test_builders import Builders,ROOT
KCC=Path(os.environ.get('Awl_OWNED_RESULTS_TEST_BINARY',str(ROOT/'build/Awl-linux-x86_64/bin/kcc')))
@unittest.skipUnless(supports_version(KCC,(0,14,0)),'requires native0.14 owned results')
class OwnedResults(Builders):
    def invoke(self,command,*args):return subprocess.run([str(KCC),command,str(self.root/'main.aw'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=120)
    def reject_result(self,s,code='E223'):
        self.source(s,True);r=self.invoke('check','--diagnostic-format','json');self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(json.loads(r.stderr)['diagnostics'][0]['code'],code,r.stderr)
    def test_pipeline_o0_o3(self):
        shutil.copytree(ROOT/'examples/owned-results',self.root,dirs_exist_ok=True)
        for opt in ['0','3']:self.output('frame=99999 / returned\n100000 factory -> transform -> caller pipelines\n2188890\n',opt)
    def test_terminal_outer_owner_return_in_branches_and_loop(self):
        self.source('function make(n:i64)->own spool scoped b:spool=spool_new(8) spool_i64(b,n) if n==0 then return move b end while n==1 do return move b end return move b end function main()->i64 local i:i64=0 while i<3 do scoped b:spool=make(i) spool_print(b) i=i+1 end return 0 end',True);self.output('0\n1\n2\n')
    def test_unavailable_and_zero_capacity(self):
        self.source('function make(n:i64)->own spool scoped b:spool=spool_new(n) return move b end function main()->i64 scoped a:spool=make(-1) scoped b:spool=make(0) print(spool_valid(a)) print(spool_valid(b)) return 0 end',True);self.output('false\ntrue\n')
    def test_no_discard_manual_adoption_argument_or_borrow_escape(self):
        h='function make()->own spool scoped b:spool=spool_new(8) return move b end function take(borrow b:spool)->unit end function main()->i64 '
        for body in ['make()','local b:spool=make()','take(make())','spool_print(make())']:
            self.reject_result(h+body+' return 0 end')
    def test_owned_return_requires_real_owner(self):
        for setup,val in [('local b:spool=spool_new(8)','move b'),('scoped b:spool=spool_new(8)','b'),('','spool_new(8)')]:
            self.reject_result('function bad()->own spool '+setup+' return '+val+' end function main()->i64 return 0 end')
        self.reject_result('function bad(borrow b:spool)->own spool return move b end function main()->i64 return 0 end')
    def test_owned_call_not_ordinary_return(self):
        self.reject_result('function make()->own spool scoped b:spool=spool_new(8) return move b end function bad()->spool return make() end function main()->i64 return 0 end')
    def test_owned_result_type_policy(self):
        for ty in ['i64','bool','string','[spool;1]']:
            self.reject_result('function bad()->own '+ty+' return 0 end function main()->i64 return 0 end')
    def test_transform_source_is_consumed(self):
        self.reject_result('function transform(own b:spool)->own spool return move b end function main()->i64 scoped a:spool=spool_new(8) scoped b:spool=transform(move a) spool_print(a) return 0 end','E221')
    def test_release_once_after_return_not_in_factory(self):
        self.source('function make()->own spool scoped b:spool=spool_new(8) spool_append(b,"alive") return move b end function transform(own b:spool)->own spool return move b end function main()->i64 scoped a:spool=make() scoped b:spool=transform(move a) spool_print(b) return 0 end',True)
        r=self.invoke('emit-c');self.assertEqual(r.returncode,0,r.stderr);c=self.root/'trace.c';c.write_text(r.stdout.replace('static void k_spool_free(KSpool b) {','static void k_spool_free(KSpool b) { fprintf(stderr,"release=%" PRIu64 "\\n",b.id);',1));exe=self.root/'trace';flags=['-std=c11','-O2']
        if os.environ.get('Awl_BUILDER_SANITIZE')=='1':flags+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        subprocess.run([shutil.which('cc'),*flags,str(c),'-o',str(exe)],capture_output=True,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'alive\n','release=1\n'))
for name in Builders.__dict__:
    if name.startswith('test_') and name not in OwnedResults.__dict__:setattr(OwnedResults,name,None)
del Builders
if __name__=='__main__':unittest.main()
