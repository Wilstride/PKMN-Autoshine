"""Launcher for the web control UI.

This module sets up thread-safe queues, starts the worker thread and
exposes start_server(macro_file, host, port) which runs the aiohttp app.
"""
from __future__ import annotations

import asyncio
import threading
import queue
import time
from aiohttp import web

from . import handlers
from . import worker


async def start_server(macro_file: str | None, host: str = '0.0.0.0', port: int = 8080):
    cmd_q: 'queue.Queue' = queue.Queue()
    logs_term_q: 'queue.Queue' = queue.Queue()
    logs_ws_q: 'queue.Queue' = queue.Queue()

    async def terminal_log_printer():
        loop = asyncio.get_event_loop()
        while True:
            msg = await loop.run_in_executor(None, logs_term_q.get)
            print(msg)

    term_logger = asyncio.create_task(terminal_log_printer())

    macro_status = worker.MacroStatus()
    
    # Store adapter preference in a mutable container (None = auto-detect, prioritizing Pico)
    adapter_config = {'preferred': None}

    def _start_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(worker.worker_main(macro_file, cmd_q, [logs_term_q, logs_ws_q,], status=macro_status, preferred_adapter=adapter_config['preferred']))

    worker_thread = threading.Thread(target=_start_worker, daemon=True)
    worker_thread.start()

    app = web.Application()
    app['cmd_q'] = cmd_q
    app['logs_ws_q'] = logs_ws_q
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
    app.router.add_post('/api/stop', handlers.api_stop)
    app.router.add_get('/api/adapters', handlers.api_list_adapters)
    app.router.add_get('/api/adapters/status', handlers.api_adapter_status)
    app.router.add_post('/api/adapters/select', handlers.api_select_adapter)
    app.router.add_post('/api/alerts/set', handlers.api_set_alerts)

    async def api_status(request):
        return web.json_response(request.app['macro_status'].to_dict())
    app.router.add_get('/api/status', api_status)

    app_runner = web.AppRunner(app)
    await app_runner.setup()
    site = web.TCPSite(app_runner, host=host, port=port)
    await site.start()
    print(f'Web control running on http://{host}:{port}')
    try:
        await app['shutdown_event'].wait()
    finally:
        term_logger.cancel()
        try:
            cmd_q.put('stop')
        except Exception:
            pass
        await app_runner.cleanup()
