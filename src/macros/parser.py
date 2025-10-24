"""Macro text parser for Nintendo Switch controller command sequences.

This module provides parsing functionality for macro text files containing
controller commands and loop structures. It supports both flattened command
lists for simple execution and structured parsing that preserves loop
hierarchy for analysis.

The parser handles:
    - Basic controller commands (PRESS, STICK, WAIT, etc.)
    - Loop structures with LOOP/ENDLOOP blocks
    - Comments (lines starting with '#')
    - Whitespace and empty line handling

Example:
    Basic parsing::
    
        commands = parse_macro('''
            # Simple macro example
            PRESS A 0.1
            WAIT 1.0
            LOOP 3
                PRESS B 0.1
                WAIT 0.5
            ENDLOOP
        ''')
        
    Structured parsing::
    
        structured = parse_macro_structured(text)
        # Preserves loop hierarchy for analysis

Typical usage:
    Most consumers want parse_macro() for flattened execution sequences.
    Use parse_macro_structured() when you need to analyze loop structure.
"""
from __future__ import annotations

import re
from typing import List, Tuple, Union

# Regular expression for parsing command lines
COMMAND_RE = re.compile(r"^(?P<cmd>\w+)\s*(?P<args>.*)$")

# Type alias for command structures
# Commands can be either simple tuples or loop structures with nested commands
Command = Union[
    Tuple[str, List[str]],                    # Simple command: (cmd, args)
    Tuple[str, List[str], List['Command']]    # Loop command: (cmd, args, nested_commands)
]


def parse_macro(text: str) -> List[Tuple[str, List[str]]]:
    """Parse macro text into a flattened list of executable commands.

    Processes macro text containing controller commands and loop structures,
    expanding all loops into their constituent commands for direct execution.
    Comments and empty lines are automatically filtered out.

    Args:
        text: Raw macro text containing commands and loop structures
        
    Returns:
        List of command tuples in the format (command_name, arguments_list).
        Commands are normalized to uppercase, arguments remain as strings.
        
    Example:
        Parse a macro with loops::
        
            commands = parse_macro('''
                # Move character
                PRESS A 0.1
                LOOP 3
                    PRESS UP 0.1
                    WAIT 0.5
                ENDLOOP
                PRESS B 0.1
            ''')
            # Returns: [('PRESS', ['A', '0.1']), ('PRESS', ['UP', '0.1']), 
            #           ('WAIT', ['0.5']), ('PRESS', ['UP', '0.1']), ...]
            
    Note:
        For analyzing loop structure without flattening, use parse_macro_structured().
        All LOOP blocks are expanded, so a LOOP 100 will generate 100 copies
        of the contained commands.
    """
    structured_commands = parse_macro_structured(text)
    return flatten_commands(structured_commands)


def parse_macro_structured(text: str) -> List[Command]:
    """Parse macro text preserving hierarchical loop structure.
    
    Processes macro text while maintaining the original loop structure for
    analysis or specialized processing that needs loop boundaries.
    
    Args:
        text: Raw macro text containing commands and loop structures
        
    Returns:
        List of Command objects where:
        - Simple commands: (command_name, arguments_list)
        - Loop commands: ('LOOP', [count_string], nested_commands_list)
        
    Example:
        Parse with structure preservation::
        
            structured = parse_macro_structured('''
                PRESS A 0.1
                LOOP 3
                    PRESS B 0.1
                ENDLOOP
            ''')
            # Returns: [('PRESS', ['A', '0.1']), 
            #           ('LOOP', ['3'], [('PRESS', ['B', '0.1'])])]
            
    Note:
        This is primarily useful for macro analysis tools. For execution,
        use parse_macro() which flattens the structure.
    """
    lines = text.splitlines()
    commands, _ = _parse_commands(lines, 0)
    return commands


def _parse_commands(
    lines: List[str], 
    start_index: int, 
    in_loop: bool = False
) -> Tuple[List[Command], int]:
    """Parse commands from lines starting at start_index.
    
    Internal parsing function that handles recursive loop parsing.
    
    Args:
        lines: List of text lines to parse
        start_index: Index to start parsing from
        in_loop: Whether we're currently inside a loop block
        
    Returns:
        Tuple of (parsed_commands, next_line_index) where next_line_index
        is the first line after the parsed block.
        
    Raises:
        ValueError: If loop syntax is malformed (unmatched LOOP/ENDLOOP)
    """
    commands = []
    i = start_index
    
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        # Skip comments (lines starting with '#') and empty lines
        if not line or line.startswith('#'):
            continue
            
        # Parse command line using regex
        match = COMMAND_RE.match(line)
        if not match:
            raise ValueError(f"Invalid macro line format: {line}")
            
        cmd = match.group('cmd').upper()
        args_text = match.group('args').strip()
        args = args_text.split() if args_text else []
        
        # Handle loop start command
        if cmd == 'LOOP':
            if not args or not args[0].isdigit():
                raise ValueError(f"LOOP command requires a numeric count: {line}")
            count = int(args[0])
            if count <= 0:
                raise ValueError(f"LOOP count must be positive: {line}")
            
            # Recursively parse loop body until ENDLOOP
            loop_body, i = _parse_commands(lines, i, in_loop=True)
            commands.append(('LOOP', [str(count)], loop_body))
            
        # Handle loop end command
        elif cmd == 'ENDLOOP':
            if not in_loop:
                raise ValueError("ENDLOOP found without matching LOOP")
            # Return to caller (end of current loop block)
            return commands, i
            
        # Handle regular controller command
        else:
            commands.append((cmd, args))
    
    # Validate that all loops are properly closed
    if in_loop:
        raise ValueError("LOOP command is missing matching ENDLOOP")
    
    return commands, i


def flatten_commands(commands: List[Command]) -> List[Tuple[str, List[str]]]:
    """Flatten structured commands into a simple execution sequence.
    
    Recursively expands all LOOP structures into repeated command sequences,
    producing a flat list suitable for direct execution by command runners.
    
    Args:
        commands: List of structured commands (may contain nested loops)
        
    Returns:
        Flat list of (command_name, arguments) tuples with all loops expanded.
        
    Example:
        Flatten loop structures::
        
            structured = [
                ('PRESS', ['A', '0.1']),
                ('LOOP', ['3'], [('PRESS', ['B', '0.1'])]),
                ('PRESS', ['C', '0.1'])
            ]
            flattened = flatten_commands(structured)
            # Returns: [('PRESS', ['A', '0.1']), ('PRESS', ['B', '0.1']),
            #           ('PRESS', ['B', '0.1']), ('PRESS', ['B', '0.1']),
            #           ('PRESS', ['C', '0.1'])]
            
    Note:
        Large loop counts will produce large command lists. Be careful with
        memory usage for macros with many iterations.
    """
    result = []
    
    for cmd in commands:
        if len(cmd) == 3 and cmd[0] == 'LOOP':  # Loop command structure
            _, count_args, loop_body = cmd
            count = int(count_args[0])
            
            # Recursively expand loop body for each iteration
            for _ in range(count):
                result.extend(flatten_commands(loop_body))
        else:
            # Simple command - add directly to result
            result.append(cmd)
    
    return result
