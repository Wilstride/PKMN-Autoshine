"""Core command execution logic for macro running.

This module provides the main run_commands function that executes
a sequence of macro commands with proper event handling and logging.
"""
from __future__ import annotations

from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Queue, Event

from .commands import CommandExecutor


async def run_commands(
    adapter,
    commands: List[Tuple[str, List[str]]],
    *,
    log_queue: Optional['Queue'] = None,
    pause_event: Optional['Event'] = None,
    stop_event: Optional['Event'] = None
) -> None:
    """Execute a sequence of macro commands.
    
    This function processes commands sequentially, respecting pause and stop
    events for interactive control. Each command is executed through the
    CommandExecutor with proper error handling and logging.
    
    Args:
        adapter: Hardware adapter for executing commands.
        commands: List of (command_name, arguments) tuples to execute.
        log_queue: Optional queue for logging command execution.
        pause_event: Optional event for pausing execution between commands.
        stop_event: Optional event for stopping execution immediately.
        
    Raises:
        ValueError: If an unknown command is encountered.
    """
    # Check if adapter supports batch commands for optimization
    if hasattr(adapter, 'send_batch_commands'):
        await _run_commands_optimized(adapter, commands, log_queue, pause_event, stop_event)
    else:
        await _run_commands_sequential(adapter, commands, log_queue, pause_event, stop_event)


async def _run_commands_sequential(
    adapter,
    commands: List[Tuple[str, List[str]]],
    log_queue: Optional['Queue'] = None,
    pause_event: Optional['Event'] = None,
    stop_event: Optional['Event'] = None
) -> None:
    """Execute commands one by one (original implementation)."""
    executor = CommandExecutor(adapter, log_queue)
    
    for cmd, args in commands:
        # Check if stop was requested before processing each command
        if stop_event is not None and stop_event.is_set():
            executor.log('stopped')
            return
        
        # Wait for resume if paused
        if pause_event is not None:
            await pause_event.wait()
        
        # Execute the command
        try:
            await _execute_single_command(executor, cmd, args, stop_event, pause_event)
        except ValueError as e:
            # Re-raise command errors with context
            raise ValueError(f'Error executing {cmd} command: {e}')


async def _run_commands_optimized(
    adapter,
    commands: List[Tuple[str, List[str]]],
    log_queue: Optional['Queue'] = None,
    pause_event: Optional['Event'] = None,
    stop_event: Optional['Event'] = None
) -> None:
    """Execute commands with batching optimization for supported adapters."""
    executor = CommandExecutor(adapter, log_queue)
    
    # Group non-SLEEP commands into batches
    batch = []
    
    for cmd, args in commands:
        # Check if stop was requested
        if stop_event is not None and stop_event.is_set():
            executor.log('stopped')
            return
        
        # Wait for resume if paused
        if pause_event is not None:
            await pause_event.wait()
        
        if cmd == 'SLEEP':
            # Send any pending batch before processing SLEEP
            if batch:
                await adapter.send_batch_commands(batch)
                executor.log(f'Sent batch of {len(batch)} commands')
                batch = []
            
            # Execute SLEEP individually (it needs special handling)
            try:
                await _execute_single_command(executor, cmd, args, stop_event, pause_event)
            except ValueError as e:
                raise ValueError(f'Error executing {cmd} command: {e}')
        else:
            # Add non-SLEEP commands to batch
            try:
                batch_cmd = _convert_to_batch_command(cmd, args)
                batch.append(batch_cmd)
                executor.log(f'{cmd} {" ".join(args)}')
            except ValueError as e:
                raise ValueError(f'Error converting {cmd} command: {e}')
    
    # Send any remaining batched commands
    if batch:
        await adapter.send_batch_commands(batch)
        executor.log(f'Sent final batch of {len(batch)} commands')


def _convert_to_batch_command(cmd: str, args: List[str]) -> str:
    """Convert a command and arguments to batch command format."""
    if cmd in ['PRESS', 'HOLD', 'RELEASE', 'STICK']:
        return f"{cmd} {' '.join(args)}"
    elif cmd == 'CENTER_STICKS':
        return "CENTER_STICKS"
    elif cmd == 'RELEASE_ALL':
        return "RELEASE_ALL"
    else:
        raise ValueError(f'Unknown command for batching: {cmd}')


async def _execute_single_command(
    executor: CommandExecutor,
    cmd: str,
    args: List[str],
    stop_event: Optional['Event'] = None,
    pause_event: Optional['Event'] = None
) -> None:
    """Execute a single macro command.
    
    Args:
        executor: CommandExecutor instance.
        cmd: Command name (PRESS, HOLD, RELEASE, SLEEP, STICK).
        args: Command arguments.
        stop_event: Optional event for stopping execution.
        pause_event: Optional event for pausing execution.
        
    Raises:
        ValueError: If command is unknown or invalid.
    """
    if cmd == 'PRESS':
        await executor.execute_press_command(args)
    elif cmd == 'HOLD':
        await executor.execute_hold_command(args)
    elif cmd == 'RELEASE':
        await executor.execute_release_command(args)
    elif cmd == 'SLEEP':
        await executor.execute_sleep_command(args, stop_event, pause_event)
    elif cmd == 'STICK':
        await executor.execute_stick_command(args)
    else:
        raise ValueError(f'Unknown macro command: {cmd}')


class CommandSequenceRunner:
    """Advanced command sequence runner with enhanced features.
    
    This class provides a more sophisticated interface for running command
    sequences with features like progress tracking, error recovery, and
    detailed execution metrics.
    """
    
    def __init__(self, adapter, log_queue: Optional['Queue'] = None):
        """Initialize the sequence runner.
        
        Args:
            adapter: Hardware adapter for executing commands.
            log_queue: Optional queue for logging execution details.
        """
        self.adapter = adapter
        self.log_queue = log_queue
        self.executor = CommandExecutor(adapter, log_queue)
        self.commands_executed = 0
        self.total_commands = 0

    async def run_sequence(
        self,
        commands: List[Tuple[str, List[str]]],
        *,
        pause_event: Optional['Event'] = None,
        stop_event: Optional['Event'] = None,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Run a command sequence with progress tracking.
        
        Args:
            commands: List of commands to execute.
            pause_event: Optional event for pausing execution.
            stop_event: Optional event for stopping execution.
            progress_callback: Optional callback for progress updates.
            
        Returns:
            True if all commands executed successfully, False if stopped.
        """
        self.total_commands = len(commands)
        self.commands_executed = 0
        
        for cmd, args in commands:
            # Check for stop request
            if stop_event is not None and stop_event.is_set():
                self._log('Sequence stopped by user request')
                return False
            
            # Wait for resume if paused
            if pause_event is not None:
                await pause_event.wait()
            
            try:
                await _execute_single_command(self.executor, cmd, args, stop_event, pause_event)
                self.commands_executed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(self.commands_executed, self.total_commands)
                    
            except Exception as e:
                self._log(f'Error executing command {cmd}: {e}')
                raise
        
        return True

    def get_progress(self) -> tuple:
        """Get current execution progress.
        
        Returns:
            Tuple of (commands_executed, total_commands).
        """
        return self.commands_executed, self.total_commands

    def _log(self, message: str) -> None:
        """Log a message using the executor's logging mechanism."""
        self.executor.log(message)