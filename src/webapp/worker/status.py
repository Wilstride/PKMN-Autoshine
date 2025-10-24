"""Macro status tracking and metrics management.

This module provides the MacroStatus class for tracking macro execution
state, runtime metrics, and alert functionality.
"""
from __future__ import annotations

import time
from typing import Optional, Dict, Any


class MacroStatus:
    """Tracks macro execution status, runtime metrics, and alerts.
    
    This class manages the state of a running macro including:
    - Execution timing and runtime tracking
    - Iteration counting and performance metrics  
    - Alert system for long-running operations
    - Session-based runtime accumulation
    """
    
    def __init__(self) -> None:
        """Initialize a new MacroStatus instance."""
        # Basic macro information
        self.name: Optional[str] = None
        self.iterations: int = 0
        self.last_iter_time: Optional[float] = None
        self.sec_per_iter: Optional[float] = None
        
        # Simple runtime tracking with session-based accumulation
        self.total_runtime: float = 0.0  # Total accumulated runtime in seconds
        self.session_start: Optional[float] = None  # When current session started
        self.is_running: bool = False   # Whether macro is currently running
        
        # Alert system for long-running operations
        self.alert_interval: int = 0  # 0 = disabled, >0 = alert every N iterations
        self.last_alert_iteration: int = 0
        self.pending_alert: bool = False  # Flag to indicate alert should be sent to client

    def start_session(self) -> None:
        """Start a new running session.
        
        This begins timing a new macro execution session. If a session is
        already running, this call is ignored to prevent timing corruption.
        """
        if not self.is_running:
            self.session_start = time.time()
            self.is_running = True

    def pause_session(self) -> None:
        """Pause the current session, accumulating runtime.
        
        This stops the current timing session and adds the elapsed time
        to the total accumulated runtime. Can be resumed with start_session().
        """
        if self.is_running and self.session_start is not None:
            # Add session time to total
            self.total_runtime += (time.time() - self.session_start)
            self.session_start = None
            self.is_running = False

    def stop_session(self) -> None:
        """Stop the current session, accumulating runtime.
        
        This permanently stops the current timing session and adds the
        elapsed time to the total accumulated runtime.
        """
        if self.is_running and self.session_start is not None:
            # Add session time to total
            self.total_runtime += (time.time() - self.session_start)
            self.session_start = None
            self.is_running = False

    def get_current_runtime(self) -> float:
        """Get current total runtime in seconds.
        
        Returns:
            Total runtime including completed sessions and current session.
        """
        runtime = self.total_runtime
        if self.is_running and self.session_start is not None:
            runtime += (time.time() - self.session_start)
        return runtime

    def reset_all_metrics(self) -> None:
        """Reset all metrics to zero.
        
        This clears all tracking data including iterations, runtime,
        and alert state. Used when explicitly resetting metrics.
        """
        self.iterations = 0
        self.last_iter_time = None
        self.sec_per_iter = None
        self.total_runtime = 0.0
        self.session_start = None
        self.is_running = False
        self.last_alert_iteration = 0
        self.pending_alert = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary for JSON serialization.
        
        Returns:
            Dictionary containing all public status information.
        """
        # Get current runtime and format as HH:MM:SS
        runtime_seconds = int(self.get_current_runtime())
        hours, remainder = divmod(runtime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        runtime = f"{hours}:{minutes:02d}:{seconds:02d}"
        
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
    
    def check_and_trigger_alert(self) -> bool:
        """Check if an alert should be triggered based on iteration count.
        
        Returns:
            True if an alert was triggered, False otherwise.
        """
        if self.alert_interval > 0 and self.iterations > 0:
            if self.iterations - self.last_alert_iteration >= self.alert_interval:
                self.pending_alert = True
                self.last_alert_iteration = self.iterations
                return True
        return False

    def update_iteration_timing(self, current_time: float) -> None:
        """Update iteration timing metrics.
        
        Args:
            current_time: Current timestamp for timing calculations.
        """
        if self.last_iter_time is not None:
            self.sec_per_iter = current_time - self.last_iter_time
        self.last_iter_time = current_time
        self.iterations += 1