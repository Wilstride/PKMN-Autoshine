"""Individual macro command implementations.

This module provides implementations for all supported macro commands
including PRESS, SLEEP, and STICK with proper validation and error handling.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Queue, Event

from adapter.base import Button, Stick


class CommandExecutor:
    """Executes individual macro commands with proper validation and logging."""
    
    def __init__(self, adapter, log_queue: Optional['Queue'] = None):
        """Initialize the command executor.
        
        Args:
            adapter: Adapter instance for hardware communication.
            log_queue: Optional queue for logging command execution.
        """
        self.adapter = adapter
        self.log_queue = log_queue

    def log(self, message: str) -> None:
        """Log a message to the queue or print if no queue available.
        
        Args:
            message: Message to log.
        """
        if self.log_queue is None:
            print(message)
        else:
            try:
                self.log_queue.put_nowait(message)
            except Exception:
                # Silently ignore queue errors
                pass

    async def execute_press_command(self, args: List[str]) -> None:
        """Execute a PRESS command to press a button.
        
        Args:
            args: Command arguments, first should be button name.
            
        Raises:
            ValueError: If button name is invalid or missing.
        """
        if not args:
            raise ValueError('PRESS command requires a button name')
        
        button_name = args[0].upper()
        button = self._parse_button(button_name)
        
        self.log(f'PRESS {button.name}')
        await self.adapter.press(button)

    async def execute_hold_command(self, args: List[str]) -> None:
        """Execute a HOLD command to hold a button down.
        
        Args:
            args: Command arguments, first should be button name.
            
        Raises:
            ValueError: If button name is invalid or missing.
        """
        if not args:
            raise ValueError('HOLD command requires a button name')
        
        button_name = args[0].upper()
        button = self._parse_button(button_name)
        
        self.log(f'HOLD {button.name}')
        await self.adapter.hold(button)

    async def execute_release_command(self, args: List[str]) -> None:
        """Execute a RELEASE command to release a button.
        
        Args:
            args: Command arguments, first should be button name.
            
        Raises:
            ValueError: If button name is invalid or missing.
        """
        if not args:
            raise ValueError('RELEASE command requires a button name')
        
        button_name = args[0].upper()
        button = self._parse_button(button_name)
        
        self.log(f'RELEASE {button.name}')
        await self.adapter.release(button)

    async def execute_sleep_command(
        self, 
        args: List[str], 
        stop_event: Optional['Event'] = None,
        pause_event: Optional['Event'] = None
    ) -> None:
        """Execute a SLEEP command with interruptible sleeping.
        
        Args:
            args: Command arguments, first should be sleep duration in seconds.
            stop_event: Optional event to interrupt sleep if stop is requested.
            pause_event: Optional event to pause/resume sleep.
            
        Raises:
            ValueError: If sleep duration is invalid or missing.
        """
        if not args:
            raise ValueError('SLEEP command requires duration in seconds')
        
        try:
            duration = float(args[0])
        except ValueError:
            raise ValueError(f'Invalid sleep duration: {args[0]}')
        
        if duration < 0:
            raise ValueError('Sleep duration cannot be negative')
        
        self.log(f'SLEEP {duration}s')
        
        # Use interruptible sleep for better responsiveness
        await self._interruptible_sleep(duration, stop_event, pause_event)

    async def execute_stick_command(self, args: List[str]) -> None:
        """Execute a STICK command to move an analog stick.
        
        Args:
            args: Command arguments [stick_name, horizontal, vertical].
            
        Raises:
            ValueError: If stick arguments are invalid or missing.
        """
        if len(args) < 3:
            raise ValueError('STICK command requires: <stick> <horizontal> <vertical>')
        
        stick_name = args[0].upper()
        stick = self._parse_stick(stick_name)
        
        try:
            horizontal = self._parse_axis_value(args[1])
            vertical = self._parse_axis_value(args[2])
        except ValueError as e:
            raise ValueError(f'Invalid stick coordinates: {e}')
        
        self.log(f'STICK {stick.name} h={horizontal} v={vertical}')
        await self.adapter.stick(stick, h=horizontal, v=vertical)

    def _parse_button(self, button_name: str) -> Button:
        """Parse button name into Button enum.
        
        Args:
            button_name: Name of the button (case insensitive).
            
        Returns:
            Button enum value.
            
        Raises:
            ValueError: If button name is not recognized.
        """
        try:
            return Button[button_name]
        except KeyError:
            try:
                return Button(button_name.lower())
            except Exception:
                available_buttons = ', '.join(button.name for button in Button)
                raise ValueError(f'Unknown button: {button_name}. Available: {available_buttons}')

    def _parse_stick(self, stick_name: str) -> Stick:
        """Parse stick name into Stick enum.
        
        Args:
            stick_name: Name of the stick.
            
        Returns:
            Stick enum value.
        """
        if stick_name in ('L', 'L_STICK', 'LEFT'):
            return Stick.L_STICK
        elif stick_name in ('R', 'R_STICK', 'RIGHT'):
            return Stick.R_STICK
        else:
            raise ValueError(f'Unknown stick: {stick_name}. Use L/LEFT or R/RIGHT')

    def _parse_axis_value(self, value_str: str) -> Union[int, float]:
        """Parse axis value from string to appropriate numeric type.
        
        Args:
            value_str: String representation of axis value.
            
        Returns:
            Parsed numeric value (int or float).
            
        Raises:
            ValueError: If value cannot be parsed.
        """
        if '.' in value_str or (value_str.startswith('-') and '.' in value_str):
            return float(value_str)
        
        try:
            # Try parsing as integer first (supports hex with 0x prefix)
            return int(value_str, 0)
        except ValueError:
            # Fall back to float parsing
            return float(value_str)

    async def _interruptible_sleep(
        self, 
        duration: float, 
        stop_event: Optional['Event'] = None,
        pause_event: Optional['Event'] = None
    ) -> None:
        """Sleep for the specified duration with interruption support.
        
        Args:
            duration: Sleep duration in seconds.
            stop_event: Event to interrupt sleep if stop is requested.
            pause_event: Event to pause/resume sleep.
        """
        remaining = duration
        interval = 0.1  # Check for interruption every 100ms
        
        while remaining > 0:
            # Check if stop was requested
            if stop_event is not None and stop_event.is_set():
                self.log('stopped during sleep')
                return
            
            # Wait for resume if paused
            if pause_event is not None:
                await pause_event.wait()
            
            # Sleep for a small interval or remaining time
            sleep_time = min(interval, remaining)
            await asyncio.sleep(sleep_time)
            remaining -= sleep_time


# Legacy function for backward compatibility
async def run_macro(adapter, commands: List[tuple], dry_run: bool = False) -> None:
    """Legacy function for running macro commands.
    
    DEPRECATED: Use CommandExecutor class instead.
    
    Args:
        adapter: Adapter instance.
        commands: List of (command, args) tuples.
        dry_run: If True, only print commands without executing.
    """
    executor = CommandExecutor(adapter)
    
    for cmd, args in commands:
        if dry_run:
            if cmd == 'PRESS':
                print(f'DRY PRESS {args[0] if args else "UNKNOWN"}')
            elif cmd == 'HOLD':
                print(f'DRY HOLD {args[0] if args else "UNKNOWN"}')
            elif cmd == 'RELEASE':
                print(f'DRY RELEASE {args[0] if args else "UNKNOWN"}')
            elif cmd == 'SLEEP':
                print(f'DRY SLEEP {args[0] if args else "0"}s')
            elif cmd == 'STICK':
                stick = args[0] if len(args) > 0 else 'L'
                h = args[1] if len(args) > 1 else '0'
                v = args[2] if len(args) > 2 else '0'
                print(f'DRY STICK {stick} h={h} v={v}')
            else:
                print(f'DRY UNKNOWN: {cmd} {args}')
        else:
            if cmd == 'PRESS':
                await executor.execute_press_command(args)
            elif cmd == 'HOLD':
                await executor.execute_hold_command(args)
            elif cmd == 'RELEASE':
                await executor.execute_release_command(args)
            elif cmd == 'SLEEP':
                await executor.execute_sleep_command(args)
            elif cmd == 'STICK':
                await executor.execute_stick_command(args)
            else:
                raise ValueError(f'Unknown macro command: {cmd}')