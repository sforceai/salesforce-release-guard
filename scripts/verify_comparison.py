"""Isolated browser checks for the fictional comparison; never connects to an org."""
import argparse
import asyncio
import base64
import json
from pathlib import Path
import socket
import subprocess
import urllib.request
import uuid


async def verify(args):
    import websockets
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([args.browser,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',f'--remote-debugging-port={port}',f'--user-data-dir={out/("browser-"+uuid.uuid4().hex[:8])}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    target=None
    for _ in range(60):
        try:
            targets=json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=1).read())
            target=next((t for t in targets if t['type']=='page'),None)
            if target:break
        except (OSError,ValueError):pass
        await asyncio.sleep(.2)
    if not target:process.terminate();raise RuntimeError('Report browser did not start')
    async with websockets.connect(target['webSocketDebuggerUrl'],max_size=32*1024*1024) as ws:
        seq=0
        async def call(method,params=None):
            nonlocal seq
            seq+=1;identity=seq
            await ws.send(json.dumps({'id':identity,'method':method,'params':params or {}}))
            while True:
                response=json.loads(await ws.recv())
                if response.get('id')==identity:
                    if 'error' in response:raise RuntimeError(response['error'])
                    return response.get('result',{})
        async def js(code):
            r=await call('Runtime.evaluate',{'expression':code,'returnByValue':True})
            if 'exceptionDetails' in r:raise AssertionError(r['exceptionDetails'])
            return r.get('result',{}).get('value')
        async def shot(name):
            data=await call('Page.captureScreenshot',{'format':'png'});(out/name).write_bytes(base64.b64decode(data['data']))
        await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
        await call('Page.navigate',{'url':Path(args.report).resolve().as_uri()})
        for _ in range(50):
            if await js("document.readyState==='complete' && typeof comparisonData!=='undefined'"):break
            await asyncio.sleep(.1)
        assert await js("document.querySelectorAll('#change-rows tr').length")==5
        await shot('comparison-desktop.png')
        await js("document.querySelector('.review-card .change-focus').click()")
        assert await js("document.getElementById('comparison-side').value")== 'before'
        assert await js('impactFocus.value')=='apex:oldexpenseutility'
        await js("document.getElementById('change-filter').value='destructive';document.getElementById('change-filter').dispatchEvent(new Event('change'))")
        assert await js("document.querySelectorAll('#change-rows tr:not([hidden])').length")==1
        await js("document.querySelector('#change-rows tr[data-change=destructive] button').click()")
        await asyncio.sleep(.4)
        assert await js("document.getElementById('comparison-side').value")== 'before'
        assert await js("impactFocus.value")== 'apex:oldexpenseutility'
        assert await js("document.getElementById('impact-connections').textContent.includes('ExistingExpenseCaller')")
        await shot('deletion-before-impact.png')
        await js("document.getElementById('comparison-side').value='after';document.getElementById('comparison-side').dispatchEvent(new Event('change'))")
        assert await js("document.getElementById('impact-svg').children.length")==0
        assert await js("document.getElementById('comparison-selection').textContent.includes('no supported component definition')")
        await js("document.getElementById('change-filter').value='';document.getElementById('change-filter').dispatchEvent(new Event('change'));document.querySelector('#change-rows tr[data-change=new] button').click()")
        assert await js('impactFocus.value')=='apex:expensepolicy'
        await js("document.getElementById('comparison-side').value='before';switchGraph()")
        assert await js("document.getElementById('impact-svg').children.length")==0
        await js("document.querySelector('#change-rows tr[data-change=modified] button').click();document.querySelector('#impact-connections .impact-link').click()")
        assert await js("document.getElementById('impact-evidence').textContent.includes('static reference')")
        await js('window.scrollTo(0,0)')
        await call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        assert not await js('document.documentElement.scrollWidth>390')
        await shot('comparison-mobile.png')
        result={'rows':5,'hero_dependency_action':'passed','classification_filter':'passed','destructive_before_graph':'passed','no_stale_graph_after_deletion':'passed','new_component_missing_before':'passed','connection_evidence':'passed','mobile_overflow':False}
        (out/'comparison-browser-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
        try:await call('Browser.close')
        except Exception:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--output',required=True);parser.add_argument('--browser',default='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    asyncio.run(verify(parser.parse_args()))
