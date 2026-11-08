#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('report',type=Path);ap.add_argument('--chromium',default='/usr/bin/chromium');ap.add_argument('--photo',type=Path,required=True);ap.add_argument('--uncertain-executable',type=Path);a=ap.parse_args();records=[]
 def check(name,condition=True):assert condition,name;records.append(name)
 with tempfile.TemporaryDirectory(prefix='Awl-board-browser-',dir='/var/tmp') as td, sync_playwright() as pw:
  folder=Path(td);process=None
  def start():
   nonlocal process
   process=subprocess.Popen([str(a.executable.resolve()),td],stdout=subprocess.PIPE,stderr=subprocess.PIPE);return int(process.stdout.readline())
  def stop():
   if process.poll() is None:process.terminate()
   out,err=process.communicate(timeout=5);assert not out and not err,(out,err)
  port=start();browser=pw.chromium.launch(executable_path=a.chromium,headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1360,'height':980},device_scale_factor=1,accept_downloads=True);page=context.new_page();errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  def ready(p=page):expect(p.locator('#new')).to_be_enabled(timeout=10000)
  def create(title,note,status='todo'):
   page.locator('#new').click();page.locator('#title').fill(title);page.locator('#note').fill(note);page.locator('#status').select_option(status);page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible();ready()
  try:
   page.goto(f'http://127.0.0.1:{port}');ready();check('real native origin and worker initialization',page.locator('#summary').inner_text()=='0 of 0 tasks · 0 done')
   create('Make the next step clear','Choose a small piece of work that makes a real difference')
   create('Gather the useful details','Keep the context close, not scattered across tabs')
   create('Build something that lasts','Native Awl writes a checked snapshot before acknowledging an edit','doing')
   create('Leave a little room to explore','Search runs in Awl-compiled WebAssembly, right here in the browser','doing')
   create('Keep the owl looking sharp','The original owl, on a rounded pure-black tile','done')
   create('Bring yesterday’s work along','Your board survives a server restart, no cloud required','done')
   expect(page.locator('.card')).to_have_count(6);check('create six persistent tasks through UI')
   page.locator('#search').fill('WEBASSEMBLY');expect(page.locator('.card')).to_have_count(1);check('ASCII-folded search is actually Awl WASM',page.evaluate('AwlBoard.lastFilter.code')==0 and page.evaluate('AwlBoard.lastFilter.ids')==[4])
   page.locator('#search').fill('');page.locator('#filter').select_option('done');expect(page.locator('.card')).to_have_count(2);check('status filtering');page.locator('#filter').select_option('all');expect(page.locator('.card')).to_have_count(6);ready()
   page.locator('.card[data-id="1"] .edit').click();page.locator('#title').fill('Make the next step clear 🦉');page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible();ready();check('edit Unicode title',page.locator('.card[data-id="1"] h3').inner_text().endswith('🦉'))
   page.locator('.card[data-id="2"] .move').select_option('doing');ready();expect(page.locator('.column[data-status="doing"] .card')).to_have_count(3);check('move task between columns')
   with page.expect_download() as dl:page.locator('#export').click()
   download=dl.value;check('download is exactly the current persistent snapshot',Path(download.path()).read_bytes()==(folder/'board.json').read_bytes())
   # A second independent browser context supplies an actual stale-write race
   other_context=browser.new_context();other=other_context.new_page();other.goto(f'http://127.0.0.1:{port}');ready(other)
   page.locator('.card[data-id="1"] .edit').click();page.locator('#note').fill('my draft must survive a conflict')
   other.locator('.card[data-id="1"] .edit').click();other.locator('#note').fill('saved from the other tab');other.locator('#save').click();expect(other.locator('#editor')).not_to_be_visible();ready(other)
   page.locator('#save').click();expect(page.locator('#form-error')).to_contain_text('another tab');check('stale tab preserves its draft',page.locator('#note').input_value()=='my draft must survive a conflict');check('stale tab cannot overwrite saved data',json.loads((folder/'board.json').read_bytes())['tasks'][0]['note']=='saved from the other tab');page.locator('#cancel').click();page.evaluate('AwlBoard.refresh()');ready();other_context.close()
   # Real filesystem refusal, not a mocked response
   (folder/'.board.tmp').mkdir();page.locator('.card[data-id="1"] .edit').click();page.locator('#note').fill('a retryable draft');page.locator('#save').click();expect(page.locator('#form-error')).to_contain_text('nothing was published');check('storage failure keeps editor and draft',page.locator('#note').input_value()=='a retryable draft');(folder/'.board.tmp').rmdir();page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible();ready();check('retry after repairing actual storage')
   # Drop a response only after the real native mutation has committed
   def lose_response(route):route.fetch();route.abort()
   page.route('**/api/tasks/1',lose_response,times=1);page.locator('.card[data-id="1"] .edit').click();page.locator('#note').fill('committed despite a lost response');page.locator('#save').click();expect(page.locator('#form-error')).to_contain_text('result is unknown');check('lost acknowledgement retains draft and admits uncertainty',json.loads((folder/'board.json').read_bytes())['tasks'][0]['note']=='committed despite a lost response');page.locator('#cancel').click();page.evaluate('AwlBoard.refresh()');ready();check('refresh reconciles lost acknowledgement without duplicate',page.evaluate('AwlBoard.state.tasks.length')==6)
   create('literal markup <script>not code</script>','<img src=x onerror=alert(1)>');check('untrusted text is not HTML',page.locator('.card img,.card script').count()==0 and '<script>' in page.locator('.card[data-id="7"] h3').inner_text());page.locator('.card[data-id="7"] .edit').click();page.once('dialog',lambda d:d.accept());page.locator('#delete').click();expect(page.locator('#editor')).not_to_be_visible();ready();expect(page.locator('.card')).to_have_count(6);check('delete task through UI')
   stop();port=start();page.goto(f'http://127.0.0.1:{port}');ready();expect(page.locator('.card')).to_have_count(6);check('UI survives a real native process restart',page.evaluate('AwlBoard.state.tasks[0].note')=='committed despite a lost response')
   # keyboard-only dialog entry and cancellation, then UTF-8 length validation
   page.locator('#new').focus();page.keyboard.press('Enter');expect(page.locator('#title')).to_be_focused();page.locator('#title').fill('🦉'*41);page.locator('#save').click();expect(page.locator('#form-error')).to_contain_text('UTF-8 byte');page.keyboard.press('Escape');expect(page.locator('#editor')).not_to_be_visible();check('keyboard dialog and UTF-8 length feedback')
   page.set_viewport_size({'width':390,'height':844});check('mobile has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'));expect(page.locator('#new')).to_be_visible();page.set_viewport_size({'width':1360,'height':980})
   page.locator('#search').fill('no such task');expect(page.locator('.card')).to_have_count(0);check('empty filter result');page.locator('#search').fill('');expect(page.locator('.card')).to_have_count(6);ready()
   page.locator('.card[data-id="1"] .edit').click();page.locator('#title').fill('Make the next step clear');page.locator('#note').fill('Turn a clear idea into one small, useful action');page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible();ready();page.locator('h1').click();a.photo.parent.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(a.photo),full_page=True);check('genuine Chromium application capture')
   if a.uncertain_executable:
    stop();process=subprocess.Popen([str(a.uncertain_executable.resolve()),td,'0','256'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'BOARD_FAULT':'dir-sync','ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'});port=int(process.stdout.readline());page.goto(f'http://127.0.0.1:{port}');ready();page.locator('.card[data-id="1"] .edit').click();page.locator('#note').fill('published with uncertain durability');page.locator('#save').click();expect(page.locator('#editor')).not_to_be_visible();expect(page.locator('#message')).to_contain_text('durability is uncertain');expect(page.locator('#new')).to_be_disabled();out,err=process.communicate(timeout=5);check('real postpublication uncertainty disables edits and preserves published state',process.returncode==6 and not out and not err and json.loads((folder/'board.json').read_bytes())['tasks'][0]['note']=='published with uncertain durability')
   check('no page script errors',not errors);check('no external resources',all(u.startswith(('http://127.0.0.1:','blob:http://127.0.0.1:')) for u in requests))
   report={'status':'PASS','cases':len(records),'records':records,'browser':browser.version,'executable_sha256':hashlib.sha256(a.executable.read_bytes()).hexdigest(),'photo_sha256':hashlib.sha256(a.photo.read_bytes()).hexdigest(),'qualification':'real headless Chromium on Linux with actual native Awl service and CSP enabled, no unsafe-eval/CSP bypass, no simulated screenshot, JS DOM glue and contributor WASM build remain'};a.report.write_text(json.dumps(report,separators=(',',':'))+'\n');print('PASS',len(records),'real browser checks')
  finally:browser.close();stop()
if __name__=='__main__':main()
