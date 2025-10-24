"""Macro execution session management.

This module provides the MacroRunner class that orchestrates macro execution
sessions with proper lifecycle management, event handling, and state tracking.
"""
from __future__ import annotations

import asyncio
from typing import List, Tuple, Optional, TYPE_CHECKING
from asyncio import Queue, Event

if TYPE_CHECKING:
    pass

from .runner_core import run_commands


class MacroRunner:
    """Orchestrates macro execution sessions with lifecycle management.
    
    This class manages the execution of macro sequences including:
    - Setup command execution before main loop
    - Continuous macro looping with iteration tracking
    - Graceful pause/resume functionality
    - Single-run execution mode
    - Event-driven state management
    """
    
    def __init__(self, adapter):
        """Initialize the macro runner.
        
        Args:
            adapter: Hardware adapter for executing commands.
        """
        self.adapter = adapter
        self._task: Optional[asyncio.Task] = None
        self._commands: Optional[List[Tuple[str, List[str]]]] = None
        self._setup_commands: Optional[List[Tuple[str, List[str]]]] = None
        self.log_queue: Optional[Queue] = None
        
        # Event management for execution control
        self._pause_event = Event()
        self._pause_event.set()  # Start unpaused
        self._stop_event = Event()
        self._graceful_pause_event = Event()
        self._graceful_pause_event.set()  # Start unpaused

    def set_commands(self, commands: List[Tuple[str, List[str]]]) -> None:
        """Set the main macro commands to execute.
        
        Args:
            commands: List of (command_name, arguments) tuples.
        """
        self._commands = commands

    def set_setup_commands(self, setup_commands: Optional[List[Tuple[str, List[str]]]]) -> None:
        """Set commands to run once before the main macro loop starts.
        
        Args:
            setup_commands: Optional list of setup commands, or None to disable.
        """
        self._setup_commands = setup_commands

    def logs(self) -> Queue:
        """Get the log queue for this runner.
        
        Returns:
            Queue instance for receiving log messages.
        """
        if self.log_queue is None:
            self.log_queue = Queue()
        return self.log_queue

    def is_running(self) -> bool:
        """Check if the macro runner is currently executing.
        
        Returns:
            True if a macro execution task is active.
        """
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start macro execution in continuous loop mode.
        
        Raises:
            RuntimeError: If no commands are set or runner is already running.
        """
        if self._commands is None:
            raise RuntimeError('No commands set')
        
        if isinstance(self._commands, list) and len(self._commands) == 0:
            self._log('MacroRunner: no commands to run')
            return
        
        if self.is_running():
            return
        
        # Reset execution state
        self._stop_event.clear()
        self._pause_event.set()
        self._graceful_pause_event.set()

        # Start the main execution loop
        self._task = asyncio.create_task(self._execution_loop())

    async def stop(self) -> None:
        """Stop macro execution gracefully.
        
        This method signals the execution loop to stop and waits for it to
        complete, then cleans up the adapter state.
        """
        if not self.is_running():
            return
        
        self._log('=== stopping macro ===')
        
        # Signal stop and unblock any pauses
        self._stop_event.set()
        self._pause_event.set()
        self._graceful_pause_event.set()
        
        try:
            await self._task
        finally:
            self._task = None
        
        # Clean up adapter state
        await self._cleanup_adapter_state()

    async def pause(self) -> None:
        """Gracefully pause after current iteration completes.
        
        This method requests a pause that will take effect after the current
        iteration finishes, ensuring commands are not interrupted mid-execution.
        """
        if self.is_running():
            self._graceful_pause_event.clear()
            self._log('=== graceful pause requested ===')

    def resume(self) -> None:
        """Resume execution from a paused state.
        
        This method resumes both immediate pauses and graceful pauses.
        """
        self._pause_event.set()
        self._graceful_pause_event.set()

    async def force_stop(self) -> None:
        """Immediately stop macro execution regardless of current state.
        
        This method forcibly cancels the execution task and cleans up state
        without waiting for graceful completion.
        """
        if not self.is_running():
            return
        
        self._log('=== force stop requested ===')
        
        # Set all events to stop execution immediately
        self._stop_event.set()
        self._pause_event.set()
        self._graceful_pause_event.set()
        
        # Cancel the task if it's still running
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        
        self._task = None
        await self._cleanup_adapter_state()

    async def run_once(self) -> None:
        """Run the macro commands exactly once without looping.
        
        This method executes the main commands once and then stops, without
        entering the continuous loop mode.
        
        Raises:
            RuntimeError: If no commands are set.
        """
        if self._commands is None:
            raise RuntimeError('No commands set')
        
        if isinstance(self._commands, list) and len(self._commands) == 0:
            self._log('MacroRunner: no commands to run')
            return

        # Ensure events are in correct state for single run
        self._pause_event.set()
        self._graceful_pause_event.set()
        self._stop_event.clear()

        try:
            self._log('=== iteration 1 start ===')  # For metrics tracking
            self._log('=== running macro once ===')
            
            # Execute commands once with stop event support
            await run_commands(
                self.adapter, 
                self._commands, 
                log_queue=self.log_queue,
                stop_event=self._stop_event
            )
            
            self._log('=== macro run completed ===')
            
        except Exception as e:
            self._log(f'Error during single macro run: {e}')
            raise
        finally:
            await self._cleanup_adapter_state()

    async def _execution_loop(self) -> None:
        """Main execution loop for continuous macro running.
        
        This method handles setup command execution followed by the main
        macro loop with iteration tracking and graceful pause support.
        """
        try:
            # Execute setup commands if configured
            await self._execute_setup_commands()
            
            # Main macro loop
            iteration = 0
            while not self._stop_event.is_set():
                iteration += 1
                
                try:
                    self._log(f'=== iteration {iteration} start ===')
                    
                    # Execute main commands (without pause_event for graceful handling)
                    await run_commands(
                        self.adapter, 
                        self._commands, 
                        log_queue=self.log_queue,
                        stop_event=self._stop_event
                    )
                    
                    # Check for graceful pause after iteration completes
                    await self._handle_graceful_pause(iteration)
                    
                except Exception as e:
                    self._log(f'Error during macro run: {e}')
                
                # Small delay between iterations
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self._log(f'Error in execution loop: {e}')

    async def _execute_setup_commands(self) -> None:
        """Execute setup commands if configured.
        
        Raises:
            Exception: If setup command execution fails, preventing main loop.
        """
        if self._setup_commands is not None and len(self._setup_commands) > 0:
            try:
                self._log('=== running setup macro ===')
                await run_commands(
                    self.adapter, 
                    self._setup_commands, 
                    log_queue=self.log_queue,
                    pause_event=self._pause_event,
                    stop_event=self._stop_event
                )
                self._log('=== setup macro completed ===')
            except Exception as e:
                self._log(f'Error during setup macro: {e}')
                # Don't continue to main loop if setup fails
                raise

    async def _handle_graceful_pause(self, iteration: int) -> None:
        """Handle graceful pause logic after iteration completion.
        
        Args:
            iteration: Current iteration number for logging.
        """
        if not self._graceful_pause_event.is_set():
            self._log(f'=== pausing after iteration {iteration} ===')
            
            # Release controls before pausing
            await self._cleanup_adapter_state()
            
            # Wait for resume
            await self._graceful_pause_event.wait()

    async def _cleanup_adapter_state(self) -> None:
        """Clean up adapter state by releasing all controls."""
        try:
            await self.adapter.release_all_buttons()
        except Exception:
            pass
        
        try:
            await self.adapter.center_sticks()
        except Exception:
            pass

    def _log(self, message: str) -> None:
        """Log a message to the log queue or print if no queue available.
        
        Args:
            message: Message to log.
        """
        if self.log_queue is not None:
            try:
                self.log_queue.put_nowait(message)
            except Exception:
                pass
        else:
            print(message)