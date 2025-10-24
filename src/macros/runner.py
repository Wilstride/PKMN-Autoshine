"""Legacy macro runner module - imports from refactored execution package.

This module maintains backward compatibility by re-exporting the public API
from the refactored execution package. New code should import directly from
the execution package modules.

DEPRECATED: This module will be removed in a future version.
Use: from macros.execution import MacroRunner, run_commands
"""
from __future__ import annotations

# Import everything from the new execution package
from .execution import *

# Specific imports for explicit compatibility
from .execution.session import MacroRunner
from .execution.runner_core import run_commands
from .execution.commands import run_macro

__all__ = [
    'MacroRunner',
    'run_commands',
    'run_macro'
]
