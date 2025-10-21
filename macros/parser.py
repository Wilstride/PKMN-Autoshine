"""Macro text parser.

Provides parse_macro(text) -> list[(cmd, args)].
"""
from __future__ import annotations

import re
from typing import List, Tuple

COMMAND_RE = re.compile(r"^(?P<cmd>\w+)\s*(?P<args>.*)$")


def parse_macro(text: str) -> List[Tuple[str, List[str]]]:
    """Parse macro text into a list of (command, args) tuples.

    Lines starting with '#' or empty lines are ignored. Commands and args are
    split on whitespace. Returns commands as uppercase strings and raw arg
    strings preserved.
    """
    commands = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = COMMAND_RE.match(line)
        if not m:
            raise ValueError(f"Invalid macro line: {line}")
        cmd = m.group('cmd').upper()
        args = m.group('args').strip()
        if args:
            parts = args.split()
        else:
            parts = []
        commands.append((cmd, parts))
    return commands
