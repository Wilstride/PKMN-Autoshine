"""Adapter management API handlers.

This module provides HTTP API endpoints for managing hardware adapters
(Pico, joycontrol, etc.). It handles listing available adapters, testing
connectivity, and setting preferences.

Example:
    # Register adapter endpoints
    app.router.add_get('/api/adapters', list_adapters)
    app.router.add_post('/api/adapters/select', select_adapter)
"""
from __future__ import annotations

import queue
from aiohttp import web
from typing import Dict, Any, List


async def list_adapters(request: web.Request) -> web.Response:
    """List available adapter types.
    
    Returns information about all adapter types that can be used
    for Switch controller emulation.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        JSON response with array of available adapter configurations.
        Returns 500 if adapter factory cannot be imported.
    """
    try:
        from adapter.factory import get_available_adapters
        adapters = get_available_adapters()
        
        return web.json_response({
            'status': 'ok',
            'adapters': adapters,
            'count': len(adapters)
        })
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error listing adapters: {e}'
        )


async def adapter_status(request: web.Request) -> web.Response:
    """Get current adapter preference and test connectivity.
    
    Returns the currently preferred adapter type and connectivity
    status for all available adapters.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        JSON response with preferred adapter and connectivity status.
        Returns 500 if connectivity testing fails.
    """
    try:
        from adapter.factory import test_adapter_connectivity
        
        adapter_config = request.app.get('adapter_config', {})
        preferred = adapter_config.get('preferred')
        
        # Test connectivity for all adapters
        connectivity = await test_adapter_connectivity()
        
        return web.json_response({
            'status': 'ok',
            'preferred': preferred,
            'connectivity': connectivity,
            'timestamp': _get_current_timestamp()
        })
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error checking adapter status: {e}'
        )


async def select_adapter(request: web.Request) -> web.Response:
    """Set the preferred adapter type.
    
    Updates the application's preferred adapter configuration and
    notifies the worker about the change.
    
    Expects JSON body with:
    - adapter: The adapter type ('pico', 'joycontrol', or null for auto)
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        JSON response confirming the adapter preference change.
        Returns 400 for invalid adapter types.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    adapter_type = data.get('adapter')
    
    # Validate adapter type
    valid_adapters = [None, 'pico', 'joycontrol', 'auto']
    if adapter_type not in valid_adapters:
        return web.Response(
            status=400, 
            text=f'Invalid adapter type. Must be one of: {valid_adapters}'
        )
    
    try:
        # Update the app's preferred adapter configuration
        adapter_config = request.app.get('adapter_config', {})
        adapter_config['preferred'] = adapter_type
        
        # Send command to worker to notify about adapter change
        cmd_q: queue.Queue = request.app['cmd_q']
        cmd_q.put(f'adapter:{adapter_type}')
        
        adapter_name = adapter_type or 'auto-detect'
        
        return web.json_response({
            'status': 'ok',
            'preferred': adapter_type,
            'adapter_name': adapter_name,
            'message': f'Adapter preference set to "{adapter_name}". '
                      'Restart the system for changes to take effect.',
            'restart_required': True
        })
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error setting adapter preference: {e}'
        )


async def test_adapters(request: web.Request) -> web.Response:
    """Test connectivity for all available adapters.
    
    Performs connectivity tests for all adapter types and returns
    detailed status information.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        JSON response with detailed connectivity test results.
        Returns 500 if testing fails.
    """
    try:
        from adapter.factory import test_adapter_connectivity, get_available_adapters
        
        # Get available adapters and test connectivity
        available_adapters = get_available_adapters()
        connectivity = await test_adapter_connectivity()
        
        # Add detailed information to connectivity results
        test_results = []
        for adapter_info in available_adapters:
            adapter_type = adapter_info.get('type', 'unknown')
            adapter_name = adapter_info.get('name', adapter_type)
            
            # Find connectivity status for this adapter
            adapter_connectivity = next(
                (conn for conn in connectivity if conn.get('type') == adapter_type),
                {'available': False, 'error': 'No connectivity information'}
            )
            
            test_results.append({
                'type': adapter_type,
                'name': adapter_name,
                'available': adapter_connectivity.get('available', False),
                'error': adapter_connectivity.get('error'),
                'details': adapter_connectivity.get('details', {}),
                **adapter_info  # Include all original adapter info
            })
        
        return web.json_response({
            'status': 'ok',
            'test_results': test_results,
            'timestamp': _get_current_timestamp(),
            'total_adapters': len(test_results),
            'available_count': sum(1 for r in test_results if r['available'])
        })
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error testing adapters: {e}'
        )


async def adapter_command(request: web.Request) -> web.Response:
    """Generic adapter command endpoint.
    
    Handles various adapter-related commands through a single endpoint.
    
    Expects JSON body with:
    - command: The command type ('test', 'select', 'refresh')
    - adapter: Required for 'select' command
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        JSON response based on the command type.
        Returns 400 for invalid commands.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    command = data.get('command')
    
    if not command:
        return web.Response(status=400, text='command required')
    
    if command == 'test':
        # Redirect to test_adapters
        return await test_adapters(request)
    elif command == 'select':
        # Redirect to select_adapter
        return await select_adapter(request)
    elif command == 'refresh':
        # Send refresh command to worker
        cmd_q: queue.Queue = request.app['cmd_q']
        cmd_q.put('test_adapters')
        
        return web.json_response({
            'status': 'ok',
            'command': 'refresh',
            'message': 'Adapter refresh command sent'
        })
    else:
        return web.Response(
            status=400, 
            text=f'Unknown adapter command: {command}'
        )


# Private helper functions

def _get_current_timestamp() -> str:
    """Get current timestamp in ISO format.
    
    Returns:
        Current timestamp as ISO format string.
    """
    from datetime import datetime
    return datetime.now().isoformat()