"""Message broadcasting utilities for WebSocket communication.

This module provides functions to broadcast log messages and status updates
to all connected WebSocket clients through thread-safe queues.
"""
from __future__ import annotations

import queue
from typing import List, Dict, Any

from .status import MacroStatus


def broadcast_log_message(
    log_queues: List[queue.Queue], 
    message: str, 
    level: str = 'info'
) -> None:
    """Broadcast a log message to all connected WebSocket clients.
    
    Args:
        log_queues: List of thread-safe queues for WebSocket connections.
        message: The log message to broadcast.
        level: Log level ('info', 'warning', 'error', 'success').
    """
    log_msg: Dict[str, str] = {
        'type': 'log',
        'message': message,
        'level': level
    }
    
    _broadcast_message(log_queues, log_msg)


def broadcast_status_update(
    log_queues: List[queue.Queue], 
    macro_status: MacroStatus, 
    adapter_name: str = "Unknown"
) -> None:
    """Broadcast a status update to all connected WebSocket clients.
    
    Args:
        log_queues: List of thread-safe queues for WebSocket connections.
        macro_status: Current macro execution status.
        adapter_name: Name of the connected adapter.
    """
    status_msg: Dict[str, Any] = {
        'type': 'status',
        'status': f"Running: {macro_status.iterations} iterations" if macro_status.name else "Idle",
        'macro_name': macro_status.name or "No macro loaded",
        'adapter_name': adapter_name,
        'iterations': macro_status.iterations
    }
    
    _broadcast_message(log_queues, status_msg)


def _broadcast_message(log_queues: List[queue.Queue], message: Dict[str, Any]) -> None:
    """Internal helper to broadcast a message to all queues.
    
    Uses both immediate (put_nowait) and blocking (put) strategies to ensure
    message delivery while handling queue full conditions gracefully.
    
    Args:
        log_queues: List of thread-safe queues for WebSocket connections.
        message: Message dictionary to broadcast.
    """
    for log_queue in log_queues:
        try:
            log_queue.put_nowait(message)
        except queue.Full:
            try:
                # Fallback to blocking put if queue is full
                log_queue.put(message)
            except Exception:
                # Silently ignore if client connection is dead
                pass
        except Exception:
            # Silently ignore other queue errors (e.g., closed connections)
            pass


# Legacy function names for backward compatibility
# TODO: Remove these after updating all imports
def broadcast_log(logs_qs: list, message: str, level: str = 'info') -> None:
    """Legacy function name - use broadcast_log_message instead."""
    broadcast_log_message(logs_qs, message, level)


def broadcast_status(logs_qs: list, app_status: MacroStatus, adapter_name: str = "Unknown") -> None:
    """Legacy function name - use broadcast_status_update instead."""
    broadcast_status_update(logs_qs, app_status, adapter_name)