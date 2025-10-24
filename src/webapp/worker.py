"""Worker logic that runs in a separate thread with its own asyncio loop.

This file contains worker_main() which creates the adapter, MacroRunner and
forwards logs to thread-safe queues. It also listens to a thread-safe cmd_q.
"""
from __future__ import annotations

import asyncio
import pathlib
import traceback
import time
import queue
from typing import Optional

from macros.parser import parse_macro
from macros.runner import MacroRunner
from adapter.factory import create_adapter


class MacroStatus:
    def __init__(self):
        self.name = None
        self.iterations = 0
        self.last_iter_time = None
        self.sec_per_iter = None
        
        # Simple runtime tracking
        self.total_runtime = 0.0  # Total accumulated runtime in seconds
        self.session_start = None  # When current session started
        self.is_running = False   # Whether macro is currently running
        
        # Alert system
        self.alert_interval = 0  # 0 = disabled, >0 = alert every N iterations
        self.last_alert_iteration = 0
        self.pending_alert = False  # Flag to indicate alert should be sent to client

    def start_session(self):
        """Start a new running session."""
        if not self.is_running:
            self.session_start = time.time()
            self.is_running = True

    def pause_session(self):
        """Pause the current session, accumulating runtime."""
        if self.is_running and self.session_start is not None:
            # Add session time to total
            self.total_runtime += (time.time() - self.session_start)
            self.session_start = None
            self.is_running = False

    def stop_session(self):
        """Stop the current session, accumulating runtime."""
        if self.is_running and self.session_start is not None:
            # Add session time to total
            self.total_runtime += (time.time() - self.session_start)
            self.session_start = None
            self.is_running = False

    def get_current_runtime(self):
        """Get current total runtime in seconds."""
        runtime = self.total_runtime
        if self.is_running and self.session_start is not None:
            runtime += (time.time() - self.session_start)
        return runtime

    def reset_all_metrics(self):
        """Reset all metrics to zero."""
        self.iterations = 0
        self.last_iter_time = None
        self.sec_per_iter = None
        self.total_runtime = 0.0
        self.session_start = None
        self.is_running = False
        self.last_alert_iteration = 0
        self.pending_alert = False
    def to_dict(self):
        # Get current runtime
        runtime_seconds = int(self.get_current_runtime())
        h, m, s = runtime_seconds//3600, (runtime_seconds%3600)//60, runtime_seconds%60
        runtime = f"{h}:{m:02d}:{s:02d}"
        
        result = {
            'name': self.name,
            'runtime': runtime,
            'iterations': self.iterations,
            'sec_per_iter': round(self.sec_per_iter, 2) if self.sec_per_iter is not None else None,
            'alert_interval': self.alert_interval,
        }
        
        # Include alert flag if there's a pending alert
        if self.pending_alert:
            result['pending_alert'] = True
            self.pending_alert = False  # Clear the flag after including it
            
        return result
    
    def check_and_trigger_alert(self):
        """Check if an alert should be triggered based on iteration count."""
        if self.alert_interval > 0 and self.iterations > 0:
            if self.iterations - self.last_alert_iteration >= self.alert_interval:
                self.pending_alert = True
                self.last_alert_iteration = self.iterations
                return True
        return False


def broadcast_status(logs_qs: list, app_status: MacroStatus, adapter_name: str = "Unknown"):
    """Send status update to all WebSocket clients."""
    status_msg = {
        'type': 'status',
        'status': f"Running: {app_status.iterations} iterations" if app_status.name else "Idle",
        'macro_name': app_status.name or "No macro loaded",
        'adapter_name': adapter_name,
        'iterations': app_status.iterations
    }
    
    for q in logs_qs:
        try:
            q.put_nowait(status_msg)
        except Exception:
            try:
                q.put(status_msg)
            except Exception:
                pass

def broadcast_log(logs_qs: list, message: str, level: str = 'info'):
    """Send log message to all WebSocket clients."""
    log_msg = {
        'type': 'log',
        'message': message,
        'level': level
    }
    
    for q in logs_qs:
        try:
            q.put_nowait(log_msg)
        except Exception:
            try:
                q.put(log_msg)
            except Exception:
                pass

