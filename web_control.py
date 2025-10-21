"""Simple web control UI using aiohttp to pause/resume/restart macros and stream logs.

A single-page app that opens a websocket to receive log lines and to send control 
commands (pause/resume/restart).
"""

import asyncio
import threading
import queue
from aiohttp import web, WSMsgType
import pathlib
import json
import argparse
import logging
import traceback

from adapter.joycontrol import JoycontrolAdapter
from macros.parser import parse_macro, MacroRunner

logging.basicConfig(
    level=logging.DEBUG,           # Show DEBUG messages and above
    format='[%(levelname)s] %(name)s: %(message)s'
)

ROOT = pathlib.Path(__file__).parent

INDEX_HTML = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Macro Control</title>
  <style>body{font-family:monospace;} #log{white-space:pre; background:#111; color:#0f0; padding:1rem; height:60vh; overflow:auto}</style>
</head>
<body>
  <h1>Macro Control</h1>
  <button id="pause">Pause</button>
  <button id="resume">Resume</button>
  <button id="restart">Restart</button>
  <div id="status">Status: idle</div>
  <div id="log"></div>
    <hr>
    <div>
        <label for="macro_select">Select macro:</label>
        <select id="macro_select"></select>
        <button id="run_macro">Run</button>
    </div>
    <div>
        <h3>Create / Edit Macro</h3>
        <input id="macro_name" placeholder="filename.txt" />
        <button id="save_macro">Save</button>
        <br>
        <textarea id="macro_editor" style="width:100%;height:200px"></textarea>
    </div>
<script>
let ws = new WebSocket("ws://"+location.host+"/ws");
ws.onopen = ()=>console.log('ws open');
ws.onmessage = (e)=>{
    let m = JSON.parse(e.data);
    if(m.type==='log'){
        document.getElementById('log').textContent += m.msg + '\\n';
        document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
    } else if(m.type==='status'){
        document.getElementById('status').textContent = 'Status: '+m.msg;
    }
};
function send(cmd){ ws.send(JSON.stringify({cmd:cmd})); }
document.getElementById('pause').onclick = ()=>send('pause');
document.getElementById('resume').onclick = ()=>send('resume');
document.getElementById('restart').onclick = ()=>send('restart');
// Macro UI helpers
async function listMacros(){
    let res = await fetch('/api/macros');
    if(!res.ok) return;
    let names = await res.json();
    let sel = document.getElementById('macro_select');
    sel.innerHTML = '';
    names.forEach(n=>{ let o = document.createElement('option'); o.value = n; o.textContent = n; sel.appendChild(o); });
}

document.getElementById('run_macro').onclick = async ()=>{
    let sel = document.getElementById('macro_select');
    let name = sel.value;
    if(!name) return;
    await fetch('/api/select', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({name:name})});
}

document.getElementById('save_macro').onclick = async ()=>{
    let name = document.getElementById('macro_name').value;
    let content = document.getElementById('macro_editor').value;
    if(!name) return alert('Enter filename');
    let res = await fetch('/api/macros', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({name:name, content:content})});
    if(res.ok){
        await listMacros();
        alert('Saved');
    } else {
        alert('Save failed');
    }
}

document.getElementById('macro_select').onchange = async ()=>{
    let name = document.getElementById('macro_select').value;
    if(!name) return;
    let res = await fetch('/api/macros/'+encodeURIComponent(name));
    if(res.ok){
        let text = await res.text();
        document.getElementById('macro_editor').value = text;
        document.getElementById('macro_name').value = name;
    }
}

