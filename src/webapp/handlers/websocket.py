"""WebSocket handlers for real-time communication.

This module provides WebSocket endpoints for real-time communication between
the web frontend and the macro execution backend. It handles connection
management, message broadcasting, and command forwarding.

Example:
    # Set up WebSocket handler in aiohttp app
    app.router.add_get('/ws', websocket_handler)
"""
from __future__ import annotations

import json
import queue
from aiohttp import web, WSMsgType
from typing import Set


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections for real-time communication.
    
    This handler manages WebSocket connections, forwards commands to the worker,
    and broadcasts status updates and logs to connected clients.
    
    Args:
        request: The aiohttp web request containing WebSocket upgrade.
        
    Returns:
        WebSocketResponse: The established WebSocket connection.
        
    Raises:
        ConnectionError: If WebSocket handshake fails.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    app = request.app
    cmd_q: queue.Queue = app['cmd_q']
    log_buffer = app['log_buffer']
    websocket_connections: Set[web.WebSocketResponse] = app['websocket_connections']

    # Add this connection to the broadcast list
    websocket_connections.add(ws)

    # Send initial connection status
    await _send_message(ws, {'type': 'status', 'msg': 'connected'})

    # Send recent logs from buffer to new connection
    await _send_buffered_logs(ws, log_buffer)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await _handle_websocket_message(ws, msg, cmd_q)
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        # Remove connection from broadcast list when client disconnects
        websocket_connections.discard(ws)

    return ws


async def _send_message(ws: web.WebSocketResponse, data: dict) -> None:
    """Send a JSON message through the WebSocket.
    
    Args:
        ws: The WebSocket connection to send through.
        data: The data dictionary to send as JSON.
    """
    try:
        await ws.send_str(json.dumps(data))
    except Exception:
        # Connection may be closed, ignore send errors
        pass


async def _send_buffered_logs(ws: web.WebSocketResponse, log_buffer: dict) -> None:
    """Send buffered logs to a newly connected WebSocket client.
    
    Args:
        ws: The WebSocket connection to send logs to.
        log_buffer: The application's log buffer with 'lock' and 'logs' keys.
    """
    with log_buffer['lock']:
        for buffered_log in log_buffer['logs']:
            try:
                if isinstance(buffered_log, dict):
                    await ws.send_str(json.dumps(buffered_log))
                else:
                    await ws.send_str(json.dumps({
                        'type': 'log', 
                        'message': buffered_log
                    }))
            except Exception:
                # Stop sending if connection fails
                break


async def _handle_websocket_message(
    ws: web.WebSocketResponse, 
    msg: WSMsgType, 
    cmd_q: queue.Queue
) -> None:
    """Handle incoming WebSocket messages and forward commands.
    
    Args:
        ws: The WebSocket connection that sent the message.
        msg: The WebSocket message to process.
        cmd_q: The command queue to forward commands to.
    """
    try:
        data = json.loads(msg.data)
    except Exception:
        # Fallback to treating raw message as command
        data = {'cmd': msg.data}
    
    cmd = data.get('cmd')
    
    # Process control commands
    if cmd in ('pause', 'resume', 'restart', 'stop', 'force_stop'):
        cmd_q.put(cmd)
        await _send_message(ws, {'type': 'status', 'msg': cmd})