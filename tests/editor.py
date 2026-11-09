#!/usr/bin/env python3
import argparse,hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--playwright',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.playwright));from playwright.sync_api import sync_playwright
 html=ROOT/'editor/Awl-studio.html';requests=[];records=[]
 with tempfile.TemporaryDirectory(prefix='Awl-editor-',dir='/var/tmp') as td,sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage']);context=browser.new_context(viewport={'width':1440,'height':960},offline=True,accept_downloads=True);page=context.new_page();page.on('request',lambda r:requests.append(r.url));page.goto(html.as_uri());assert page.title().startswith('Awl Studio') and page.locator('.logo').inner_text()=='A';assert page.locator('#files button.file').count()==69;records+=['Awl title/logo','69 editable source files']
  for path in page.locator('#entry option').evaluate_all('(xs)=>xs.map(x=>x.value)'):assert path.endswith('.aw')
  records.append('all source discovery uses .aw')
  def choose(path):page.locator('#files button.file[title="'+path+'"]').click()
  def run():page.locator('#run').click();page.wait_for_function('!document.getElementById("run").disabled',timeout=30000);return page.locator('#output').inner_text()
  choose('examples/exports/main.aw');out=run();assert out.startswith('readonly variable\n1.0.0\n') and 'Error' not in out,out;records.append('multi-file .aw imports and exports')
  choose('examples/numeric/main.aw');out=run();assert out.startswith('128.59\n128.59\n1\n1\n9\n') and 'Error' not in out,out;records.append('f64 helpers, compatible literals and math')
  choose('examples/collections/main.aw');out=run();assert 'Expected' in out and 'error' in page.locator('#output').get_attribute('class'),out;records.append('unsupported native collections fail explicitly')
  choose('examples/numeric/main.aw')
  with page.expect_download() as download:page.locator('#download').click()
  assert download.value.suggested_filename=='main.aw';download.value.save_as(str(Path(td)/'main.aw'));assert (Path(td)/'main.aw').read_text()==(ROOT/'examples/numeric/main.aw').read_text();records.append('real source download uses .aw')
  choose('examples/numeric/donut.aw');page.locator('#run').click();page.wait_for_function('document.querySelector("#viewport canvas") && !document.getElementById("stats").textContent.startsWith("Executing")',timeout=30000);assert page.locator('#viewport canvas').count()==1;records.append('actual source-computed donut canvas')
  page.wait_for_function('parseInt(document.getElementById("stats").textContent.split(" · ")[1])>=15',timeout=30000)
  screenshot=ROOT/'editor/Awl-studio.png';page.screenshot(path=str(screenshot));page.locator('#stop').click();assert page.locator('#status').inner_text()=='Stopped';records.append('worker stop terminates execution')
  assert not [u for u in requests if not u.startswith(('file:','blob:','data:'))],requests
  result={'status':'PASS','html_sha256':sha(html),'runtime_sha256':sha(ROOT/'editor/runtime.js'),'harness_sha256':sha(Path(__file__)),'source_files':69,'records':records,'image_sha256':sha(screenshot),'capture':'actual offline Chromium screenshot of running Awl source, no generated or drawn terminal content','browser':browser.version,'external_requests':[],'qualification':'limited browser JavaScript subset, not native compiler/type/ownership/64-bit equivalence'};a.report.write_text(json.dumps(result,separators=(',',':'))+'\n');browser.close();print('PASS',len(records),'offline editor checks')
if __name__=='__main__':main()