// populate list on load
listMacros().catch(e=>console.error(e));
</script>
</body>
</html>
'''


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    app = request.app
    cmd_q: 'queue.Queue' = app['cmd_q']
    logs_q: 'queue.Queue' = app['logs_ws_q']

    # send initial status
    await ws.send_str(json.dumps({'type':'status','msg': 'connected'}))

    loop = asyncio.get_event_loop()

    async def log_forwarder():
        # use run_in_executor to blockingly get from the thread-safe queue
        while True:
            msg = await loop.run_in_executor(None, logs_q.get)
            await ws.send_str(json.dumps({'type':'log','msg': msg}))

    forwarder = asyncio.create_task(log_forwarder())

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except Exception:
                data = {'cmd': msg.data}
            cmd = data.get('cmd')
            if cmd in ('pause', 'resume', 'restart', 'stop'):
                cmd_q.put(cmd)
                await ws.send_str(json.dumps({'type':'status','msg': cmd}))
        elif msg.type == WSMsgType.ERROR:
            break

    forwarder.cancel()
    return ws


async def index(request):
    return web.Response(text=INDEX_HTML, content_type='text/html')


async def api_list_macros(request):
    logging.getLogger(__name__).debug('api_list_macros called; ROOT=%s', ROOT)
    macros_dir = ROOT / 'macros'
    if not macros_dir.exists():
        return web.json_response([], status=200)
    names = [p.name for p in macros_dir.iterdir() if p.is_file()]
    return web.json_response(sorted(names))


async def api_get_macro(request):
    name = request.match_info['name']
    from pathlib import Path
    path = ROOT / 'macros' / Path(name).name
    if not path.exists():
        return web.Response(status=404)
    return web.Response(text=path.read_text(), content_type='text/plain')


async def api_save_macro(request):
    data = await request.json()
    name = data.get('name')
    content = data.get('content', '')
    if not name:
        return web.Response(status=400, text='name required')
    from pathlib import Path
    path = ROOT / 'macros' / Path(name).name
    path.write_text(content)
    return web.Response(status=201)


async def api_select_macro(request):
    data = await request.json()
    name = data.get('name')
    if not name:
        return web.Response(status=400, text='name required')
    # send load command to worker via cmd_q
    cmd_q: 'queue.Queue' = request.app['cmd_q']
    cmd_q.put(f'load:{name}')
    return web.Response(status=200)


async def worker_main(macro_file: str, cmd_q: 'queue.Queue', logs_qs: list):
    """Worker coroutine to run in its own asyncio loop (in a thread).

    It creates the adapter and MacroRunner and forwards runner logs into the
    thread-safe logs_q. It also listens to cmd_q for control commands.
    """
    try:
        for q in logs_qs:
            try:
                q.put_nowait('worker: starting')
            except Exception:
                try:
                    q.put('worker: starting')
                except Exception:
                    pass

        text = open(macro_file).read()
        commands = parse_macro(text)
        for q in logs_qs:
            try:
                q.put_nowait(f'worker: parsed {len(commands)} commands')
            except Exception:
                try:
                    q.put(f'worker: parsed {len(commands)} commands')
                except Exception:
                    pass

        for q in logs_qs:
            try:
                q.put_nowait('worker: creating adapter')
            except Exception:
                try:
                    q.put('worker: creating adapter')
                except Exception:
                    pass
        adapter = JoycontrolAdapter()
        for q in logs_qs:
            try:
                q.put_nowait('worker: connecting adapter')
            except Exception:
                try:
                    q.put('worker: connecting adapter')
                except Exception:
                    pass
        await adapter.connect()
        for q in logs_qs:
            try:
                q.put_nowait('worker: adapter connected')
            except Exception:
                try:
                    q.put('worker: adapter connected')
                except Exception:
                    pass

        runner = MacroRunner(adapter)
        runner.set_commands(commands)
        rlogs = runner.logs()

        async def forward_rlogs():
            while True:
                try:
                    msg = await rlogs.get()
                except asyncio.CancelledError:
                    break
                for q in logs_qs:
                    try:
                        q.put_nowait(msg)
                    except Exception:
                        try:
                            q.put(msg)
                        except Exception:
                            pass

        loop = asyncio.get_event_loop()

        async def cmd_handler():
            while True:
                # block in thread executor until a command is available
                cmd = await loop.run_in_executor(None, cmd_q.get)
                for q in logs_qs:
                    try:
                        q.put_nowait(f'worker: got cmd: {cmd}')
                    except Exception:
                        try:
                            q.put(f'worker: got cmd: {cmd}')
                        except Exception:
                            pass
                if cmd == 'pause':
                    runner.pause()
                elif cmd == 'resume':
                    runner.resume()
                elif cmd == 'restart':
                    try:
                        await runner.restart()
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error restarting: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error restarting: {e}')
                                except Exception:
                                    pass
                elif cmd == 'stop':
                    await runner.stop()
                    break
                elif isinstance(cmd, str) and cmd.startswith('load:'):
                    # load:<filename> -> load macro from macros/ and restart runner
                    name = cmd.split(':',1)[1]
                    try:
                        # sanitize and only allow basename
                        from pathlib import Path
                        mpath = Path(ROOT) / 'macros' / Path(name).name
                        text = mpath.read_text()
                        new_commands = parse_macro(text)
                        runner.set_commands(new_commands)
                        await runner.restart()
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Loaded macro: {name} ({len(new_commands)} commands)')
                            except Exception:
                                try:
                                    q.put(f'Loaded macro: {name} ({len(new_commands)} commands)')
                                except Exception:
                                    pass
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error loading macro {name}: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error loading macro {name}: {e}')
                                except Exception:
                                    pass

        await runner.start()
        await asyncio.gather(forward_rlogs(), cmd_handler())
    except Exception as e:
        tb = traceback.format_exc()
        for q in logs_qs:
            try:
                q.put_nowait(f'Worker error: {e}\n{tb}')
            except Exception:
                try:
                    q.put(f'Worker error: {e}\n{tb}')
                except Exception:
                    pass



async def start_server(macro_file: str, host: str='0.0.0.0', port: int=8080):
    # Create thread-safe command and log queues and start worker thread
    cmd_q: 'queue.Queue' = queue.Queue()
    logs_term_q: 'queue.Queue' = queue.Queue()
    logs_ws_q: 'queue.Queue' = queue.Queue()

    # forward logs from the worker logs_q to the terminal
    async def terminal_log_printer():
        loop = asyncio.get_event_loop()
        while True:
            msg = await loop.run_in_executor(None, logs_term_q.get)
            print(msg)

    term_logger = asyncio.create_task(terminal_log_printer())

    # start worker thread with its own asyncio loop
    def _start_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(worker_main(macro_file, cmd_q, [logs_term_q, logs_ws_q]))

    worker = threading.Thread(target=_start_worker, daemon=True)
    worker.start()

    app = web.Application()
    app['cmd_q'] = cmd_q
    app['logs_ws_q'] = logs_ws_q
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/api/macros', api_list_macros)
    app.router.add_get('/api/macros/{name}', api_get_macro)
    app.router.add_post('/api/macros', api_save_macro)
    app.router.add_post('/api/select', api_select_macro)

    # Properly set up AppRunner and TCPSite and keep the server running until
    # cancelled. Use distinct names to avoid shadowing the MacroRunner `runner`.
    app_runner = web.AppRunner(app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=host, port=port)
    await site.start()
    print(f'Web control running on http://{host}:{port}')
    try:
        # wait forever until cancelled (e.g., Ctrl-C)
        await asyncio.Event().wait()
    finally:
        term_logger.cancel()
        # signal worker to stop
        try:
            cmd_q.put('stop')
        except Exception:
            pass
        await app_runner.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('macro_file')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    asyncio.run(start_server(args.macro_file, host=args.host, port=args.port))