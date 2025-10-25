"""New web server implementation using PicoManager for direct Pico communication.

This version removes the worker thread and macro execution logic, focusing
on configuration and progress monitoring of PicoSwitchController devices.
"""
from __future__ import annotations

import asyncio
import threading
import queue
import time
import json
from aiohttp import web
from typing import Dict, List, Optional
import pathlib

from . import handlers
from .pico_manager import PicoManager


async def start_pico_server(host: str = '0.0.0.0', port: int = 8080):
    """Start the new Pico-based web server.
    
    Args:
        host: Host address to bind to.
        port: Port to listen on.
    """
    logs_broadcast_q: 'queue.Queue' = queue.Queue()

    # Shared log buffer for web connections (circular buffer of last 100 logs)
    log_buffer = {'logs': [], 'max_size': 100, 'lock': threading.Lock()}
    websocket_connections = set()

    # Initialize PicoManager
    pico_manager = PicoManager()
    
    def pico_response_handler(device_port: str, response: str):
        """Handle responses from Pico devices."""
        message = f"[{device_port}] {response}"
        try:
            logs_broadcast_q.put_nowait(message)
        except queue.Full:
            pass  # Drop message if queue is full

    pico_manager.set_response_callback(pico_response_handler)
    
    # Auto-connect to all available Pico devices
    try:
        connected_count = await pico_manager.connect_all_devices()
        message = f"Connected to {connected_count} Pico device(s)"
        logs_broadcast_q.put_nowait(message)
        print(message)
    except Exception as e:
        message = f"Error connecting to Pico devices: {e}"
        logs_broadcast_q.put_nowait(message)
        print(message)

    # Start monitoring Pico devices
    await pico_manager.start_monitoring()

    async def log_broadcaster():
        """Broadcast logs to all WebSocket connections and maintain log buffer."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                msg = await loop.run_in_executor(None, logs_broadcast_q.get)
                
                # Add to circular buffer
                with log_buffer['lock']:
                    log_buffer['logs'].append(msg)
                    if len(log_buffer['logs']) > log_buffer['max_size']:
                        log_buffer['logs'].pop(0)  # Remove oldest
                
                # Broadcast to all connected WebSocket clients
                if websocket_connections:
                    if isinstance(msg, dict):
                        json_msg = json.dumps(msg)
                    else:
                        json_msg = json.dumps({'type': 'log', 'message': msg})
                    
                    # Create a copy of the set to avoid modification during iteration
                    connections_copy = websocket_connections.copy()
                    for ws in connections_copy:
                        try:
                            if not ws.closed:
                                await ws.send_str(json_msg)
                            else:
                                websocket_connections.discard(ws)
                        except Exception:
                            # Remove broken connections
                            websocket_connections.discard(ws)
            except Exception:
                break

    log_broadcaster_task = asyncio.create_task(log_broadcaster())

    app = web.Application()
    app['log_buffer'] = log_buffer
    app['websocket_connections'] = websocket_connections
    app['pico_manager'] = pico_manager
    app['logs_queue'] = logs_broadcast_q
    app['shutdown_event'] = asyncio.Event()

    # Set up routes
    app.router.add_get('/', pico_index_handler)
    app.router.add_get('/ws', pico_websocket_handler)
    
    # Static files
    static_dir = pathlib.Path(__file__).parent / 'static'
    app.router.add_static('/static/', static_dir, name='static')
    
    # API routes
    app.router.add_get('/api/macros', handlers.api_list_macros)
    app.router.add_get('/api/macros/{name}', handlers.api_get_macro)
    app.router.add_post('/api/macros', handlers.api_save_macro)
    
    # New Pico-specific API routes
    app.router.add_get('/api/pico/devices', api_list_pico_devices)
    app.router.add_post('/api/pico/connect', api_connect_pico_device)
    app.router.add_post('/api/pico/disconnect', api_disconnect_pico_device)
    app.router.add_post('/api/pico/load_macro', api_load_macro_to_picos)
    app.router.add_post('/api/pico/start_macro', api_start_macro_on_picos)
    app.router.add_post('/api/pico/stop_macro', api_stop_macro_on_picos)
    app.router.add_get('/api/pico/status', api_pico_status)

    app.router.add_get('/api/logs/recent', api_recent_logs)

    app_runner = web.AppRunner(app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=host, port=port)
    await site.start()
    print(f'Pico Web Control running on http://{host}:{port}')
    
    try:
        await app['shutdown_event'].wait()
    finally:
        log_broadcaster_task.cancel()
        await pico_manager.cleanup()
        await app_runner.cleanup()


# Handler functions for the new Pico-based server

async def pico_index_handler(request):
    """Serve the main page with Pico-specific interface."""
    path = pathlib.Path(__file__).parent / 'static' / 'pico-index.html'
    return web.Response(text=path.read_text(), content_type='text/html')


async def pico_websocket_handler(request):
    """Handle WebSocket connections for real-time updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    websocket_connections = request.app['websocket_connections']
    websocket_connections.add(ws)
    
    try:
        # Send recent logs to new connection
        log_buffer = request.app['log_buffer']
        with log_buffer['lock']:
            for log_msg in log_buffer['logs']:
                if isinstance(log_msg, dict):
                    await ws.send_str(json.dumps(log_msg))
                else:
                    await ws.send_str(json.dumps({'type': 'log', 'message': log_msg}))
        
        # Send current device status
        pico_manager = request.app['pico_manager']
        status = pico_manager.get_device_status()
        await ws.send_str(json.dumps({'type': 'device_status', 'devices': status}))
        
        async for msg in ws:
            if msg.type == web.MsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    # Handle WebSocket commands if needed
                    pass
                except json.JSONDecodeError:
                    pass
            elif msg.type == web.MsgType.ERROR:
                break
    except Exception as e:
        print(f'WebSocket error: {e}')
    finally:
        websocket_connections.discard(ws)
    
    return ws


