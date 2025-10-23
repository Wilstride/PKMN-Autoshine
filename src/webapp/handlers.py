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
    log_buffer = app['log_buffer']
    websocket_connections = app['websocket_connections']

    # Add this connection to the broadcast list
    websocket_connections.add(ws)

    await ws.send_str(json.dumps({'type':'status','msg': 'connected'}))

    # Send recent logs from buffer to new connection
    with log_buffer['lock']:
        for buffered_log in log_buffer['logs']:
            try:
                if isinstance(buffered_log, dict):
                    await ws.send_str(json.dumps(buffered_log))
                else:
                    await ws.send_str(json.dumps({'type':'log','message': buffered_log}))
            except Exception:
                break

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    data = {'cmd': msg.data}
                cmd = data.get('cmd')
                if cmd in ('pause', 'resume', 'restart', 'stop', 'force_stop'):
                    cmd_q.put(cmd)
                    await ws.send_str(json.dumps({'type':'status','msg': cmd}))
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        # Remove connection from broadcast list when client disconnects
        websocket_connections.discard(ws)

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
    setup_name = data.get('setup_name')
    
    if not name:
        return web.Response(status=400, text='name required')
    
    cmd_q: 'queue.Queue' = request.app['cmd_q']
    
    # Send both setup and main macro names
    if setup_name:
        cmd_q.put(f'load:{name}:{setup_name}')
    else:
        cmd_q.put(f'load:{name}')
    
    return web.Response(status=200)


async def api_run_once(request):
    data = await request.json()
    name = data.get('name')
    
    if not name:
        return web.Response(status=400, text='name required')
    
    cmd_q: 'queue.Queue' = request.app['cmd_q']
    
    # Send run-once command
    cmd_q.put(f'run_once:{name}')
    
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


async def api_set_alerts(request):
    """Set alert interval for iteration notifications."""
    try:
        data = await request.json()
        alert_interval = data.get('alert_interval', 0)
        
        # Validate alert interval
        if not isinstance(alert_interval, int) or alert_interval < 0:
            return web.Response(status=400, text='Alert interval must be a non-negative integer')
        
        if alert_interval > 10000:
            return web.Response(status=400, text='Alert interval cannot exceed 10000')
        
        # Send command to worker to set alert interval
        cmd_q: 'queue.Queue' = request.app['cmd_q']
        cmd_q.put(f'alert:{alert_interval}')
        
        return web.json_response({
            'alert_interval': alert_interval,
            'message': f'Alert interval set to {alert_interval} iterations' if alert_interval > 0 else 'Alerts disabled'
        })
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def api_command(request):
    """Generic command API endpoint for sending commands to the worker."""
    try:
        data = await request.json()
        command = data.get('command')
        
        if not command:
            return web.Response(status=400, text='command required')
        
        cmd_q: 'queue.Queue' = request.app['cmd_q']
        
        if command == 'run_macro':
            setup_macro = data.get('setup_macro')
            main_macro = data.get('main_macro')
            
            if not main_macro:
                return web.Response(status=400, text='main_macro required')
            
            # Send load command with both setup and main macro
            if setup_macro:
                cmd_q.put(f'load:{main_macro}:{setup_macro}')
            else:
                cmd_q.put(f'load:{main_macro}')
                
        elif command == 'set_alerts':
            interval = data.get('interval', 0)
            # Validate interval
            if not isinstance(interval, int) or interval < 0 or interval > 10000:
                return web.Response(status=400, text='Invalid alert interval')
            cmd_q.put(f'alert:{interval}')
            
        elif command == 'set_adapter':
            adapter = data.get('adapter', '')
            cmd_q.put(f'adapter:{adapter}')
            
        elif command in ['pause', 'resume', 'force_stop', 'test_adapters']:
            cmd_q.put(command)
            
        else:
            return web.Response(status=400, text=f'Unknown command: {command}')
        
        return web.json_response({'status': 'ok', 'command': command})
        
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def api_reset_metrics(request):
    """Reset macro status metrics (iterations, runtime, etc.)."""
    try:
        cmd_q: 'queue.Queue' = request.app['cmd_q']
        cmd_q.put('reset_metrics')
        return web.json_response({'status': 'ok', 'message': 'Metrics reset'})
    except Exception as e:
        return web.Response(status=500, text=str(e))
