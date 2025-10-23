"""Macro text parser.

Provides parse_macro(text) -> list[(cmd, args, device_id)].
Supports device targeting syntax: device_id:COMMAND args
"""
from __future__ import annotations

import re
from typing import List, Tuple, Optional

COMMAND_RE = re.compile(r"^(?:(?P<device>\w+):)?(?P<cmd>\w+)\s*(?P<args>.*)$")


def parse_macro(text: str) -> List[Tuple[str, List[str], Optional[str]]]:
    """Parse macro text into a list of (command, args, device_id) tuples.

    Lines starting with '#' or empty lines are ignored. Commands and args are
    split on whitespace. Device targeting is supported with syntax: device_id:COMMAND args
    
    Examples:
        PRESS A          -> ('PRESS', ['A'], None)              # All devices
        pico_0:PRESS A   -> ('PRESS', ['A'], 'pico_0')         # Specific device
        all:PRESS A      -> ('PRESS', ['A'], None)             # Explicit all devices
        *:PRESS A        -> ('PRESS', ['A'], None)             # Explicit all devices
    
    Returns commands as uppercase strings and raw arg strings preserved.
    """
    commands = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = COMMAND_RE.match(line)
        if not m:
            raise ValueError(f"Invalid macro line: {line}")
        
        device = m.group('device')
        cmd = m.group('cmd').upper()
        args = m.group('args').strip()
        
        # Handle special device targeting keywords
        if device in ('all', '*'):
            device = None
        
        if args:
            parts = args.split()
        else:
            parts = []
        
        commands.append((cmd, parts, device))
    return commands
