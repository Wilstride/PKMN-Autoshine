"""Control command API handlers.

This module provides HTTP API endpoints for controlling macro execution,
managing alerts, and resetting metrics. It handles pause/resume/stop commands
and configuration changes.

Example:
    # Register control endpoints  
    app.router.add_post('/api/stop', stop)
    app.router.add_post('/api/command', command)
"""
from __future__ import annotations

import asyncio
import queue
from aiohttp import web
from typing import Dict, Any, Optional


async def stop(request: web.Request) -> web.Response:
    """Stop macro execution and trigger application shutdown.
    
    This endpoint stops any running macro and sets the shutdown event
    to gracefully terminate the application.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        HTTP 200 response indicating stop command was sent.
    """
    cmd_q: queue.Queue = request.app['cmd_q']
    
    try:
        cmd_q.put('stop')
    except Exception:
        # Queue might be full or closed, ignore
        pass
    
    # Signal application shutdown
    shutdown_event: Optional[asyncio.Event] = request.app.get('shutdown_event')
    if shutdown_event is not None:
        shutdown_event.set()
    
    return web.json_response({
        'status': 'ok',
        'message': 'Stop command sent, application shutting down'
    })


async def set_alerts(request: web.Request) -> web.Response:
    """Set alert interval for iteration notifications.
    
    Expects JSON body with:
    - alert_interval: Integer number of iterations between alerts (0 to disable)
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 200 on success, 400 for invalid interval values.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    alert_interval = data.get('alert_interval', 0)
    
    # Validate alert interval
    if not isinstance(alert_interval, int) or alert_interval < 0:
        return web.Response(
            status=400, 
            text='Alert interval must be a non-negative integer'
        )
    
    if alert_interval > 10000:
        return web.Response(
            status=400, 
            text='Alert interval cannot exceed 10000'
        )
    
    # Send command to worker to set alert interval
    cmd_q: queue.Queue = request.app['cmd_q']
    cmd_q.put(f'alert:{alert_interval}')
    
    message = (
        f'Alert interval set to {alert_interval} iterations' 
        if alert_interval > 0 
        else 'Alerts disabled'
    )
    
    return web.json_response({
        'status': 'ok',
        'alert_interval': alert_interval,
        'message': message
    })


async def command(request: web.Request) -> web.Response:
    """Generic command API endpoint for sending commands to the worker.
    
    This is a flexible endpoint that handles various command types.
    
    Expects JSON body with:
    - command: The command type to execute
    - Additional parameters depending on command type
    
    Supported commands:
    - run_macro: Run macro with optional setup (requires main_macro, optional setup_macro)
    - set_alerts: Set alert interval (requires interval)
    - set_adapter: Set adapter preference (requires adapter)
    - pause, resume, force_stop, test_adapters: Simple commands
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 200 on success, 400 for invalid commands or missing parameters.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    command = data.get('command')
    
    if not command:
        return web.Response(status=400, text='command required')
    
    cmd_q: queue.Queue = request.app['cmd_q']
    
    try:
        if command == 'run_macro':
            return await _handle_run_macro_command(data, cmd_q)
        elif command == 'set_alerts':
            return await _handle_set_alerts_command(data, cmd_q)
        elif command == 'set_adapter':
            return await _handle_set_adapter_command(data, cmd_q)
        elif command in ['pause', 'resume', 'force_stop', 'test_adapters']:
            return await _handle_simple_command(command, cmd_q)
        else:
            return web.Response(status=400, text=f'Unknown command: {command}')
    except Exception as e:
        return web.Response(status=500, text=f'Error processing command: {e}')


async def reset_metrics(request: web.Request) -> web.Response:
    """Reset macro status metrics (iterations, runtime, etc.).
    
    This endpoint resets all macro execution metrics including iteration
    count, runtime, and other statistics tracked by the worker.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        HTTP 200 response indicating metrics were reset.
    """
    try:
        cmd_q: queue.Queue = request.app['cmd_q']
        cmd_q.put('reset_metrics')
        
        return web.json_response({
            'status': 'ok', 
            'message': 'Metrics reset successfully'
        })
    except Exception as e:
        return web.Response(status=500, text=f'Error resetting metrics: {e}')


# Private helper functions for command handling

async def _handle_run_macro_command(data: Dict[str, Any], cmd_q: queue.Queue) -> web.Response:
    """Handle run_macro command with setup macro support.
    
    Args:
        data: The request data containing macro names.
        cmd_q: The command queue to send commands to.
        
    Returns:
        HTTP response indicating success or failure.
    """
    setup_macro = data.get('setup_macro')
    main_macro = data.get('main_macro')
    
    if not main_macro:
        return web.Response(status=400, text='main_macro required')
    
    # Send load command with both setup and main macro
    if setup_macro:
        cmd_q.put(f'load:{main_macro}:{setup_macro}')
        message = f'Running macro "{main_macro}" with setup "{setup_macro}"'
    else:
        cmd_q.put(f'load:{main_macro}')
        message = f'Running macro "{main_macro}"'
    
    return web.json_response({
        'status': 'ok',
        'command': 'run_macro',
        'message': message
    })


async def _handle_set_alerts_command(data: Dict[str, Any], cmd_q: queue.Queue) -> web.Response:
    """Handle set_alerts command with validation.
    
    Args:
        data: The request data containing alert interval.
        cmd_q: The command queue to send commands to.
        
    Returns:
        HTTP response indicating success or failure.
    """
    interval = data.get('interval', 0)
    
    # Validate interval
    if not isinstance(interval, int) or interval < 0 or interval > 10000:
        return web.Response(status=400, text='Invalid alert interval (0-10000)')
    
    cmd_q.put(f'alert:{interval}')
    
    message = (
        f'Alert interval set to {interval} iterations' 
        if interval > 0 
        else 'Alerts disabled'
    )
    
    return web.json_response({
        'status': 'ok',
        'command': 'set_alerts',
        'interval': interval,
        'message': message
    })


async def _handle_set_adapter_command(data: Dict[str, Any], cmd_q: queue.Queue) -> web.Response:
    """Handle set_adapter command.
    
    Args:
        data: The request data containing adapter preference.
        cmd_q: The command queue to send commands to.
        
    Returns:
        HTTP response indicating success or failure.
    """
    adapter = data.get('adapter', '')
    cmd_q.put(f'adapter:{adapter}')
    
    return web.json_response({
        'status': 'ok',
        'command': 'set_adapter',
        'adapter': adapter,
        'message': f'Adapter preference set to "{adapter}"'
    })


async def _handle_simple_command(command: str, cmd_q: queue.Queue) -> web.Response:
    """Handle simple commands that don't require parameters.
    
    Args:
        command: The command string to send.
        cmd_q: The command queue to send commands to.
        
    Returns:
        HTTP response indicating the command was sent.
    """
    cmd_q.put(command)
    
    return web.json_response({
        'status': 'ok',
        'command': command,
        'message': f'Command "{command}" sent'
    })