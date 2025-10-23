"""Macro text parser.

Provides parse_macro(text) -> list[(cmd, args)] with loop support.
"""
from __future__ import annotations

import re
from typing import List, Tuple, Union

COMMAND_RE = re.compile(r"^(?P<cmd>\w+)\s*(?P<args>.*)$")

# Command can be either a simple command tuple or a loop structure
Command = Union[Tuple[str, List[str]], Tuple[str, List[str], List['Command']]]


def parse_macro(text: str) -> List[Tuple[str, List[str]]]:
    """Parse macro text into a flattened list of commands with loop support.

    Lines starting with '#' or empty lines are ignored. Commands and args are
    split on whitespace. Returns commands as uppercase strings and raw arg
    strings preserved.
    
    Loop syntax:
    LOOP <count>
        ... commands ...
    ENDLOOP
    
    Loops are automatically expanded into repeated command sequences.
    For structured parsing, use parse_macro_structured().
    
    Returns: List of (cmd, args) tuples
    """
    structured_commands = parse_macro_structured(text)
    return flatten_commands(structured_commands)


def parse_macro_structured(text: str) -> List[Command]:
    """Parse macro text into structured commands preserving loop structure.
    
    Returns:
    - Simple commands: (cmd, args)  
    - Loop commands: ('LOOP', [count], [nested_commands])
    """
    lines = text.splitlines()
    commands, _ = _parse_commands(lines, 0)
    return commands


def _parse_commands(lines: List[str], start_index: int, in_loop: bool = False) -> Tuple[List[Command], int]:
    """Parse commands starting from start_index, return (commands, next_index)."""
    commands = []
    i = start_index
    
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
            
        # Parse command
        m = COMMAND_RE.match(line)
        if not m:
            raise ValueError(f"Invalid macro line: {line}")
            
        cmd = m.group('cmd').upper()
        args = m.group('args').strip()
        if args:
            parts = args.split()
        else:
            parts = []
        
        # Handle loop start
        if cmd == 'LOOP':
            if not parts or not parts[0].isdigit():
                raise ValueError(f"LOOP command requires a numeric count: {line}")
            count = int(parts[0])
            if count <= 0:
                raise ValueError(f"LOOP count must be positive: {line}")
            
            # Parse loop body
            loop_body, i = _parse_commands(lines, i, in_loop=True)
            commands.append(('LOOP', [str(count)], loop_body))
            
        # Handle loop end
        elif cmd == 'ENDLOOP':
            if not in_loop:
                raise ValueError("ENDLOOP found without matching LOOP")
            # Return to caller (end of current loop/block)
            return commands, i
            
        # Regular command
        else:
            commands.append((cmd, parts))
    
    # If we're in a loop and reach end of file, that's an error
    if in_loop:
        raise ValueError("LOOP command is missing matching ENDLOOP")
    
    return commands, i


def flatten_commands(commands: List[Command]) -> List[Tuple[str, List[str]]]:
    """Flatten loop structures into a simple command list for execution.
    
    This expands LOOP commands into repeated sequences of their contents.
    Used for backward compatibility with existing execution code.
    """
    result = []
    
    for cmd in commands:
        if len(cmd) == 3 and cmd[0] == 'LOOP':  # Loop command
            _, count_args, loop_body = cmd
            count = int(count_args[0])
            
            # Repeat the loop body 'count' times
            for _ in range(count):
                result.extend(flatten_commands(loop_body))
        else:
            # Regular command
            result.append(cmd)
    
    return result
