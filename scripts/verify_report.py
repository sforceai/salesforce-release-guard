"""Visual/browser QA for our local report only. Requires websockets and installed Edge.

Uses an isolated headless browser profile, never the user's browsing session.
"""
import argparse
import asyncio
import base64
import json
import html
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import uuid


async def verify(args):
    import websockets
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    profile = output / ('browser-' + uuid.uuid4().hex[:8])
    process = subprocess.Popen([args.browser, '--headless', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--disable-background-networking', f'--remote-debugging-port={port}',
        f'--user-data-dir={profile}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    browser_url = f'http://127.0.0.1:{port}'
    target = None
    for _ in range(60):
        try:
            targets = json.loads(urllib.request.urlopen(browser_url + '/json', timeout=1).read())
            target = next((t for t in targets if t['type'] == 'page'), None)
            if target: break
        except (OSError, ValueError):
            pass
        await asyncio.sleep(0.2)
    if not target:
        process.terminate()
        raise RuntimeError('Isolated report browser did not start')
    async with websockets.connect(target['webSocketDebuggerUrl'], max_size=32 * 1024 * 1024) as ws:
        sequence = 0
        async def call(method, params=None):
            nonlocal sequence
            sequence += 1
            identity = sequence
            await ws.send(json.dumps({'id': identity, 'method': method, 'params': params or {}}))
            while True:
                response = json.loads(await ws.recv())
                if response.get('id') == identity:
                    if 'error' in response: raise RuntimeError(response['error'])
                    return response.get('result', {})
        async def js(expression):
            result = await call('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
            if 'exceptionDetails' in result: raise AssertionError(result['exceptionDetails'])
            return result.get('result', {}).get('value')
        await call('Page.enable')
        await call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False})
        await call('Page.navigate', {'url': Path(args.report).resolve().as_uri()})
        for _ in range(50):
            if await js("document.readyState==='complete' && !!document.getElementById('findings')"):
                break
            await asyncio.sleep(0.1)
        expected = await js("document.querySelectorAll('.finding').length")
        assert expected > 0, 'No findings rendered'
        impact_checks=None
        if await js("!!document.getElementById('impact-data')"):
            assert await js("document.getElementById('impact-svg').querySelectorAll('g[role=button]').length")>0
            initial=await js("document.querySelectorAll('#impact-connections tr').length")
            assert initial>0
            await js("document.getElementById('impact-direction').value='upstream';document.getElementById('impact-direction').dispatchEvent(new Event('change'))")
            upstream=await js("document.getElementById('impact-connections').textContent")
            assert 'imports apex' in upstream
            await js("document.getElementById('impact-direction').value='downstream';document.getElementById('impact-depth').value='4';showImpact()")
            downstream=await js("document.getElementById('impact-connections').textContent")
            assert 'writes' in downstream and 'may activate' in downstream
            await js("document.querySelector('#impact-connections button').click()")
            assert await js("document.getElementById('impact-evidence').textContent.includes('static reference')")
            await js("document.getElementById('impact-focus').value='flow:expensenotice';showImpact()")
            flow=await js("document.getElementById('impact-connections').textContent")
            assert 'invokes apex' in flow and 'fault' in flow and 'enqueues' in flow
            await js("document.getElementById('impact-heading').scrollIntoView({block:'start'})")
            shot=await call('Page.captureScreenshot',{'format':'png'})
            (output/'impact-desktop.png').write_bytes(base64.b64decode(shot['data']))
            await js("document.querySelector('.inspect-impact').click()")
            await asyncio.sleep(0.4)
            assert await js("document.getElementById('impact-focus').value.startsWith('method:')")
            impact_checks={'upstream_import':'passed','downstream_activation':'passed','connection_evidence':'passed','scheduled_invocable_fault_async':'passed','finding_navigation':'passed'}
            await js("impactFocus.value=impactGraph.nodes.find(n=>n.kind==='apex_method'&&n.entry_points?.includes('AuraEnabled')).id;impactDirection.value='both';impactDepth.value='2';showImpact();window.scrollTo(0,0)")
        screenshot = await call('Page.captureScreenshot', {'format': 'png'})
        (output / 'report-desktop.png').write_bytes(base64.b64decode(screenshot['data']))
        async def scene(name):
            result = await call('Page.captureScreenshot', {'format': 'png'})
            (output / name).write_bytes(base64.b64decode(result['data']))
        await scene('scene0.png')
        await js("document.getElementById('severity').value='high'; document.getElementById('severity').dispatchEvent(new Event('change'))")
        filter_result = await js("({visible:document.querySelectorAll('.finding:not([hidden])').length,wrong:[...document.querySelectorAll('.finding:not([hidden])')].some(x=>x.dataset.severity!=='high')})")
        assert filter_result['visible'] > 0 and not filter_result['wrong'], filter_result
        await scene('scene1.png')
        await js("document.getElementById('search').value='no-match-6e78'; document.getElementById('search').dispatchEvent(new Event('input'))")
        assert await js("document.querySelectorAll('.finding:not([hidden])').length") == 0
        assert await js("getComputedStyle(document.getElementById('empty')).display!=='none'")
        await js("document.getElementById('search').value='';document.getElementById('severity').value='';filter()")
        if impact_checks:
            await js("impactFocus.value='apex:expensecontroller';impactDirection.value='both';impactDepth.value='3';showImpact();document.getElementById('impact-heading').scrollIntoView({block:'start'})")
            await scene('scene2.png')
            await js("impactFocus.value='flow:expensenotice';impactDirection.value='downstream';impactDepth.value='4';showImpact()")
            await scene('scene3.png')
        else:
            await js("document.getElementById('category').value='A01:2025';filter();document.querySelector('.finding:not([hidden]) details').open=true;document.querySelector('.finding:not([hidden])').scrollIntoView({block:'start'})")
            await scene('scene2.png')
            await js("[...document.querySelectorAll('h2')].find(x=>x.textContent.includes('OWASP')).scrollIntoView({block:'start'})")
            await scene('scene3.png')
        await js("[...document.querySelectorAll('h2')].find(x=>x.textContent.includes('External')).scrollIntoView({block:'start'})")
        await scene('scene4.png')
        await js("document.getElementById('category').value='';filter();window.scrollTo(0,0)")
        await call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        screenshot = await call('Page.captureScreenshot', {'format': 'png'})
        (output / 'report-mobile.png').write_bytes(base64.b64decode(screenshot['data']))
        overflow = await js('document.documentElement.scrollWidth > 390')
        assert not overflow, 'Mobile page overflow'
        receipt = {'browser': 'isolated headless Microsoft Edge', 'findings_rendered': expected,
                   'impact_explorer':impact_checks,
                   'severity_filter': filter_result, 'empty_search_state': 'passed', 'mobile_overflow': overflow,
                   'screenshots': ['report-desktop.png', 'report-mobile.png']}
        (output / 'browser-verification.json').write_text(json.dumps(receipt, indent=2))
        if args.runtime_receipt:
            runtime = json.loads(Path(args.runtime_receipt).read_text(encoding='utf-8'))
            rows = ''.join('<tr><td>' + html.escape(r['tool']) + '</td><td>' + ('BLOCKED' if r['blocked'] else 'ALLOWED') + '</td></tr>' for r in runtime['runtime_calls'])
            probe = runtime['host_dispatch_probe']
            evidence = output / 'runtime-evidence.html'
            evidence.write_text('''<!doctype html><html><meta charset="utf-8"><style>body{background:#0b1120;color:#edf4ff;font:22px/1.7 system-ui;margin:70px 100px}h1{font-size:50px;line-height:1.2}small{color:#6ee7c1;letter-spacing:2px}table{width:100%;border-collapse:collapse}td{padding:16px;border-bottom:1px solid #28354b}td:last-child{color:#6ee7c1}p{color:#a4b3c8}pre{white-space:pre-wrap;background:#131d30;padding:22px;border-radius:12px;font:16px/1.7 monospace}</style><small>SALESFORCE GUARD · RECORDED HERMES RUNTIME CHECK</small><h1>A tool boundary.<br>Beyond a prompt.</h1><p>Captured from actual Hermes 0.21.2 registration and dispatch checks. No live Salesforce action was executed.</p><table>''' + rows + '</table><pre>' + html.escape(probe['result']) + '</pre></html>', encoding='utf-8')
            await call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False})
            await call('Page.navigate', {'url': evidence.as_uri()})
            await asyncio.sleep(0.4)
            await scene('scene5.png')
        print(json.dumps(receipt, indent=2))
        try: await call('Browser.close')
        except Exception: pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--browser', default='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    parser.add_argument('--runtime-receipt')
    args = parser.parse_args()
    asyncio.run(verify(args))


if __name__ == '__main__': main()
