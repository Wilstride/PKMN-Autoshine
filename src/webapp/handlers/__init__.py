"""Refactored webapp handlers package.

This package provides modular HTTP and WebSocket handlers for the macro automation
web interface. The handlers are organized by functionality:

- websocket: Real-time WebSocket communication
- macros: Macro file management and execution
- control: Execution control and configuration
- adapters: Hardware adapter management
- static: Static content serving

Example:
    # Import specific handlers
    from webapp.handlers.websocket import websocket_handler
    from webapp.handlers.macros import list_macros, select_macro
    from webapp.handlers.control import stop, reset_metrics
    
    # Register with aiohttp app
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/api/macros', list_macros)
"""
from __future__ import annotations

# WebSocket handlers
from .websocket import websocket_handler

# Macro management handlers
from .macros import (
    list_macros,
    get_macro, 
    save_macro,
    select_macro,
    run_once,
    run_macro_command
)

# Control command handlers
from .control import (
    stop,
    set_alerts,
    command,
    reset_metrics
)

# Adapter management handlers
from .adapters import (
    list_adapters,
    adapter_status,
    select_adapter,
    test_adapters,
    adapter_command
)

# Static content handlers
from .static import (
    index,
    favicon,
    static_file
)

# Public API exports
__all__ = [
    # WebSocket
    'websocket_handler',
    
    # Macros
    'list_macros',
    'get_macro',
    'save_macro', 
    'select_macro',
    'run_once',
    'run_macro_command',
    
    # Control
    'stop',
    'set_alerts',
    'command',
    'reset_metrics',
    
    # Adapters
    'list_adapters',
    'adapter_status',
    'select_adapter',
    'test_adapters',
    'adapter_command',
    
    # Static
    'index',
    'favicon',
    'static_file'
]


# Legacy import compatibility - these are the original handler names
# that may be used in existing code
api_list_macros = list_macros
api_get_macro = get_macro
api_save_macro = save_macro
api_select_macro = select_macro
api_run_once = run_once
api_stop = stop
api_list_adapters = list_adapters
api_adapter_status = adapter_status
api_select_adapter = select_adapter
api_set_alerts = set_alerts
api_command = command
api_reset_metrics = reset_metrics