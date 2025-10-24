"""Static content handlers.

This module provides handlers for serving static web content including
the main HTML interface and static assets.

Example:
    # Register static content handler
    app.router.add_get('/', index)
"""
from __future__ import annotations

import pathlib
from aiohttp import web


async def index(request: web.Request) -> web.Response:
    """Serve the main web interface HTML file.
    
    Serves the single-page application HTML file that provides the
    web-based control interface for macro execution.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        HTML response with the main interface content.
        Returns 500 if the HTML file cannot be read.
    """
    try:
        html_path = pathlib.Path(__file__).parent.parent / 'static' / 'index.html'
        
        if not html_path.exists():
            return web.Response(
                status=404, 
                text='Web interface not found. Please ensure static/index.html exists.'
            )
        
        content = html_path.read_text(encoding='utf-8')
        return web.Response(text=content, content_type='text/html')
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error loading web interface: {e}'
        )


async def favicon(request: web.Request) -> web.Response:
    """Serve the favicon.ico file.
    
    Args:
        request: The aiohttp web request.
        
    Returns:
        ICO file response or 404 if not found.
    """
    try:
        favicon_path = pathlib.Path(__file__).parent.parent / 'static' / 'favicon.ico'
        
        if not favicon_path.exists():
            return web.Response(status=404)
        
        content = favicon_path.read_bytes()
        return web.Response(body=content, content_type='image/x-icon')
    except Exception:
        return web.Response(status=404)


async def static_file(request: web.Request) -> web.Response:
    """Serve static files from the static directory.
    
    Handles requests for CSS, JavaScript, and other static assets.
    
    Args:
        request: The aiohttp web request with 'filename' path parameter.
        
    Returns:
        File response with appropriate content type or 404 if not found.
    """
    filename = request.match_info.get('filename', '')
    
    if not filename:
        return web.Response(status=404, text='Filename required')
    
    # Sanitize filename to prevent directory traversal
    safe_filename = pathlib.Path(filename).name
    if not safe_filename or safe_filename != filename:
        return web.Response(status=400, text='Invalid filename')
    
    try:
        static_path = pathlib.Path(__file__).parent.parent / 'static' / safe_filename
        
        if not static_path.exists() or not static_path.is_file():
            return web.Response(status=404, text=f'File "{filename}" not found')
        
        # Determine content type based on file extension
        content_type = _get_content_type(safe_filename)
        
        if content_type.startswith('text/'):
            content = static_path.read_text(encoding='utf-8')
            return web.Response(text=content, content_type=content_type)
        else:
            content = static_path.read_bytes()
            return web.Response(body=content, content_type=content_type)
    except Exception as e:
        return web.Response(
            status=500, 
            text=f'Error serving static file: {e}'
        )


def _get_content_type(filename: str) -> str:
    """Determine content type based on file extension.
    
    Args:
        filename: The filename to check.
        
    Returns:
        MIME content type string.
    """
    ext = pathlib.Path(filename).suffix.lower()
    
    content_types = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.txt': 'text/plain',
        '.xml': 'application/xml',
        '.pdf': 'application/pdf'
    }
    
    return content_types.get(ext, 'application/octet-stream')