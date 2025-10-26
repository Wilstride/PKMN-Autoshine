"""HTTP and WebSocket request handlers."""
from __future__ import annotations

import asyncio
import json
import pathlib
from aiohttp import web, WSMsgType
from typing import Set

# Will be set by server.py
pico_manager = None
log_queue = None
websocket_connections: Set[web.WebSocketResponse] = set()

# Paths - will be set by server.py
MACROS_DIR = None
STATIC_DIR = None


def log_message(msg: str, level: str = 'info') -> None:
    """Add message to log queue."""
    if log_queue is None:
        print(f"[{level}] {msg}")
        return
    
    try:
        log_queue.put_nowait({'type': 'log', 'message': msg, 'level': level})
    except:
        pass  # Drop message if queue is full


async def broadcast_logs() -> None:
    """Broadcast logs to all connected WebSocket clients."""
    if log_queue is None:
        return
    
    loop = asyncio.get_event_loop()
    while True:
        try:
            msg = await loop.run_in_executor(None, log_queue.get)
            json_msg = json.dumps(msg)
            
            # Send to all connected clients
            for ws in list(websocket_connections):
                try:
                    if not ws.closed:
                        await ws.send_str(json_msg)
                    else:
                        websocket_connections.discard(ws)
                except Exception:
                    websocket_connections.discard(ws)
        except Exception:
            await asyncio.sleep(0.1)


# ===== HTTP Handlers =====

async def serve_index(request: web.Request) -> web.Response:
    """Serve main HTML page."""
    html_path = STATIC_DIR / 'index.html'
    if not html_path.exists():
        return web.Response(status=404, text='UI not found')
    return web.Response(text=html_path.read_text(), content_type='text/html')


async def serve_static(request: web.Request) -> web.Response:
    """Serve static files."""
    filename = request.match_info['filename']
    file_path = STATIC_DIR / filename
    
    if not file_path.exists() or not file_path.is_file():
        return web.Response(status=404, text='File not found')
    
    # Determine content type
    content_type = 'text/plain'
    if filename.endswith('.css'):
        content_type = 'text/css'
    elif filename.endswith('.js'):
        content_type = 'application/javascript'
    elif filename.endswith('.html'):
        content_type = 'text/html'
    
    return web.Response(text=file_path.read_text(), content_type=content_type)


# ===== WebSocket Handler =====

async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections for real-time control."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    websocket_connections.add(ws)
    await ws.send_str(json.dumps({'type': 'status', 'message': 'connected'}))
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    cmd = data.get('command')
                    target_port = data.get('port')  # Optional: specific device
                    
                    if cmd:
                        if target_port:
                            # Send to specific device
                            device = pico_manager.get_device(target_port)
                            if device and device.connected:
                                device.send_command(cmd)
                                log_message(f"Sent '{cmd}' to {device.name}")
                            else:
                                log_message(f"Device {target_port} not connected", 'warning')
                        else:
                            # Broadcast to all devices
                            count = pico_manager.send_command_to_all(cmd)
                            log_message(f"Broadcast '{cmd}' to {count} device(s)")
                except Exception as e:
                    log_message(f"WebSocket error: {e}", 'error')
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        websocket_connections.discard(ws)
    
    return ws


# ===== Device Management Handlers =====

async def list_devices(request: web.Request) -> web.Response:
    """List all connected Pico devices."""
    devices = [device.to_dict() for device in pico_manager.get_all_devices()]
    return web.json_response(devices)


async def refresh_devices(request: web.Request) -> web.Response:
    """Discover and connect to new Pico devices."""
    old_count = len(pico_manager.get_all_devices())
    new_connections = pico_manager.connect_all()
    new_count = len(pico_manager.get_all_devices())
    
    devices = [device.to_dict() for device in pico_manager.get_all_devices()]
    
    log_message(f"Device refresh: {new_count} total, {new_connections} new")
    
    return web.json_response({
        'devices': devices,
        'total': new_count,
        'new_connections': new_connections
    })


async def get_pico_status(request: web.Request) -> web.Response:
    """Get status of all Pico devices."""
    devices = [device.to_dict() for device in pico_manager.get_all_devices()]
    return web.json_response({
        'devices': devices,
        'count': len(devices),
        'connected': len([d for d in devices if d['connected']])
    })


# ===== Macro Management Handlers =====

async def list_macros(request: web.Request) -> web.Response:
    """List all available macro files."""
    macros = []
    for file in MACROS_DIR.glob('*.txt'):
        macros.append({
            'name': file.name,
            'size': file.stat().st_size,
            'modified': file.stat().st_mtime
        })
    return web.json_response(macros)


async def get_macro(request: web.Request) -> web.Response:
    """Get content of a specific macro file."""
    name = request.match_info['name']
    safe_name = pathlib.Path(name).name
    macro_path = MACROS_DIR / safe_name
    
    if not macro_path.exists():
        return web.Response(status=404, text=f'Macro "{name}" not found')
    
    return web.Response(text=macro_path.read_text(), content_type='text/plain')


