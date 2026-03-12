"""
Scheduler module for proactive health nudging.

This module provides time window detection and scheduling capabilities
for the Health Butler Bot's proactive notification system.
"""

from .time_window_detector import (
    detect_time_windows,
    get_hour_bucket,
    get_current_matching_windows,
    TimeWindow,
)

__all__ = [
    "detect_time_windows",
    "get_hour_bucket",
    "get_current_matching_windows",
    "TimeWindow",
]
