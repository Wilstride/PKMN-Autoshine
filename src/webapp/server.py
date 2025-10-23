"""Launcher for the web control UI.

This module sets up thread-safe queues, starts the worker thread and
exposes start_server(macro_file, host, port) which runs the aiohttp app.
"""
from __future__ import annotations

import asyncio
import threading
import queue
import time
import json
from aiohttp import web

from . import handlers
from . import worker


async def start_server(macro_file: str | None, host: str = '0.0.0.0', port: int = 8080):
    cmd_q: 'queue.Queue' = queue.Queue()
    logs_term_q: 'queue.Queue' = queue.Queue()
    logs_broadcast_q: 'queue.Queue' = queue.Queue()

    # Shared log buffer for web connections (circular buffer of last 10 logs)
    log_buffer = {'logs': [], 'max_size': 10, 'lock': threading.Lock()}
    websocket_connections = set()

    async def terminal_log_printer():
        loop = asyncio.get_event_loop()
        while True:
            msg = await loop.run_in_executor(None, logs_term_q.get)
            print(msg)

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
                        json_msg = json.dumps({'type':'log','message': msg})
                    
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

    term_logger = asyncio.create_task(terminal_log_printer())
    log_broadcaster_task = asyncio.create_task(log_broadcaster())

    macro_status = worker.MacroStatus()
    
    # Store adapter preference in a mutable container (None = auto-detect, prioritizing Pico)
    adapter_config = {'preferred': None}

    def _start_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(worker.worker_main(macro_file, cmd_q, [logs_term_q, logs_broadcast_q,], status=macro_status, preferred_adapter=adapter_config['preferred']))

    worker_thread = threading.Thread(target=_start_worker, daemon=True)
    worker_thread.start()

    app = web.Application()
    app['cmd_q'] = cmd_q
    app['log_buffer'] = log_buffer
    app['websocket_connections'] = websocket_connections
    app['macro_status'] = macro_status
    app['shutdown_event'] = asyncio.Event()
    app['adapter_config'] = adapter_config

    app.router.add_get('/', handlers.index)
    app.router.add_get('/ws', handlers.websocket_handler)
    
    # Add static file routes
    import pathlib
    static_dir = pathlib.Path(__file__).parent / 'static'
    app.router.add_static('/static/', static_dir, name='static')
    app.router.add_get('/api/macros', handlers.api_list_macros)
    app.router.add_get('/api/macro/{name}', handlers.api_get_macro)
    app.router.add_post('/api/macros', handlers.api_save_macro)
    app.router.add_post('/api/command', handlers.api_command)
    app.router.add_post('/api/select', handlers.api_select_macro)
    app.router.add_post('/api/run-once', handlers.api_run_once)
    app.router.add_post('/api/stop', handlers.api_stop)
    app.router.add_get('/api/adapters', handlers.api_list_adapters)
    app.router.add_get('/api/adapters/status', handlers.api_adapter_status)
    app.router.add_post('/api/adapters/select', handlers.api_select_adapter)
    app.router.add_post('/api/alerts/set', handlers.api_set_alerts)
    app.router.add_post('/api/reset-metrics', handlers.api_reset_metrics)

    async def api_status(request):
        return web.json_response(request.app['macro_status'].to_dict())
    app.router.add_get('/api/status', api_status)

    async def api_recent_logs(request):
        log_buffer = request.app['log_buffer']
        with log_buffer['lock']:
            logs = log_buffer['logs'].copy()
        return web.json_response({'logs': logs})
    app.router.add_get('/api/logs/recent', api_recent_logs)

    app_runner = web.AppRunner(app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=host, port=port)
    await site.start()
    print(f'Web control running on http://{host}:{port}')
    try:
        await app['shutdown_event'].wait()
    finally:
        term_logger.cancel()
        log_broadcaster_task.cancel()
        try:
            cmd_q.put('stop')
        except Exception:
            pass
        await app_runner.cleanup()
