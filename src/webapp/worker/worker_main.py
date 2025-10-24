"""Main worker orchestration and coordination.

This module provides the main worker_main function that coordinates
adapter creation, macro runner setup, and message forwarding.
"""
from __future__ import annotations

import asyncio
import pathlib
import traceback
import time
import queue
from pathlib import Path
from typing import Optional, List

from macros.parser import parse_macro
from macros.runner import MacroRunner
from adapter.factory import create_adapter

from .status import MacroStatus
from .broadcasting import broadcast_log_message, broadcast_status_update
from .command_handler import CommandHandler


class LogForwarder:
    """Forwards macro runner logs to WebSocket clients and handles status updates."""
    
    def __init__(self, runner_logs: asyncio.Queue, status: MacroStatus, log_queues: List[queue.Queue]):
        """Initialize the log forwarder.
        
        Args:
            runner_logs: Queue of log messages from the macro runner.
            status: MacroStatus instance for updating metrics.
            log_queues: List of queues for broadcasting messages.
        """
        self.runner_logs = runner_logs
        self.status = status
        self.log_queues = log_queues

    async def run_forwarding_loop(self) -> None:
        """Main log forwarding loop.
        
        Processes messages from the macro runner, updates status metrics,
        and forwards all messages to connected WebSocket clients.
        """
        while True:
            try:
                msg = await self.runner_logs.get()
            except asyncio.CancelledError:
                break
            
            try:
                self._process_status_message(msg)
            except Exception:
                # Don't let status processing errors break log forwarding
                pass
            
            # Forward all messages to clients
            self._broadcast_message(msg)

    def _process_status_message(self, msg: str) -> None:
        """Process status-related messages and update metrics.
        
        Args:
            msg: Log message from the macro runner.
        """
        if msg.startswith('=== iteration'):
            # Update iteration timing and check for alerts
            now = time.time()
            self.status.update_iteration_timing(now)
            
            # Check if an alert should be triggered
            if self.status.check_and_trigger_alert():
                broadcast_log_message(
                    self.log_queues, 
                    f'ALERT: Completed {self.status.iterations} iterations',
                    'info'
                )
                
        elif msg.startswith('Loaded macro:'):
            # Update macro name when a macro is loaded
            parts = msg.split(':', 1)[1].strip().split(' ', 1)
            self.status.name = parts[0]
            # Don't reset metrics when loading a new macro - keep accumulating
            
        elif (msg.startswith('Macro stopped') or 
              msg.startswith('Macro finished') or 
              msg.startswith('Executed macro once:') or 
              (msg.startswith('Run-once macro') and 'completed' in msg)):
            # Stop runtime tracking when macro completes
            self.status.stop_session()

    def _broadcast_message(self, msg: str) -> None:
        """Broadcast a message to all connected clients.
        
        Args:
            msg: Message to broadcast.
        """
        for log_queue in self.log_queues:
            try:
                log_queue.put_nowait(msg)
            except queue.Full:
                try:
                    log_queue.put(msg)
                except Exception:
                    pass
            except Exception:
                pass


async def worker_main(
    macro_file: Optional[str], 
    command_queue: queue.Queue, 
    log_queues: List[queue.Queue], 
    status: Optional[MacroStatus] = None, 
    preferred_adapter: Optional[str] = None
) -> None:
    """Main worker function that coordinates macro execution.
    
    This function sets up the adapter, macro runner, and handles the main
    execution loop including command processing and log forwarding.
    
    Args:
        macro_file: Optional path to initial macro file to load.
        command_queue: Queue for receiving commands from the web interface.
        log_queues: List of queues for broadcasting messages to clients.
        status: Optional existing MacroStatus instance to use.
        preferred_adapter: Optional adapter type preference.
    """
    try:
        broadcast_log_message(log_queues, 'worker: starting', 'info')

        # Load initial macro if provided
        commands = []
        if macro_file:
            commands = await _load_initial_macro(macro_file, log_queues)
        
        broadcast_log_message(log_queues, f'worker: parsed {len(commands)} commands', 'info')

        # Create and connect adapter
        broadcast_log_message(log_queues, 'worker: creating and connecting adapter (prioritizing Pico)', 'info')
        
        # Initialize status tracker
        macro_status = status if status is not None else MacroStatus()
        
        adapter = await create_adapter(preferred_adapter)
        adapter_name = adapter.__class__.__name__ if adapter else "No adapter"
        broadcast_log_message(log_queues, 'worker: adapter connected', 'success')
        broadcast_status_update(log_queues, macro_status, adapter_name)

        # Set up macro runner
        runner = MacroRunner(adapter)
        runner.set_commands(commands)
        runner_logs = runner.logs()

        # Set up log forwarding
        log_forwarder = LogForwarder(runner_logs, macro_status, log_queues)
        
        # Set up command handling
        command_handler = CommandHandler(runner, macro_status, log_queues, command_queue)

        # Start runner if we have commands
        await runner.start()
        # Only start runtime tracking if there are commands to run
        if commands and len(commands) > 0:
            macro_status.start_session()

        # Run main loops
        await asyncio.gather(
            log_forwarder.run_forwarding_loop(),
            command_handler.run_command_loop()
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f'Worker error: {e}\\n{tb}'
        broadcast_log_message(log_queues, error_msg, 'error')


async def _load_initial_macro(macro_file: str, log_queues: List[queue.Queue]) -> List:
    """Load the initial macro file if provided.
    
    Args:
        macro_file: Path to the macro file to load.
        log_queues: List of queues for broadcasting messages.
        
    Returns:
        List of parsed macro commands, or empty list if loading failed.
    """
    try:
        macro_path = Path(macro_file)
        if macro_path.exists():
            text = macro_path.read_text()
            return parse_macro(text)
        else:
            broadcast_log_message(log_queues, f'Initial macro not found: {macro_file}', 'warning')
            return []
    except Exception as e:
        broadcast_log_message(log_queues, f'Error reading initial macro {macro_file}: {e}', 'error')
        return []