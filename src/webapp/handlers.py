"""Legacy handlers module - imports from refactored handlers package.

This module maintains backward compatibility by re-exporting the public API
from the refactored handlers package. New code should import directly from
the handlers package modules.

DEPRECATED: This module will be removed in a future version.
Use: from webapp.handlers import websocket_handler, list_macros, etc.
"""
from __future__ import annotations

import pathlib

# Import everything from the new handlers package
from .handlers import *

# Specific imports for explicit compatibility
from .handlers.websocket import websocket_handler
from .handlers.macros import (
    list_macros as api_list_macros,
    get_macro as api_get_macro,
    save_macro as api_save_macro,
    select_macro as api_select_macro,
    run_once as api_run_once
)
from .handlers.control import (
    stop as api_stop,
    set_alerts as api_set_alerts,
    command as api_command,
    reset_metrics as api_reset_metrics
)
from .handlers.adapters import (
    list_adapters as api_list_adapters,
    adapter_status as api_adapter_status,
    select_adapter as api_select_adapter
)
from .handlers.static import index

# Legacy globals for compatibility
ROOT = pathlib.Path(__file__).parent.parent.parent
INDEX_HTML = None  # Deprecated - use handlers.static.index instead

__all__ = [
    'websocket_handler',
    'index',
    'api_list_macros',
    'api_get_macro',
    'api_save_macro',
    'api_select_macro',
    'api_run_once',
    'api_stop',
    'api_set_alerts',
    'api_command',
    'api_reset_metrics',
    'api_list_adapters',
    'api_adapter_status',
    'api_select_adapter',
    'ROOT',
    'INDEX_HTML'
]
