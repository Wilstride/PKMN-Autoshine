"""Simple web control UI using aiohttp to pause/resume/restart macros and stream logs.

A single-page app that opens a websocket to receive log lines and to send control 
commands (pause/resume/restart).
"""

import asyncio
from aiohttp import web, WSMsgType
import pathlib
import json
import argparse

from adapter.joycontrol import JoycontrolAdapter
from macros.parser import parse_macro, MacroRunner

ROOT = pathlib.Path(__file__).parents[1]

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
<script>
let ws = new WebSocket("ws://"+location.host+"/ws");
ws.onopen = ()=>console.log('ws open');
ws.onmessage = (e)=>{
  let m = JSON.parse(e.data);
  if(m.type==='log'){
    document.getElementById('log').textContent += m.msg + '\n';
    document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
  } else if(m.type==='status'){
    document.getElementById('status').textContent = 'Status: '+m.msg;
  }
};
function send(cmd){ ws.send(JSON.stringify({cmd:cmd})); }
document.getElementById('pause').onclick = ()=>send('pause');
document.getElementById('resume').onclick = ()=>send('resume');
document.getElementById('restart').onclick = ()=>send('restart');
</script>
</body>
</html>
'''


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    app = request.app
    runner: MacroRunner = app['runner']

    # send initial status
    await ws.send_str(json.dumps({'type':'status','msg': 'running' if runner.is_running() else 'idle'}))

    async def log_forwarder():
        q = runner.logs()
        while True:
            msg = await q.get()
            await ws.send_str(json.dumps({'type':'log','msg': msg}))

    forwarder = asyncio.create_task(log_forwarder())

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except Exception:
                data = {'cmd': msg.data}
            cmd = data.get('cmd')
            if cmd == 'pause':
                runner.pause()
                await ws.send_str(json.dumps({'type':'status','msg':'paused'}))
            elif cmd == 'resume':
                runner.resume()
                await ws.send_str(json.dumps({'type':'status','msg':'running'}))
            elif cmd == 'restart':
                await runner.restart()
                await ws.send_str(json.dumps({'type':'status','msg':'running'}))
        elif msg.type == WSMsgType.ERROR:
            break

    forwarder.cancel()
    return ws


async def index(request):
    return web.Response(text=INDEX_HTML, content_type='text/html')


async def start_server(macro_file: str, host: str='0.0.0.0', port: int=8080):
    adapter = JoycontrolAdapter()
    await adapter.connect()

    text = open(macro_file).read()
    commands = parse_macro(text)

    runner = MacroRunner(adapter)
    runner.set_commands(commands)
    runner.logs()  # create log queue
    await runner.start()

    # forward logs to terminal as well as websocket
    async def terminal_log_printer():
        q = runner.logs()
        while True:
            msg = await q.get()
            print(msg)

    term_logger = asyncio.create_task(terminal_log_printer())

    app = web.Application()
    app['runner'] = runner
    app.router.add_get('/', index)
    app.router.add_get('/ws', websocket_handler)

    runner_site = web.TCPSite(web.AppRunner(app), host=host, port=port)
    try:
        await web._run_app(app, host=host, port=port)
    finally:
        term_logger.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('macro_file')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    asyncio.run(start_server(args.macro_file, host=args.host, port=args.port))
*** End Patch