"""Worker package for macro execution and coordination.

This package provides modular components for running macros in a separate
thread with proper status tracking, command handling, and message broadcasting.

Components:
- status: MacroStatus class for tracking execution metrics
- broadcasting: Functions for sending messages to WebSocket clients  
- command_handler: CommandHandler class for processing web interface commands
- worker_main: Main orchestration and coordination logic

Public API:
- MacroStatus: Status tracking class
- worker_main: Main worker function
- broadcast_log_message: Send log messages to clients
- broadcast_status_update: Send status updates to clients
"""
from __future__ import annotations

# Import main API components
from .status import MacroStatus
from .worker_main import worker_main
from .broadcasting import (
    broadcast_log_message,
    broadcast_status_update,
    # Legacy names for backward compatibility
    broadcast_log,
    broadcast_status
)

__all__ = [
    'MacroStatus',
    'worker_main', 
    'broadcast_log_message',
    'broadcast_status_update',
    # Legacy names
    'broadcast_log',
    'broadcast_status'
]