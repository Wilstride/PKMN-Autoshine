"""Macro execution package with modular command processing.

This package provides a modular approach to macro execution with clear
separation of concerns between command implementation, execution logic,
and session management.

Components:
- commands: Individual command implementations (HOLD, RELEASE, SLEEP, STICK)
- runner_core: Core command sequence execution logic
- session: MacroRunner class for session management

Public API:
- MacroRunner: Main class for macro execution sessions
- run_commands: Execute a sequence of commands
- CommandExecutor: Execute individual commands
- run_macro: Legacy function for backward compatibility
"""
from __future__ import annotations

# Import main API components
from .session import MacroRunner
from .runner_core import run_commands, CommandSequenceRunner
from .commands import CommandExecutor, run_macro

__all__ = [
    'MacroRunner',
    'run_commands', 
    'CommandSequenceRunner',
    'CommandExecutor',
    'run_macro'  # Legacy compatibility
]