async def api_list_pico_devices(request):
    """List all available and connected Pico devices."""
    pico_manager = request.app['pico_manager']
    
    # Discover available devices
    available_ports = await pico_manager.discover_devices()
    
    # Get current status
    device_status = pico_manager.get_device_status()
    
    devices = []
    for port in available_ports:
        status = device_status.get(port, {
            'connected': False,
            'running_macro': False,
            'current_macro': False,
            'iteration_count': 0
        })
        devices.append({
            'port': port,
            'available': True,
            **status
        })
    
    return web.json_response({'devices': devices})


async def api_connect_pico_device(request):
    """Connect to a specific Pico device."""
    data = await request.json()
    port = data.get('port')
    
    if not port:
        return web.Response(status=400, text='port required')
    
    pico_manager = request.app['pico_manager']
    success = await pico_manager.connect_device(port)
    
    if success:
        logs_queue = request.app['logs_queue']
        logs_queue.put_nowait(f"Connected to Pico device on {port}")
        return web.json_response({'success': True})
    else:
        return web.Response(status=500, text=f'Failed to connect to {port}')


async def api_disconnect_pico_device(request):
    """Disconnect from a specific Pico device."""
    data = await request.json()
    port = data.get('port')
    
    if not port:
        return web.Response(status=400, text='port required')
    
    pico_manager = request.app['pico_manager']
    await pico_manager.disconnect_device(port)
    
    logs_queue = request.app['logs_queue']
    logs_queue.put_nowait(f"Disconnected from Pico device on {port}")
    return web.json_response({'success': True})


async def api_load_macro_to_picos(request):
    """Load a macro to selected Pico devices."""
    data = await request.json()
    macro_name = data.get('macro_name')
    device_ports = data.get('device_ports')  # List of ports, or None for all
    
    if not macro_name:
        return web.Response(status=400, text='macro_name required')
    
    # Read macro file
    try:
        from pathlib import Path
        ROOT = Path(__file__).parent.parent.parent
        macro_path = ROOT / 'data' / 'macros' / Path(macro_name).name
        
        if not macro_path.exists():
            return web.Response(status=404, text='Macro file not found')
        
        macro_content = macro_path.read_text()
        
    except Exception as e:
        return web.Response(status=500, text=f'Error reading macro: {e}')
    
    # Load to Pico devices
    pico_manager = request.app['pico_manager']
    results = await pico_manager.load_macro(macro_content, device_ports)
    
    logs_queue = request.app['logs_queue']
    success_count = sum(1 for success in results.values() if success)
    logs_queue.put_nowait(f"Loaded macro '{macro_name}' to {success_count}/{len(results)} devices")
    
    return web.json_response({'results': results})


async def api_start_macro_on_picos(request):
    """Start macro execution on selected Pico devices."""
    data = await request.json()
    device_ports = data.get('device_ports')  # List of ports, or None for all
    
    pico_manager = request.app['pico_manager']
    results = await pico_manager.start_macro(device_ports)
    
    logs_queue = request.app['logs_queue']
    success_count = sum(1 for success in results.values() if success)
    logs_queue.put_nowait(f"Started macro on {success_count}/{len(results)} devices")
    
    return web.json_response({'results': results})


async def api_stop_macro_on_picos(request):
    """Stop macro execution on selected Pico devices."""
    data = await request.json()
    device_ports = data.get('device_ports')  # List of ports, or None for all
    
    pico_manager = request.app['pico_manager']
    results = await pico_manager.stop_macro(device_ports)
    
    logs_queue = request.app['logs_queue']
    success_count = sum(1 for success in results.values() if success)
    logs_queue.put_nowait(f"Stopped macro on {success_count}/{len(results)} devices")
    
    return web.json_response({'results': results})


async def api_pico_status(request):
    """Get status of all Pico devices."""
    pico_manager = request.app['pico_manager']
    status = pico_manager.get_device_status()
    return web.json_response({'devices': status})


async def api_recent_logs(request):
    """Get recent log messages."""
    log_buffer = request.app['log_buffer']
    with log_buffer['lock']:
        logs = log_buffer['logs'].copy()
    return web.json_response({'logs': logs})