async def worker_main(macro_file: Optional[str], cmd_q: 'queue.Queue', logs_qs: list, status: Optional[MacroStatus]=None, preferred_adapter: Optional[str]=None):
    try:
        broadcast_log(logs_qs, 'worker: starting')

        commands = []
        if macro_file:
            try:
                p = pathlib.Path(macro_file)
                if p.exists():
                    text = p.read_text()
                    commands = parse_macro(text)
                else:
                    broadcast_log(logs_qs, f'Initial macro not found: {macro_file}', 'warning')
            except Exception as e:
                broadcast_log(logs_qs, f'Error reading initial macro {macro_file}: {e}', 'error')
        broadcast_log(logs_qs, f'worker: parsed {len(commands)} commands')

        broadcast_log(logs_qs, 'worker: creating and connecting adapter (prioritizing Pico)')
        
        # Initialize app_status before using it
        app_status = status if status is not None else MacroStatus()
        
        adapter = await create_adapter(preferred_adapter)  # Factory handles connection automatically
        adapter_name = adapter.__class__.__name__ if adapter else "No adapter"
        broadcast_log(logs_qs, 'worker: adapter connected', 'success')
        broadcast_status(logs_qs, app_status, adapter_name)

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
                        
                        # Update iteration timing
                        if st.last_iter_time is not None:
                            st.sec_per_iter = now - st.last_iter_time
                        st.last_iter_time = now
                        st.iterations += 1
                        
                        # Check if an alert should be triggered
                        if st.check_and_trigger_alert():
                            for q in logs_qs:
                                try:
                                    q.put_nowait(f'ALERT: Completed {st.iterations} iterations')
                                except Exception:
                                    try:
                                        q.put(f'ALERT: Completed {st.iterations} iterations')
                                    except Exception:
                                        pass
                    elif msg.startswith('Loaded macro:'):
                        parts = msg.split(':',1)[1].strip().split(' ',1)
                        st = app_status
                        st.name = parts[0]
                        # Don't reset metrics when loading a new macro - keep accumulating
                    elif msg.startswith('Macro stopped') or msg.startswith('Macro finished') or msg.startswith('Executed macro once:') or msg.startswith('Run-once macro') and 'completed' in msg:
                        # Stop runtime tracking when macro completes
                        st = app_status
                        st.stop_session()
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
                broadcast_log(logs_qs, f'worker: got cmd: {cmd}', 'info')
                if cmd == 'pause':
                    try:
                        if runner.is_running():
                            broadcast_log(logs_qs, 'Pausing macro - will stop after current iteration completes...', 'warning')
                            await runner.pause()
                            app_status.pause_session()  # Pause runtime tracking
                            broadcast_log(logs_qs, 'Pause requested - macro will stop after current iteration.', 'info')
                        else:
                            broadcast_log(logs_qs, 'No macro is currently running', 'warning')
                    except Exception as e:
                        broadcast_log(logs_qs, f'Error pausing runner: {e}', 'error')
                elif cmd == 'resume':
                    try:
                        app_status.start_session()  # Resume runtime tracking
                        runner.resume()
                    except Exception:
                        pass
                elif cmd == 'restart':
                    try:
                        await runner.stop()
                        await runner.start()
                        # Only start runtime tracking if runner has commands to run
                        if hasattr(runner, '_commands') and runner._commands and len(runner._commands) > 0:
                            app_status.start_session()
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
                elif cmd == 'force_stop':
                    try:
                        await runner.force_stop()
                        app_status.stop_session()  # Stop runtime tracking completely
                        broadcast_log(logs_qs, 'Macro force stopped', 'warning')
                    except Exception as e:
                        broadcast_log(logs_qs, f'Error force stopping: {e}', 'error')
                elif isinstance(cmd, str) and cmd.startswith('adapter:'):
                    # Handle adapter switching - this would require restarting the entire worker
                    # For now, just log it - full implementation would require more complex worker management
                    new_adapter = cmd.split(':', 1)[1] if ':' in cmd else None
                    for q in logs_qs:
                        try:
                            q.put_nowait(f'Adapter change requested: {new_adapter}. Please restart the system.')
                        except Exception:
                            try:
                                q.put(f'Adapter change requested: {new_adapter}. Please restart the system.')
                            except Exception:
                                pass
                elif cmd == 'reset_metrics':
                    try:
                        app_status.reset_all_metrics()
                        broadcast_log(logs_qs, 'Metrics reset to zero', 'success')
                    except Exception as e:
                        broadcast_log(logs_qs, f'Error resetting metrics: {e}', 'error')
                elif isinstance(cmd, str) and cmd.startswith('alert:'):
                    # Handle alert interval setting
                    try:
                        alert_interval = int(cmd.split(':', 1)[1]) if ':' in cmd else 0
                        app_status.alert_interval = alert_interval
                        app_status.last_alert_iteration = app_status.iterations  # Reset alert counter
                        msg = f'Alert interval set to {alert_interval} iterations' if alert_interval > 0 else 'Alerts disabled'
                        for q in logs_qs:
                            try:
                                q.put_nowait(msg)
                            except Exception:
                                try:
                                    q.put(msg)
                                except Exception:
                                    pass
                    except ValueError:
                        for q in logs_qs:
                            try:
                                q.put_nowait('Invalid alert interval - must be a number')
                            except Exception:
                                try:
                                    q.put('Invalid alert interval - must be a number')
                                except Exception:
                                    pass
                elif isinstance(cmd, str) and cmd.startswith('run_once:'):
                    # Handle run-once command - run a macro just once without looping
                    parts = cmd.split(':', 1)
                    name = parts[1] if len(parts) > 1 else ''
                    
                    try:
                        from pathlib import Path
                        base_path = Path(pathlib.Path(__file__).parent.parent.parent) / 'data' / 'macros'
                        
                        mpath = base_path / Path(name).name
                        text = mpath.read_text()
                        new_commands = parse_macro(text)
                        
                        # Set single-run mode and prepare runner
                        runner.set_commands(new_commands)
                        runner.set_setup_commands(None)  # No setup for single runs
                        
                        # Stop any existing macro
                        await runner.stop()
                        
                        # Update status
                        try:
                            app_status.name = name
                            # Don't reset metrics for run_once - keep accumulating runtime
                            # Runtime will start when first iteration begins
                        except Exception:
                            pass
                        
                        # Create a cancellable task for run_once
                        async def run_once_task():
                            await runner.run_once()
                        
                        run_once_task_ref = asyncio.create_task(run_once_task())
                        runner._task = run_once_task_ref  # Store task reference for force_stop
                        
                        # Start runtime tracking for run_once
                        app_status.start_session()
                        
                        try:
                            await run_once_task_ref
                            # Stop runtime when run_once completes successfully
                            app_status.stop_session()
                        except asyncio.CancelledError:
                            broadcast_log(logs_qs, f'Run-once macro {name} was force stopped', 'warning')
                            # Also stop runtime when cancelled
                            app_status.stop_session()
                        finally:
                            runner._task = None
                        
                        msg = f'Executed macro once: {name} ({len(new_commands)} commands)'
                        for q in logs_qs:
                            try:
                                q.put_nowait(msg)
                            except Exception:
                                try:
                                    q.put(msg)
                                except Exception:
                                    pass
                    except Exception as e:
                        for q in logs_qs:
                            try:
                                q.put_nowait(f'Error running macro once {name}: {e}')
                            except Exception:
                                try:
                                    q.put(f'Error running macro once {name}: {e}')
                                except Exception:
                                    pass
                elif isinstance(cmd, str) and cmd.startswith('load:'):
                    parts = cmd.split(':', 2)  # Split into at most 3 parts: 'load', name, setup_name
                    name = parts[1] if len(parts) > 1 else ''
                    setup_name = parts[2] if len(parts) > 2 else None
                    
                    try:
                        from pathlib import Path
                        # load macros from the data directory to avoid mixing code and data
                        base_path = Path(pathlib.Path(__file__).parent.parent.parent) / 'data' / 'macros'
                        
                        # Load main macro
                        mpath = base_path / Path(name).name
                        text = mpath.read_text()
                        new_commands = parse_macro(text)
                        runner.set_commands(new_commands)
                        
                        # Load setup macro if specified
                        setup_commands = None
                        if setup_name:
                            setup_path = base_path / Path(setup_name).name
                            setup_text = setup_path.read_text()
                            setup_commands = parse_macro(setup_text)
                            runner.set_setup_commands(setup_commands)
                        else:
                            runner.set_setup_commands(None)
                        
                        await runner.stop()
                        await runner.start()
                        # Only start runtime tracking if commands were actually loaded
                        if new_commands and len(new_commands) > 0:
                            app_status.start_session()
                        try:
                            app_status.name = name
                            # Don't reset metrics when loading - keep accumulating runtime
                        except Exception:
                            pass
                        
                        # Log the loaded macros
                        if setup_name:
                            msg = f'Loaded macros: setup={setup_name} ({len(setup_commands)} commands), main={name} ({len(new_commands)} commands)'
                        else:
                            msg = f'Loaded macro: {name} ({len(new_commands)} commands)'
                        
                        for q in logs_qs:
                            try:
                                q.put_nowait(msg)
                            except Exception:
                                try:
                                    q.put(msg)
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
        # Only start runtime tracking if there are commands to run
        if commands and len(commands) > 0:
            app_status.start_session()
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