async def create_macro(request: web.Request) -> web.Response:
    """Create a new macro file."""
    try:
        data = await request.json()
        name = data.get('name')
        content = data.get('content', '')
        
        if not name:
            return web.Response(status=400, text='name required')
        
        safe_name = pathlib.Path(name).name
        if not safe_name.endswith('.txt'):
            safe_name += '.txt'
        
        macro_path = MACROS_DIR / safe_name
        
        if macro_path.exists():
            return web.Response(status=409, text=f'Macro "{safe_name}" already exists')
        
        macro_path.write_text(content)
        log_message(f"Created macro: {safe_name}", 'success')
        
        return web.json_response({'status': 'ok', 'name': safe_name})
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def update_macro(request: web.Request) -> web.Response:
    """Update an existing macro file."""
    try:
        name = request.match_info['name']
        data = await request.json()
        content = data.get('content', '')
        
        safe_name = pathlib.Path(name).name
        macro_path = MACROS_DIR / safe_name
        
        if not macro_path.exists():
            return web.Response(status=404, text=f'Macro "{name}" not found')
        
        macro_path.write_text(content)
        log_message(f"Updated macro: {safe_name}", 'info')
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.Response(status=500, text=str(e))


async def delete_macro(request: web.Request) -> web.Response:
    """Delete a macro file."""
    name = request.match_info['name']
    safe_name = pathlib.Path(name).name
    macro_path = MACROS_DIR / safe_name
    
    if not macro_path.exists():
        return web.Response(status=404, text=f'Macro "{name}" not found')
    
    macro_path.unlink()
    log_message(f"Deleted macro: {safe_name}", 'info')
    
    return web.json_response({'status': 'ok', 'message': f'Macro "{safe_name}" deleted'})


# ===== Macro Upload Handler =====

async def upload_macro(request: web.Request) -> web.Response:
    """Upload macro to Pico device(s)."""
    try:
        data = await request.json()
        name = data.get('name')
        target_port = data.get('port')  # Optional: specific device, or None for all
        
        if not name:
            return web.Response(status=400, text='name required')
        
        safe_name = pathlib.Path(name).name
        macro_path = MACROS_DIR / safe_name
        
        if not macro_path.exists():
            return web.Response(status=404, text=f'Macro "{name}" not found')
        
        content = macro_path.read_text()
        
        if target_port:
            # Upload to specific device
            device = pico_manager.get_device(target_port)
            if not device or not device.connected:
                return web.Response(status=503, text=f'Pico {target_port} not connected')
            
            if device.send_macro(content):
                device.current_macro = safe_name
                log_message(f"✓ Uploaded '{safe_name}' to {device.name}", 'success')
                return web.json_response({
                    'status': 'ok',
                    'message': f'Macro uploaded to {device.name}'
                })
            else:
                log_message(f"✗ Failed to upload to {device.name}", 'error')
                return web.Response(status=500, text='Failed to upload macro')
        else:
            # Upload to all connected devices
            devices = pico_manager.get_connected_devices()
            if not devices:
                return web.Response(status=503, text='No Picos connected')
            
            success_count = 0
            for device in devices:
                if device.send_macro(content):
                    device.current_macro = safe_name
                    success_count += 1
            
            if success_count > 0:
                log_message(f"✓ Uploaded '{safe_name}' to {success_count}/{len(devices)} device(s)", 'success')
                return web.json_response({
                    'status': 'ok',
                    'message': f'Macro uploaded to {success_count} device(s)',
                    'count': success_count
                })
            else:
                log_message(f"✗ Failed to upload to any device", 'error')
                return web.Response(status=500, text='Failed to upload to any device')
    except Exception as e:
        log_message(f"Upload error: {e}", 'error')
        import traceback
        traceback.print_exc()
        return web.Response(status=500, text=str(e))


# ===== Pairing Control Handler =====

async def enable_pairing(request: web.Request) -> web.Response:
    """Enable pairing mode on a specific Pico device."""
    try:
        data = await request.json()
        target_port = data.get('port')
        
        if not target_port:
            return web.Response(status=400, text='port required')
        
        device = pico_manager.get_device(target_port)
        if not device or not device.connected:
            return web.Response(status=503, text=f'Pico {target_port} not connected')
        
        # Send PAIR command to device
        device.send_command('PAIR')
        log_message(f"🔗 Pairing mode enabled on {device.name}", 'info')
        
        return web.json_response({
            'status': 'ok',
            'message': f'Pairing mode enabled on {device.name}',
            'port': target_port
        })
    except Exception as e:
        log_message(f"Pairing error: {e}", 'error')
        return web.Response(status=500, text=str(e))
