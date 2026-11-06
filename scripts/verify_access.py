"""Isolated browser checks for fictional access reports; no org connection."""
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
    try:
        target=None
        for _ in range(60):
            try:
                targets=json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=1).read())
                target=next((t for t in targets if t['type']=='page'),None)
                if target:break
            except (OSError,ValueError):pass
            await asyncio.sleep(.2)
        if not target:raise RuntimeError('Report browser did not start')
        async with websockets.connect(target['webSocketDebuggerUrl'],max_size=8*1024*1024) as ws:
            seq=0
            async def call(method,params=None):
                nonlocal seq
                seq+=1;key=seq;await ws.send(json.dumps({'id':key,'method':method,'params':params or {}}))
                while True:
                    response=json.loads(await ws.recv())
                    if response.get('id')==key:
                        if 'error' in response:raise RuntimeError(response['error'])
                        return response.get('result',{})
            async def js(expression):return (await call('Runtime.evaluate',{'expression':expression,'returnByValue':True}))['result'].get('value')
            await call('Page.enable');await call('Page.navigate',{'url':Path(args.report).resolve().as_uri()})
            for _ in range(50):
                if await js("document.querySelectorAll('tbody tr').length===11"):break
                await asyncio.sleep(.1)
            assert await js("document.querySelectorAll('td.allowed').length===3")
            assert await js("document.querySelectorAll('td.denied').length===8")
            assert await js("document.body.textContent.includes('Record access and effective execution authorization are not assessed')")
            contrast=await js("(()=>{const e=document.querySelector('main>section'),s=getComputedStyle(e),rgb=x=>x.match(/\\d+/g).slice(0,3).map(Number),l=x=>rgb(x).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0),a=l(s.color),b=l(s.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)})()")
            assert contrast>=4.5,contrast
            for width,name in [(1280,'access-desktop.png'),(390,'access-mobile.png')]:
                await call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<500})
                assert not await js('document.documentElement.scrollWidth>'+str(width))
                shot=await call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})
                (out/name).write_bytes(base64.b64decode(shot['data']))
            result={'fictional_rows':11,'allowed':3,'denied':8,'limitations_visible':True,'panel_text_contrast':round(contrast,2),'desktop_mobile_overflow':False}
            (out/'access-browser-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
            try:await call('Browser.close')
            except Exception:pass
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--output',required=True);parser.add_argument('--browser',default='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    asyncio.run(verify(parser.parse_args()))
