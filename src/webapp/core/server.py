"""Main server module."""
from __future__ import annotations

import asyncio
import pathlib
import queue
from aiohttp import web

from .pico_manager import PicoManager
from . import handlers

# Paths
ROOT = pathlib.Path(__file__).parent.parent.parent.parent
MACROS_DIR = ROOT / 'data' / 'macros'
STATIC_DIR = pathlib.Path(__file__).parent.parent / 'static'

# Ensure macros directory exists
MACROS_DIR.mkdir(parents=True, exist_ok=True)


def setup_routes(app: web.Application) -> None:
    """Configure all application routes."""
    # Static files
    app.router.add_get('/', handlers.serve_index)
    app.router.add_get('/static/{filename}', handlers.serve_static)
    
    # WebSocket
    app.router.add_get('/ws', handlers.websocket_handler)
    
    # Device management
    app.router.add_get('/api/pico/devices', handlers.list_devices)
    app.router.add_post('/api/pico/refresh', handlers.refresh_devices)
    app.router.add_get('/api/pico/status', handlers.get_pico_status)
    
    # Macro management
    app.router.add_get('/api/macros', handlers.list_macros)
    app.router.add_get('/api/macros/{name}', handlers.get_macro)
    app.router.add_post('/api/macros', handlers.create_macro)
    app.router.add_put('/api/macros/{name}', handlers.update_macro)
    app.router.add_delete('/api/macros/{name}', handlers.delete_macro)
    
    # Macro upload
    app.router.add_post('/api/upload', handlers.upload_macro)


async def poll_serial_buffers(pico_manager: PicoManager) -> None:
    """Background task to poll all Pico serial buffers every 100ms."""
    while True:
        try:
            pico_manager.poll_all_devices()
            await asyncio.sleep(0.1)  # 100ms polling interval
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in serial buffer polling: {e}")
            await asyncio.sleep(0.1)


async def on_startup(app: web.Application) -> None:
    """Initialize services on server startup."""
    print("🎮 Starting PKMN-Autoshine Multi-Pico Server...")
    
    # Start log broadcaster
    app['log_broadcast_task'] = asyncio.create_task(handlers.broadcast_logs())
    
    # Connect to all available Picos
    connected = app['pico_manager'].connect_all()
    
    print(f"🎯 Connected Picos: {connected}")
    for device in app['pico_manager'].get_all_devices():
        print(f"   - {device.name} ({device.port})")
    
    # Start background serial buffer polling (100ms intervals)
    app['polling_task'] = asyncio.create_task(poll_serial_buffers(app['pico_manager']))
    print("📡 Serial buffer polling started (100ms interval)")
    
    print(f"📁 Macros: {MACROS_DIR}")


async def on_shutdown(app: web.Application) -> None:
    """Cleanup on server shutdown."""
    print("\n🛑 Shutting down server...")
    
    # Cancel serial buffer polling
    if 'polling_task' in app:
        app['polling_task'].cancel()
        try:
            await app['polling_task']
        except asyncio.CancelledError:
            pass
    
    # Cancel log broadcaster
    if 'log_broadcast_task' in app:
        app['log_broadcast_task'].cancel()
        try:
            await app['log_broadcast_task']
        except asyncio.CancelledError:
            pass
    
    # Disconnect all devices
    app['pico_manager'].disconnect_all()
    
    print("✓ Server stopped")


def start_server(host: str = '0.0.0.0', port: int = 8080) -> None:
    """Start the web server."""
    # Create application
    app = web.Application()
    
    # Initialize global state
    app['pico_manager'] = PicoManager(logger=print)
    app['log_queue'] = queue.Queue(maxsize=100)
    
    # Set global references for handlers
    handlers.pico_manager = app['pico_manager']
    handlers.log_queue = app['log_queue']
    handlers.MACROS_DIR = MACROS_DIR
    handlers.STATIC_DIR = STATIC_DIR
    
    # Setup routes
    setup_routes(app)
    
    # Register startup/shutdown handlers
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Run server
    print(f"🎮 PKMN Autoshine Multi-Pico Server")
    print(f"📡 Listening on http://{host}:{port}")
    
    web.run_app(app, host=host, port=port, print=lambda x: None)


if __name__ == '__main__':
    start_server()
