"""HTTP and websocket handlers for the web control UI.

Contains aiohttp handlers and embedded single-page HTML.
"""
from __future__ import annotations

import pathlib
import json
import queue
import asyncio
from aiohttp import web, WSMsgType
from typing import Optional

ROOT = pathlib.Path(__file__).parent.parent.parent

INDEX_HTML = None


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    app = request.app
    cmd_q: 'queue.Queue' = app['cmd_q']
    logs_q: 'queue.Queue' = app['logs_ws_q']

    await ws.send_str(json.dumps({'type':'status','msg': 'connected'}))

    loop = asyncio.get_event_loop()

    async def log_forwarder():
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
    # serve the static html file
    path = pathlib.Path(__file__).parent / 'static' / 'index.html'
    return web.Response(text=path.read_text(), content_type='text/html')


async def api_list_macros(request):
    macros_dir = ROOT / 'data' / 'macros'
    if not macros_dir.exists():
        return web.json_response([], status=200)
    names = [p.name for p in macros_dir.iterdir() if p.is_file()]
    return web.json_response(sorted(names))


async def api_get_macro(request):
    name = request.match_info['name']
    from pathlib import Path
    path = ROOT / 'data' / 'macros' / Path(name).name
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
    path = ROOT / 'data' / 'macros' / Path(name).name
    path.write_text(content)
    return web.Response(status=201)


async def api_select_macro(request):
    data = await request.json()
    name = data.get('name')
    if not name:
        return web.Response(status=400, text='name required')
    cmd_q: 'queue.Queue' = request.app['cmd_q']
    cmd_q.put(f'load:{name}')
    return web.Response(status=200)


async def api_stop(request):
    cmd_q: 'queue.Queue' = request.app['cmd_q']
    try:
        cmd_q.put('stop')
    except Exception:
        pass
    ev: Optional[asyncio.Event] = request.app.get('shutdown_event')
    if ev is not None:
        ev.set()
    return web.Response(status=200)


async def api_restart_host(request):
    import subprocess
    try:
        subprocess.Popen(['sudo', 'shutdown', '-r', 'now'])
    except Exception as e:
        return web.Response(status=500, text=str(e))
    return web.Response(status=200)


async def api_stop_host(request):
    import subprocess
    try:
        subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
    except Exception as e:
        return web.Response(status=500, text=str(e))
    return web.Response(status=200)


async def api_list_adapters(request):
    """List available adapter types."""
    try:
        from adapter.factory import get_available_adapters
        adapters = get_available_adapters()
        return web.json_response(adapters)
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def api_adapter_status(request):
    """Get current adapter preference and test connectivity."""
    try:
        from adapter.factory import test_adapter_connectivity
        
        adapter_config = request.app.get('adapter_config', {})
        preferred = adapter_config.get('preferred')
        connectivity = await test_adapter_connectivity()
        
        return web.json_response({
            'preferred': preferred,
            'connectivity': connectivity
        })
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def api_select_adapter(request):
    """Set the preferred adapter type."""
    try:
        data = await request.json()
        adapter_type = data.get('adapter')
        
        if adapter_type not in [None, 'pico', 'joycontrol']:
            return web.Response(status=400, text='Invalid adapter type')
        
        # Update the app's preferred adapter
        adapter_config = request.app.get('adapter_config', {})
        adapter_config['preferred'] = adapter_type
        
        # Send command to worker to notify about adapter change
        cmd_q: 'queue.Queue' = request.app['cmd_q']
        cmd_q.put(f'adapter:{adapter_type}')
        
        return web.json_response({
            'preferred': adapter_type,
            'message': 'Adapter preference updated. Restart the system to take effect.'
        })
    except Exception as e:
        return web.Response(status=500, text=str(e))
