"""Macro execution and MacroRunner class.

Contains the logic to run parsed macros against an adapter and the
MacroRunner orchestration class used by the web worker.
"""
from __future__ import annotations

import asyncio
from typing import List, Tuple, Any
from asyncio import Queue, Event


async def run_macro(adapter, commands: List[Tuple[str, List[str], str | None]], dry_run: bool = False):
    from adapter.base import Button, Stick

    for cmd, args, device_id in commands:
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
                device_str = f" on {device_id}" if device_id else ""
                print(f'DRY PRESS {btn}{device_str}')
            else:
                # Check if adapter supports device targeting
                if hasattr(adapter, 'press') and 'device_id' in adapter.press.__code__.co_varnames:
                    await adapter.press(btn, device_id=device_id)
                else:
                    if device_id:
                        raise ValueError(f'Adapter does not support device targeting (device_id: {device_id})')
                    await adapter.press(btn)

        elif cmd == 'SLEEP':
            if len(args) < 1:
                raise ValueError('SLEEP requires seconds')
            sec = float(args[0])
            if dry_run:
                device_str = f" on {device_id}" if device_id else ""
                print(f'DRY SLEEP {sec}s{device_str}')
            else:
                # Check if adapter supports device targeting for sleep
                if hasattr(adapter, 'sleep') and 'device_id' in adapter.sleep.__code__.co_varnames:
                    await adapter.sleep(sec, device_id=device_id)
                else:
                    # For sleep, just sleep globally if device_id is not supported
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
                device_str = f" on {device_id}" if device_id else ""
                print(f'DRY STICK {stick_enum} h={h} v={v}{device_str}')
            else:
                # Check if adapter supports device targeting
                if hasattr(adapter, 'stick') and 'device_id' in adapter.stick.__code__.co_varnames:
                    await adapter.stick(stick_enum, h=h, v=v, device_id=device_id)
                else:
                    if device_id:
                        raise ValueError(f'Adapter does not support device targeting (device_id: {device_id})')
                    await adapter.stick(stick_enum, h=h, v=v)

        else:
            raise ValueError(f'Unknown macro command: {cmd}')


async def run_commands(adapter, commands: List[Tuple[str, List[str], str | None]], *, log_queue: Queue | None = None, pause_event: Event | None = None, stop_event: Event | None = None):
    from adapter.base import Button, Stick

    def log(msg: str):
        if log_queue is None:
            print(msg)
        else:
            try:
                log_queue.put_nowait(msg)
            except Exception:
                pass

    for cmd, args, device_id in commands:
        if stop_event is not None and stop_event.is_set():
            log('stopped')
            return
        if pause_event is not None:
            await pause_event.wait()

        device_str = f" on {device_id}" if device_id else ""

        if cmd == 'PRESS':
            btn_name = args[0].upper() if args else ''
            try:
                btn = Button[btn_name]
            except KeyError:
                try:
                    btn = Button(btn_name.lower())
                except Exception:
                    raise ValueError(f'Unknown button: {btn_name}')
            log(f'PRESS {btn.name}{device_str}')
            
            # Check if adapter supports device targeting
            if hasattr(adapter, 'press') and 'device_id' in adapter.press.__code__.co_varnames:
                await adapter.press(btn, device_id=device_id)
            else:
                if device_id:
                    raise ValueError(f'Adapter does not support device targeting (device_id: {device_id})')
                await adapter.press(btn)

        elif cmd == 'SLEEP':
            sec = float(args[0]) if args else 0.0
            log(f'SLEEP {sec}s{device_str}')
            
            # Check if adapter supports device targeting for sleep
            if hasattr(adapter, 'sleep') and 'device_id' in adapter.sleep.__code__.co_varnames:
                await adapter.sleep(sec, device_id=device_id)
            else:
                # For sleep, handle it globally regardless of device_id
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
            log(f'STICK {stick_enum.name} h={h} v={v}{device_str}')
            
            # Check if adapter supports device targeting
            if hasattr(adapter, 'stick') and 'device_id' in adapter.stick.__code__.co_varnames:
                await adapter.stick(stick_enum, h=h, v=v, device_id=device_id)
            else:
                if device_id:
                    raise ValueError(f'Adapter does not support device targeting (device_id: {device_id})')
                await adapter.stick(stick_enum, h=h, v=v)

        else:
            raise ValueError(f'Unknown macro command: {cmd}')


class MacroRunner:
    def __init__(self, adapter):
        self.adapter = adapter
        self._task = None
        self._commands = None
        self.log_queue: Queue | None = None
        self._pause_event = Event()
        self._pause_event.set()
        self._stop_event = Event()

    def set_commands(self, commands: List[Tuple[str, List[str], str | None]]):
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

        async def _loop():
            iteration = 0
            while not self._stop_event.is_set():
                iteration += 1
                try:
                    if self.log_queue is not None:
                        try:
                            self.log_queue.put_nowait(f'=== iteration {iteration} start ===')
                        except Exception:
                            pass
                    await run_commands(self.adapter, self._commands, log_queue=self.log_queue, pause_event=self._pause_event, stop_event=self._stop_event)
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
        self._stop_event.set()
        self._pause_event.set()
        try:
            await self._task
        finally:
            self._task = None
        try:
            await self.adapter.release_all_buttons()
        except Exception:
            pass
        try:
            await self.adapter.center_sticks()
        except Exception:
            pass

    async def pause(self):
        self._pause_event.clear()
        try:
            await self.adapter.release_all_buttons()
        except Exception:
            pass
        try:
            await self.adapter.center_sticks()
        except Exception:
            pass

    def resume(self):
        self._pause_event.set()

    async def restart(self):
        await self.stop()
        await self.start()
