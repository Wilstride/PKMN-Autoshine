"""Legacy worker module - imports from refactored worker package.

This module maintains backward compatibility by re-exporting the public API
from the refactored worker package. New code should import directly from
the worker package modules.

DEPRECATED: This module will be removed in a future version.
Use: from webapp.worker import MacroStatus, worker_main
"""
from __future__ import annotations

# Import everything from the new worker package
from .worker import *

# Specific imports for explicit compatibility
from .worker.status import MacroStatus
from .worker.worker_main import worker_main
from .worker.broadcasting import broadcast_log, broadcast_status

__all__ = [
    'MacroStatus',
    'worker_main',
    'broadcast_log', 
    'broadcast_status'
]
