"""Macro execution and MacroRunner class.

Contains the logic to run parsed macros against an adapter and the
MacroRunner orchestration class used by the web worker.
"""
from __future__ import annotations

import asyncio
from typing import List, Tuple, Any
from asyncio import Queue, Event


async def run_macro(adapter, commands: List[Tuple[str, List[str]]], dry_run: bool = False):
    from adapter.base import Button, Stick

    for cmd, args in commands:
        if cmd == 'PRESS':
            if len(args) < 1:
                raise ValueError('PRESS requires a button name')
            btn_name = args[0].upper()
            try:
                btn = Button[btn_name]
            except KeyError:
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
            def parse_axis(x: str) -> Any:
                if '.' in x or x.startswith('-') and '.' in x:
                    return float(x)
                try:
                    return int(x, 0)
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
    from adapter.base import Button, Stick

    def log(msg: str):
        if log_queue is None:
            print(msg)
        else:
            try:
                log_queue.put_nowait(msg)
            except Exception:
                pass

    for cmd, args in commands:
        if stop_event is not None and stop_event.is_set():
            log('stopped')
            return
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
    def __init__(self, adapter):
        self.adapter = adapter
        self._task = None
        self._commands = None
        self._setup_commands = None
        self.log_queue: Queue | None = None
        self._pause_event = Event()
        self._pause_event.set()
        self._stop_event = Event()
        self._graceful_pause_event = Event()
        self._graceful_pause_event.set()

    def set_commands(self, commands: List[Tuple[str, List[str]]]):
        self._commands = commands

    def set_setup_commands(self, setup_commands: List[Tuple[str, List[str]]]):
        """Set commands to run once before the main macro loop starts."""
        self._setup_commands = setup_commands

    def logs(self) -> Queue:
        if self.log_queue is None:
            self.log_queue = Queue()
        return self.log_queue

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self):
        if self._commands is None:
            raise RuntimeError('No commands set')
        if isinstance(self._commands, list) and len(self._commands) == 0:
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait('MacroRunner: no commands to run')
                except Exception:
                    pass
            return
        if self.is_running():
            return
        self._stop_event.clear()
        self._pause_event.set()
        self._graceful_pause_event.set()

        async def _loop():
            # Run setup commands once if they exist
            if self._setup_commands is not None and len(self._setup_commands) > 0:
                try:
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait('=== running setup macro ===')
                        except Exception:
                            pass
                    await run_commands(self.adapter, self._setup_commands, log_queue=self.log_queue, pause_event=self._pause_event, stop_event=self._stop_event)
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait('=== setup macro completed ===')
                        except Exception:
                            pass
                except Exception as e:
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait(f'Error during setup macro: {e}')
                        except Exception:
                            pass
                    else:
                        print(f'Error during setup macro: {e}')
                    # Don't continue to main loop if setup fails
                    return

            # Main macro loop
            iteration = 0
            while not self._stop_event.is_set():
                iteration += 1
                try:
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait(f'=== iteration {iteration} start ===')
                        except Exception:
                            pass
                    # Don't pass pause_event to run_commands for graceful pause - let iteration complete
                    await run_commands(self.adapter, self._commands, log_queue=self.log_queue, stop_event=self._stop_event)
                    
                    # Check for graceful pause after iteration completes
                    if not self._graceful_pause_event.is_set():
                        if self.log_queue is not None:
                            try:
                                self.log_queue.put_nowait(f'=== pausing after iteration {iteration} ===')
                            except Exception:
                                pass
                        # Release controls and wait for resume
                        try:
                            await self.adapter.release_all_buttons()
                            await self.adapter.center_sticks()
                        except Exception:
                            pass
                        await self._graceful_pause_event.wait()
                        
                except Exception as e:
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait(f'Error during macro run: {e}')
                        except Exception:
                            pass
                    else:
                        print(f'Error during macro run: {e}')
                await asyncio.sleep(0.1)

        self._task = asyncio.create_task(_loop())

    async def stop(self):
        if not self.is_running():
            return
            
        if self.log_queue is not None:
            try:
                self.log_queue.put_nowait('=== stopping macro ===')
            except Exception:
                pass
        
        # Signal stop and unblock any pauses
        self._stop_event.set()
        self._pause_event.set()
        self._graceful_pause_event.set()
        
        try:
            await self._task
        finally:
            self._task = None
        
        # Clean up adapter state
        try:
            await self.adapter.release_all_buttons()
        except Exception:
            pass
        try:
            await self.adapter.center_sticks()
        except Exception:
            pass

    async def pause(self):
        """Gracefully pause after current iteration completes."""
        if self.is_running():
            self._graceful_pause_event.clear()
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait('=== graceful pause requested ===')
                except Exception:
                    pass

    def resume(self):
        """Resume from pause."""
        self._pause_event.set()
        self._graceful_pause_event.set()

    async def force_stop(self):
        """Immediately stop macro execution regardless of current state."""
        if not self.is_running():
            return
        
        if self.log_queue is not None:
            try:
                self.log_queue.put_nowait('=== force stop requested ===')
            except Exception:
                pass
        
        # Set all events to stop execution immediately
        self._stop_event.set()
        self._pause_event.set()  # Unblock any pause waits
        self._graceful_pause_event.set()  # Unblock any graceful pause waits
        
        # Cancel the task if it's still running
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        
        self._task = None
        
        # Clean up adapter state
        try:
            await self.adapter.release_all_buttons()
        except Exception:
            pass
        try:
            await self.adapter.center_sticks()
        except Exception:
            pass

    async def run_once(self):
        """Run the macro commands exactly once without looping."""
        if self._commands is None:
            raise RuntimeError('No commands set')
        if isinstance(self._commands, list) and len(self._commands) == 0:
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait('MacroRunner: no commands to run')
                except Exception:
                    pass
            return

        # Ensure pause events are in correct state for run_once
        self._pause_event.set()
        self._graceful_pause_event.set()
        self._stop_event.clear()

        try:
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait('=== running macro once ===')
                except Exception:
                    pass
            
            # Only pass stop_event to allow force stopping, but not pause_event 
            # since run_once should complete without being paused
            await run_commands(self.adapter, self._commands, log_queue=self.log_queue, 
                             stop_event=self._stop_event)
            
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait('=== macro run completed ===')
                except Exception:
                    pass
        except Exception as e:
            if self.log_queue is not None:
                try:
                    self.log_queue.put_nowait(f'Error during single macro run: {e}')
                except Exception:
                    pass
            else:
                print(f'Error during single macro run: {e}')
        finally:
            # Clean up adapter state
            try:
                await self.adapter.release_all_buttons()
            except Exception:
                pass
            try:
                await self.adapter.center_sticks()
            except Exception:
                pass
