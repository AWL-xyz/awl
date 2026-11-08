#!/usr/bin/env python3
import hashlib,http.client,json,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
archive=Path(sys.argv[1]).resolve();report=Path(sys.argv[2]);records=[]
with tempfile.TemporaryDirectory(prefix='Awl-board-package-check-',dir='/var/tmp') as td:
 td=Path(td)
 with tarfile.open(archive) as t:t.extractall(td,filter='data')
 app=td/'Awl-board';inventory=json.loads((app/'inventory.json').read_text())
 for name,item in inventory.items():
  p=app/name;assert p.is_file() and p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
 records.append('exact archive per-file inventory and executable bit verified');assert os.access(app/'awl-board',os.X_OK)
 r=subprocess.run(['readelf','-l',str(app/'awl-board')],check=True,capture_output=True,text=True);assert 'INTERP' not in r.stdout;records.append('static executable has no dynamic interpreter')
 root=td/'empty-root';root.mkdir();(root/'data').mkdir();shutil.copy2(app/'awl-board',root/'awl-board');os.chmod(td,0o755);os.chmod(root,0o755);os.chmod(root/'data',0o777)
 for epoch in range(2):
  p=subprocess.Popen(['sudo','-n','chroot','--userspec=65534:65534',str(root),'/awl-board','/data','0','2'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:
   line=p.stdout.readline();assert line.strip().isdigit(),(line,p.communicate());port=int(line)
   c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('GET','/api/tasks');r=c.getresponse();data=json.loads(r.read());tag=r.getheader('ETag');c.close();assert r.status==200 and data['revision']==epoch and len(data['tasks'])==epoch
   c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('PUT' if epoch==0 else 'DELETE','/api/tasks/1',json.dumps({'title':'standalone','note':'no host tooling','status':'todo'}) if epoch==0 else None,headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{port}','If-Match':tag});r=c.getresponse();data=json.loads(r.read());c.close();assert r.status==(201 if epoch==0 else 200) and data['revision']==epoch+1
   out,err=p.communicate(timeout=5);assert p.returncode==0 and not out and not err;records.append('unprivileged empty-root standalone '+('create' if epoch==0 else 'restart/delete'))
  finally:
   if p.poll() is None:p.kill();p.communicate()
 # remove only files created inside this owned acceptance root
 subprocess.run(['sudo','-n','rm','-f',str(root/'data/board.json'),str(root/'data/.board.tmp')],check=True)
result={'status':'PASS','cases':len(records),'records':records,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'executable_sha256':inventory['awl-board']['sha256'],'qualification':'exact standalone Linux application archive, executable runs as uid65534 in empty chroot with no shell/Python/Node/compiler/SDK/libraries, local host sockets only, not a new SDK or native Windows acceptance'};report.write_text(json.dumps(result,separators=(',',':'))+'\n');print('PASS',len(records),'exact application archive checks')
