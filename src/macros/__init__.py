"""macros package exposing parser and runner modules."""

from .parser import parse_macro
from .runner import run_macro, run_commands, MacroRunner

__all__ = ['parse_macro', 'run_macro', 'run_commands', 'MacroRunner']
