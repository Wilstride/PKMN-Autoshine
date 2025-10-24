"""Command handling logic for the macro worker.

This module provides the CommandHandler class that processes commands
from the web interface and manages macro execution state.
"""
from __future__ import annotations

import asyncio
import pathlib
import queue
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from macros.runner import MacroRunner

from macros.parser import parse_macro
from .status import MacroStatus
from .broadcasting import broadcast_log_message


class CommandHandler:
    """Handles commands received from the web interface.
    
    This class processes various macro control commands including:
    - Execution control (pause, resume, stop, restart)
    - Macro loading and execution
    - Runtime configuration (alerts, metrics)
    - Adapter management
    """
    
    def __init__(
        self,
        runner: 'MacroRunner',
        status: MacroStatus,
        log_queues: List[queue.Queue],
        command_queue: queue.Queue
    ):
        """Initialize the command handler.
        
        Args:
            runner: MacroRunner instance for macro execution.
            status: MacroStatus instance for state tracking.
            log_queues: List of queues for broadcasting messages.
            command_queue: Queue for receiving commands.
        """
        self.runner = runner
        self.status = status
        self.log_queues = log_queues
        self.command_queue = command_queue
        self._macros_base_path = Path(pathlib.Path(__file__).parent.parent.parent.parent) / 'data' / 'macros'

    async def run_command_loop(self) -> None:
        """Main command processing loop.
        
        Continuously processes commands from the command queue until
        a 'stop' command is received.
        """
        loop = asyncio.get_event_loop()
        
        while True:
            cmd = await loop.run_in_executor(None, self.command_queue.get)
            broadcast_log_message(self.log_queues, f'worker: got cmd: {cmd}', 'info')
            
            try:
                should_stop = await self._process_command(cmd)
                if should_stop:
                    break
            except Exception as e:
                broadcast_log_message(self.log_queues, f'Error processing command {cmd}: {e}', 'error')

    async def _process_command(self, cmd: str) -> bool:
        """Process a single command.
        
        Args:
            cmd: Command string to process.
            
        Returns:
            True if the command loop should stop, False otherwise.
        """
        if cmd == 'pause':
            return await self._handle_pause()
        elif cmd == 'resume':
            return await self._handle_resume()
        elif cmd == 'restart':
            return await self._handle_restart()
        elif cmd == 'stop':
            return await self._handle_stop()
        elif cmd == 'force_stop':
            return await self._handle_force_stop()
        elif cmd == 'reset_metrics':
            return await self._handle_reset_metrics()
        elif isinstance(cmd, str) and cmd.startswith('adapter:'):
            return await self._handle_adapter_change(cmd)
        elif isinstance(cmd, str) and cmd.startswith('alert:'):
            return await self._handle_alert_config(cmd)
        elif isinstance(cmd, str) and cmd.startswith('run_once:'):
            return await self._handle_run_once(cmd)
        elif isinstance(cmd, str) and cmd.startswith('load:'):
            return await self._handle_load_macro(cmd)
        else:
            broadcast_log_message(self.log_queues, f'Unknown command: {cmd}', 'warning')
            return False

    async def _handle_pause(self) -> bool:
        """Handle pause command."""
        try:
            if self.runner.is_running():
                broadcast_log_message(self.log_queues, 'Pausing macro - will stop after current iteration completes...', 'warning')
                await self.runner.pause()
                self.status.pause_session()  # Pause runtime tracking
                broadcast_log_message(self.log_queues, 'Pause requested - macro will stop after current iteration.', 'info')
            else:
                broadcast_log_message(self.log_queues, 'No macro is currently running', 'warning')
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error pausing runner: {e}', 'error')
        return False

    async def _handle_resume(self) -> bool:
        """Handle resume command."""
        try:
            self.status.start_session()  # Resume runtime tracking
            self.runner.resume()
        except Exception:
            pass
        return False

    async def _handle_restart(self) -> bool:
        """Handle restart command."""
        try:
            await self.runner.stop()
            await self.runner.start()
            # Only start runtime tracking if runner has commands to run
            if hasattr(self.runner, '_commands') and self.runner._commands and len(self.runner._commands) > 0:
                self.status.start_session()
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error restarting: {e}', 'error')
        return False

    async def _handle_stop(self) -> bool:
        """Handle stop command."""
        await self.runner.stop()
        return True  # Signal to stop the command loop

    async def _handle_force_stop(self) -> bool:
        """Handle force stop command."""
        try:
            await self.runner.force_stop()
            self.status.stop_session()  # Stop runtime tracking completely
            broadcast_log_message(self.log_queues, 'Macro force stopped', 'warning')
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error force stopping: {e}', 'error')
        return False

    async def _handle_reset_metrics(self) -> bool:
        """Handle reset metrics command."""
        try:
            self.status.reset_all_metrics()
            broadcast_log_message(self.log_queues, 'Metrics reset to zero', 'success')
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error resetting metrics: {e}', 'error')
        return False

    async def _handle_adapter_change(self, cmd: str) -> bool:
        """Handle adapter change command."""
        # Handle adapter switching - this would require restarting the entire worker
        # For now, just log it - full implementation would require more complex worker management
        new_adapter = cmd.split(':', 1)[1] if ':' in cmd else None
        broadcast_log_message(self.log_queues, f'Adapter change requested: {new_adapter}. Please restart the system.', 'warning')
        return False

    async def _handle_alert_config(self, cmd: str) -> bool:
        """Handle alert configuration command."""
        try:
            alert_interval = int(cmd.split(':', 1)[1]) if ':' in cmd else 0
            self.status.alert_interval = alert_interval
            self.status.last_alert_iteration = self.status.iterations  # Reset alert counter
            msg = f'Alert interval set to {alert_interval} iterations' if alert_interval > 0 else 'Alerts disabled'
            broadcast_log_message(self.log_queues, msg, 'info')
        except ValueError:
            broadcast_log_message(self.log_queues, 'Invalid alert interval - must be a number', 'error')
        return False

    async def _handle_run_once(self, cmd: str) -> bool:
        """Handle run once command."""
        parts = cmd.split(':', 1)
        name = parts[1] if len(parts) > 1 else ''
        
        try:
            macro_path = self._macros_base_path / Path(name).name
            text = macro_path.read_text()
            new_commands = parse_macro(text)
            
            # Set single-run mode and prepare runner
            self.runner.set_commands(new_commands)
            self.runner.set_setup_commands(None)  # No setup for single runs
            
            # Stop any existing macro
            await self.runner.stop()
            
            # Update status
            try:
                self.status.name = name
                # Don't reset metrics for run_once - keep accumulating runtime
            except Exception:
                pass
            
            # Create a cancellable task for run_once
            async def run_once_task():
                await self.runner.run_once()
            
            run_once_task_ref = asyncio.create_task(run_once_task())
            self.runner._task = run_once_task_ref  # Store task reference for force_stop
            
            # Start runtime tracking for run_once
            self.status.start_session()
            
            try:
                await run_once_task_ref
                # Stop runtime when run_once completes successfully
                self.status.stop_session()
            except asyncio.CancelledError:
                broadcast_log_message(self.log_queues, f'Run-once macro {name} was force stopped', 'warning')
                # Also stop runtime when cancelled
                self.status.stop_session()
            finally:
                self.runner._task = None
            
            msg = f'Executed macro once: {name} ({len(new_commands)} commands)'
            broadcast_log_message(self.log_queues, msg, 'success')
            
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error running macro once {name}: {e}', 'error')
        
        return False

    async def _handle_load_macro(self, cmd: str) -> bool:
        """Handle load macro command."""
        parts = cmd.split(':', 2)  # Split into at most 3 parts: 'load', name, setup_name
        name = parts[1] if len(parts) > 1 else ''
        setup_name = parts[2] if len(parts) > 2 else None
        
        try:
            # Load main macro
            macro_path = self._macros_base_path / Path(name).name
            text = macro_path.read_text()
            new_commands = parse_macro(text)
            self.runner.set_commands(new_commands)
            
            # Load setup macro if specified
            setup_commands = None
            if setup_name:
                setup_path = self._macros_base_path / Path(setup_name).name
                setup_text = setup_path.read_text()
                setup_commands = parse_macro(setup_text)
                self.runner.set_setup_commands(setup_commands)
            else:
                self.runner.set_setup_commands(None)
            
            await self.runner.stop()
            await self.runner.start()
            
            # Only start runtime tracking if commands were actually loaded
            if new_commands and len(new_commands) > 0:
                self.status.start_session()
            
            try:
                self.status.name = name
                # Don't reset metrics when loading - keep accumulating runtime
            except Exception:
                pass
            
            # Log the loaded macros
            if setup_name:
                msg = f'Loaded macros: setup={setup_name} ({len(setup_commands)} commands), main={name} ({len(new_commands)} commands)'
            else:
                msg = f'Loaded macro: {name} ({len(new_commands)} commands)'
            
            broadcast_log_message(self.log_queues, msg, 'success')
            
        except Exception as e:
            broadcast_log_message(self.log_queues, f'Error loading macro {name}: {e}', 'error')
        
        return False