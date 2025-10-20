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
from asyncio import Queue, Event

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


async def run_commands(adapter, commands: List[Tuple[str, List[str]]], *, log_queue: Queue | None = None, pause_event: Event | None = None, stop_event: Event | None = None):
    """Run commands with optional log_queue, pause_event and stop_event.

    - log_queue: asyncio.Queue[str] used to publish textual logs (if provided).
    - pause_event: when set, execution proceeds; when cleared, runner waits.
    - stop_event: when set, runner stops asap.
    """
    from adapter.base import Button, Stick

    def log(msg: str):
        if log_queue is None:
            print(msg)
        else:
            # don't await here; queue should be large enough for logging bursts
            try:
                log_queue.put_nowait(msg)
            except Exception:
                pass

    for cmd, args in commands:
        # stop if requested
        if stop_event is not None and stop_event.is_set():
            log('stopped')
            return

        # pause if requested
        if pause_event is not None:
            await pause_event.wait()

        if cmd == 'PRESS':
            btn_name = args[0].upper() if args else ''
            try:
                btn = Button[btn_name]
            except KeyError:
                try:
                    btn = Button(btn_name.lower())
                except Exception:
                    raise ValueError(f'Unknown button: {btn_name}')
            log(f'PRESS {btn.name}')
            await adapter.press(btn)

        elif cmd == 'SLEEP':
            sec = float(args[0]) if args else 0.0
            log(f'SLEEP {sec}s')
            # sleep in short increments to be responsive to stop/pause
            remaining = sec
            interval = 0.1
            while remaining > 0:
                if stop_event is not None and stop_event.is_set():
                    log('stopped during sleep')
                    return
                if pause_event is not None:
                    await pause_event.wait()
                await asyncio.sleep(min(interval, remaining))
                remaining -= interval

        elif cmd == 'STICK':
            stick_name = args[0].upper() if args else 'L'
            stick_enum = Stick.L_STICK if stick_name in ('L', 'L_STICK', 'LEFT') else Stick.R_STICK
            def parse_axis(x: str):
                if '.' in x or (x.startswith('-') and '.' in x):
                    return float(x)
                try:
                    return int(x, 0)
                except Exception:
                    return float(x)

            h = parse_axis(args[1]) if len(args) > 1 else 0
            v = parse_axis(args[2]) if len(args) > 2 else 0
            log(f'STICK {stick_enum.name} h={h} v={v}')
            await adapter.stick(stick_enum, h=h, v=v)

        else:
            raise ValueError(f'Unknown macro command: {cmd}')


class MacroRunner:
    """High level runner that manages macro execution, pause/resume and logs."""

    def __init__(self, adapter):
        self.adapter = adapter
        self._task = None
        self._commands = None
        self.log_queue: Queue | None = None
        self._pause_event = Event()
        self._pause_event.set()  # not paused
        self._stop_event = Event()

    def set_commands(self, commands: List[Tuple[str, List[str]]]):
        self._commands = commands

    def logs(self) -> Queue:
        if self.log_queue is None:
            self.log_queue = Queue()
        return self.log_queue

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self):
        if self._commands is None:
            raise RuntimeError('No commands set')
        if self.is_running():
            return
        self._stop_event.clear()
        self._pause_event.set()
        self._task = asyncio.create_task(run_commands(self.adapter, self._commands, log_queue=self.log_queue, pause_event=self._pause_event, stop_event=self._stop_event))

    async def stop(self):
        if not self.is_running():
            return
        self._stop_event.set()
        await self._task

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    async def restart(self):
        await self.stop()
        await self.start()