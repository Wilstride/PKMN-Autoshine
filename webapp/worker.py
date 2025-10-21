"""Worker logic that runs in a separate thread with its own asyncio loop.

This file contains worker_main() which creates the adapter, MacroRunner and
forwards logs to thread-safe queues. It also listens to a thread-safe cmd_q.
"""
from __future__ import annotations

import asyncio
import pathlib
import traceback
import time
from typing import Optional

from macros.parser import parse_macro
from macros.runner import MacroRunner
from adapter.joycontrol import JoycontrolAdapter


class MacroStatus:
    def __init__(self):
        self.name = None
        self.start_time = None
        self.iterations = 0
        self.last_iter_time = None
        self.sec_per_iter = None
        self.paused = False
        self.pause_start = None
        self.paused_total = 0.0
    def to_dict(self):
        runtime = '-'
        if self.start_time is not None:
            now = time.time()
            total_paused = self.paused_total
            if self.paused and self.pause_start is not None:
                total_paused += (now - self.pause_start)
            dt = int(now - self.start_time - total_paused)
            h, m, s = dt//3600, (dt%3600)//60, dt%60
            runtime = f"{h:02}:{m:02}:{s:02}"
        return {
            'name': self.name,
            'runtime': runtime,
            'iterations': self.iterations,
            'sec_per_iter': round(self.sec_per_iter, 2) if self.sec_per_iter is not None else None,
        }


async def worker_main(macro_file: Optional[str], cmd_q: 'queue.Queue', logs_qs: list, status: Optional[MacroStatus]=None):
    try:
        for q in logs_qs:
            try:
                q.put_nowait('worker: starting')
            except Exception:
                try:
                    q.put('worker: starting')
                except Exception:
                    pass

        commands = []
        if macro_file:
            try:
                p = pathlib.Path(macro_file)
                if p.exists():
                    text = p.read_text()
                    commands = parse_macro(text)
                else:
                    for q in logs_qs:
                        try:
                            q.put_nowait(f'Initial macro not found: {macro_file}')
                        except Exception:
                            try:
                                q.put(f'Initial macro not found: {macro_file}')
                            except Exception:
                                pass
            except Exception as e:
                for q in logs_qs:
                    try:
                        q.put_nowait(f'Error reading initial macro {macro_file}: {e}')
                    except Exception:
                        try:
                            q.put(f'Error reading initial macro {macro_file}: {e}')
                        except Exception:
                            pass
        for q in logs_qs:
            try:
                q.put_nowait(f'worker: parsed {len(commands)} commands')
            except Exception:
                try:
                    q.put(f'worker: parsed {len(commands)} commands')
                except Exception:
                    pass

        for q in logs_qs:
            try:
                q.put_nowait('worker: creating adapter')
            except Exception:
                try:
                    q.put('worker: creating adapter')
                except Exception:
                    pass
        adapter = JoycontrolAdapter()
        for q in logs_qs:
            try:
                q.put_nowait('worker: connecting adapter')
            except Exception:
                try:
                    q.put('worker: connecting adapter')
                except Exception:
                    pass
        await adapter.connect()
        for q in logs_qs:
            try:
                q.put_nowait('worker: adapter connected')
            except Exception:
                try:
                    q.put('worker: adapter connected')
                except Exception:
                    pass

        app_status = status if status is not None else MacroStatus()

        runner = MacroRunner(adapter)
        runner.set_commands(commands)
        rlogs = runner.logs()

        async def forward_rlogs():
            while True:
                try:
                    msg = await rlogs.get()
                except asyncio.CancelledError:
                    break
                try:
                    if msg.startswith('=== iteration'):
                        st = app_status
                        now = time.time()
                        if st.start_time is None:
                            st.start_time = now
                        if st.last_iter_time is not None:
                            st.sec_per_iter = now - st.last_iter_time
                        st.last_iter_time = now
                        st.iterations += 1
                    if msg.startswith('Loaded macro:'):
                        parts = msg.split(':',1)[1].strip().split(' ',1)
                        st = app_status
                        st.name = parts[0]
                        st.start_time = None
                        st.iterations = 0
                        st.last_iter_time = None
                        st.sec_per_iter = None
                except Exception:
                    pass
                for q in logs_qs:
                    try:
                        q.put_nowait(msg)
                    except Exception:
                        try:
                            q.put(msg)
                        except Exception:
                            pass

        loop = asyncio.get_event_loop()

        async def cmd_handler():
            while True:
                cmd = await loop.run_in_executor(None, cmd_q.get)
                for q in logs_qs:
                    try:
                        q.put_nowait(f'worker: got cmd: {cmd}')
                    except Exception:
                        try:
                            q.put(f'worker: got cmd: {cmd}')
                        except Exception:
                            pass
                if cmd == 'pause':
                    try:
                        try:
                            app_status.paused = True
                            app_status.pause_start = time.time()
                        except Exception:
                            pass
                        await runner.pause()
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error pausing runner: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error pausing runner: {e}')
                                except Exception:
                                    pass
                elif cmd == 'resume':
                    try:
                        if app_status.paused and app_status.pause_start is not None:
                            app_status.paused_total = (app_status.paused_total or 0.0) + (time.time() - app_status.pause_start)
                        app_status.paused = False
                        app_status.pause_start = None
                    except Exception:
                        pass
                    runner.resume()
                elif cmd == 'restart':
                    try:
                        await runner.restart()
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error restarting: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error restarting: {e}')
                                except Exception:
                                    pass
                elif cmd == 'stop':
                    await runner.stop()
                    break
                elif isinstance(cmd, str) and cmd.startswith('load:'):
                    name = cmd.split(':',1)[1]
                    try:
                        from pathlib import Path
                        # load macros from the data directory to avoid mixing code and data
                        mpath = Path(pathlib.Path(__file__).parent.parent) / 'data' / 'macros' / Path(name).name
                        text = mpath.read_text()
                        new_commands = parse_macro(text)
                        runner.set_commands(new_commands)
                        await runner.restart()
                        try:
                            app_status.name = name
                            app_status.start_time = None
                            app_status.iterations = 0
                            app_status.last_iter_time = None
                            app_status.sec_per_iter = None
                            app_status.paused = False
                            app_status.pause_start = None
                            app_status.paused_total = 0.0
                        except Exception:
                            pass
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Loaded macro: {name} ({len(new_commands)} commands)')
                            except Exception:
                                try:
                                    q.put(f'Loaded macro: {name} ({len(new_commands)} commands)')
                                except Exception:
                                    pass
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error loading macro {name}: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error loading macro {name}: {e}')
                                except Exception:
                                    pass

        await runner.start()
        await asyncio.gather(forward_rlogs(), cmd_handler())
    except Exception as e:
        tb = traceback.format_exc()
        for q in logs_qs:
            try:
                q.put_nowait(f'Worker error: {e}\n{tb}')
            except Exception:
                try:
                    q.put(f'Worker error: {e}\n{tb}')
                except Exception:
                    pass
