"""Macro management API handlers.

This module provides HTTP API endpoints for managing macro files and execution.
It handles listing, loading, saving, and running macros stored in the data directory.

Example:
    # Register macro endpoints
    app.router.add_get('/api/macros', list_macros)
    app.router.add_post('/api/macros/select', select_macro)
"""
from __future__ import annotations

import pathlib
import queue
from aiohttp import web
from typing import Dict, Any


# Root directory for macro storage
_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


async def list_macros(request: web.Request) -> web.Response:
    """List all available macro files.
    
    Returns a JSON array of macro filenames from the data/macros directory.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        JSON response with array of macro filenames, sorted alphabetically.
        Returns empty array if macros directory doesn't exist.
    """
    macros_dir = _ROOT / 'data' / 'macros'
    if not macros_dir.exists():
        return web.json_response([], status=200)
    
    names = [p.name for p in macros_dir.iterdir() if p.is_file()]
    return web.json_response(sorted(names))


async def get_macro(request: web.Request) -> web.Response:
    """Get the content of a specific macro file.
    
    Args:
        request: The aiohttp web request with 'name' path parameter.
        
    Returns:
        Plain text response with macro file content.
        Returns 404 if macro file doesn't exist.
    """
    name = request.match_info['name']
    
    # Sanitize path to prevent directory traversal
    safe_path = pathlib.Path(name).name
    macro_path = _ROOT / 'data' / 'macros' / safe_path
    
    if not macro_path.exists():
        return web.Response(status=404, text=f'Macro "{name}" not found')
    
    try:
        content = macro_path.read_text(encoding='utf-8')
        return web.Response(text=content, content_type='text/plain')
    except Exception as e:
        return web.Response(status=500, text=f'Error reading macro: {e}')


async def save_macro(request: web.Request) -> web.Response:
    """Save macro content to a file.
    
    Expects JSON body with:
    - name: The filename for the macro
    - content: The macro content to save
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 201 on success, 400 if name is missing.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    name = data.get('name')
    content = data.get('content', '')
    
    if not name:
        return web.Response(status=400, text='name required')
    
    if not isinstance(name, str) or not name.strip():
        return web.Response(status=400, text='name must be non-empty string')
    
    # Sanitize filename to prevent directory traversal
    safe_name = pathlib.Path(name).name
    if not safe_name:
        return web.Response(status=400, text='Invalid filename')
    
    macro_path = _ROOT / 'data' / 'macros' / safe_name
    
    try:
        # Ensure macros directory exists
        macro_path.parent.mkdir(parents=True, exist_ok=True)
        macro_path.write_text(content, encoding='utf-8')
        return web.Response(status=201, text=f'Macro "{safe_name}" saved')
    except Exception as e:
        return web.Response(status=500, text=f'Error saving macro: {e}')


async def select_macro(request: web.Request) -> web.Response:
    """Select and load a macro for execution.
    
    Expects JSON body with:
    - name: The main macro filename to load
    - setup_name: Optional setup macro to run before main macro
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 200 on success, 400 if name is missing.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    name = data.get('name')
    setup_name = data.get('setup_name')
    
    if not name:
        return web.Response(status=400, text='name required')
    
    cmd_q: queue.Queue = request.app['cmd_q']
    
    # Send command to worker to load macro(s)
    if setup_name:
        cmd_q.put(f'load:{name}:{setup_name}')
        message = f'Loading macro "{name}" with setup "{setup_name}"'
    else:
        cmd_q.put(f'load:{name}')
        message = f'Loading macro "{name}"'
    
    return web.json_response({
        'status': 'ok',
        'message': message,
        'main_macro': name,
        'setup_macro': setup_name
    })


async def run_once(request: web.Request) -> web.Response:
    """Run a macro exactly once without looping.
    
    Expects JSON body with:
    - name: The macro filename to run once
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 200 on success, 400 if name is missing.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    name = data.get('name')
    
    if not name:
        return web.Response(status=400, text='name required')
    
    cmd_q: queue.Queue = request.app['cmd_q']
    
    # Send run-once command to worker
    cmd_q.put(f'run_once:{name}')
    
    return web.json_response({
        'status': 'ok',
        'message': f'Running macro "{name}" once',
        'macro': name
    })


async def run_macro_command(request: web.Request) -> web.Response:
    """Generic macro command endpoint for running macros with setup.
    
    This is an alternative endpoint that provides more flexibility for
    running macros with optional setup macros.
    
    Expects JSON body with:
    - main_macro: The main macro filename to run
    - setup_macro: Optional setup macro to run first
    
    Args:
        request: The aiohttp web request with JSON body.
        
    Returns:
        HTTP 200 on success, 400 if main_macro is missing.
    """
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text='Invalid JSON body')
    
    main_macro = data.get('main_macro')
    setup_macro = data.get('setup_macro')
    
    if not main_macro:
        return web.Response(status=400, text='main_macro required')
    
    cmd_q: queue.Queue = request.app['cmd_q']
    
    # Send load command with both setup and main macro
    if setup_macro:
        cmd_q.put(f'load:{main_macro}:{setup_macro}')
        message = f'Running macro "{main_macro}" with setup "{setup_macro}"'
    else:
        cmd_q.put(f'load:{main_macro}')
        message = f'Running macro "{main_macro}"'
    
    return web.json_response({
        'status': 'ok',
        'message': message,
        'main_macro': main_macro,
        'setup_macro': setup_macro
    })