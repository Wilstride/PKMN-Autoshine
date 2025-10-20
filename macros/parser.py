"""Macro parser and runner for adapter-based macros.

Supported commands (case-insensitive):
- PRESS <button>
- SLEEP <seconds>
- STICK <stick> <h> <v>   (h/v can be raw ints or normalized floats -1.0..1.0)

This module exposes:
- parse_macro(text) -> list of (cmd, args) tuples
- run_macro(adapter, commands, dry_run=False) -> runs commands against adapter

Usage example:
    from adapter.joycontrol import JoycontrolAdapter
    from macros.parser import parse_macro, run_macro

    text = open('macros/plza_travel_cafe.txt').read()
    commands = parse_macro(text)
    adapter = JoycontrolAdapter()
    await adapter.connect()
    await run_macro(adapter, commands)

The parser is intentionally small and forgiving. Unknown commands raise
ValueError when parsing.
"""

from __future__ import annotations

import re
import asyncio
from typing import List, Tuple, Any

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


async def run_macro(adapter, commands: List[Tuple[str, List[str]]], dry_run: bool = False):
    """Execute parsed macro commands against an adapter.

    adapter must implement:
    - press(button: Button, duration: float)
    - stick(stick: Stick, h: Union[int,float], v: Union[int,float])
    - Any awaitable send/connection methods already handled outside.
    """
    from adapter.base import Button, Stick

    for cmd, args in commands:
        if cmd == 'PRESS':
            if len(args) < 1:
                raise ValueError('PRESS requires a button name')
            btn_name = args[0].upper()
            # map common names to our Button enum where possible
            try:
                btn = Button[btn_name]
            except KeyError:
                # fallback: try lowercase value name
                try:
                    btn = Button(btn_name.lower())
                except Exception:
                    raise ValueError(f'Unknown button: {btn_name}')
            if dry_run:
                print(f'DRY PRESS {btn}')
            else:
                await adapter.press(btn)

        elif cmd == 'SLEEP':
            if len(args) < 1:
                raise ValueError('SLEEP requires seconds')
            sec = float(args[0])
            if dry_run:
                print(f'DRY SLEEP {sec}s')
            else:
                await asyncio.sleep(sec)

        elif cmd == 'STICK':
            if len(args) < 3:
                raise ValueError('STICK requires: <stick> <h> <v>')
            stick_name = args[0].upper()
            stick_enum = Stick.L_STICK if stick_name in ('L', 'L_STICK', 'LEFT') else Stick.R_STICK
            # parse h and v as float if they contain '.' or as int otherwise
            def parse_axis(x: str) -> Any:
                if '.' in x or x.startswith('-') and '.' in x:
                    return float(x)
                # attempt int
                try:
                    return int(x, 0)  # allow 0x... hex
                except Exception:
                    return float(x)

            h = parse_axis(args[1])
            v = parse_axis(args[2])

            if dry_run:
                print(f'DRY STICK {stick_enum} h={h} v={v}')
            else:
                await adapter.stick(stick_enum, h=h, v=v)

        else:
            raise ValueError(f'Unknown macro command: {cmd}')