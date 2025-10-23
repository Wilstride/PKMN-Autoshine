"""Compatibility wrapper for legacy imports.

Historically this repository exposed parse_macro and MacroRunner in
`macro_parser.py`. The implementation has been split into smaller modules
under `macros/`. This file re-exports the public API so existing imports
continue to work.
"""

from macros.parser import parse_macro
from macros.runner import run_macro, run_commands, MacroRunner

__all__ = [
    'parse_macro',
    'run_macro',
    'run_commands',
    'MacroRunner',
]