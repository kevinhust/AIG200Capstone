"""
Time Window Detection Algorithm for Proactive Nudging.

Analyzes workout history to detect recurring time patterns and generate
personalized workout reminders based on user habits.
"""

import logging
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Hour bucket definitions for time-of-day categorization
HOUR_BUCKETS = {
    "morning": range(6, 12),     # 6:00 - 11:59
    "afternoon": range(12, 18),  # 12:00 - 17:59
    "evening": range(18, 23),    # 18:00 - 22:59
}

# Day names for pattern display
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class TimeWindow:
    """Represents a detected time window pattern."""
    exercise_name: str
    day_of_week: int  # 0=Monday, 6=Sunday
    hour_bucket: str   # morning, afternoon, evening
    frequency: int     # How many times this pattern occurred
    confidence: float  # 0.0 to 1.0
    last_occurrence: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exercise_name": self.exercise_name,
            "day_of_week": self.day_of_week,
            "day_name": DAY_NAMES[self.day_of_week],
            "hour_bucket": self.hour_bucket,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "last_occurrence": self.last_occurrence.isoformat() if self.last_occurrence else None,
        }


def get_hour_bucket(hour: int) -> str:
    """
    Map an hour (0-23) to a time bucket.

    Args:
        hour: Hour of day (0-23)

    Returns:
        Time bucket string: "morning", "afternoon", "evening", or "night"
    """
    for bucket_name, hour_range in HOUR_BUCKETS.items():
        if hour in hour_range:
            return bucket_name
    return "night"  # 23:00 - 5:59


def detect_time_windows(
    workout_logs: List[Dict[str, Any]],
    min_frequency: int = 2,
    days_back: int = 14,
    timezone: Optional[ZoneInfo] = None,
) -> List[TimeWindow]:
    """
    Detect recurring time patterns from workout history.

    Algorithm:
    1. Filter logs within the lookback period
    2. Group by (exercise_name, day_of_week, hour_bucket)
    3. Filter groups with frequency >= min_frequency
    4. Calculate confidence scores
    5. Return sorted by confidence (descending)

    Args:
        workout_logs: List of workout log dictionaries with 'timestamp' and 'exercise_name'
        min_frequency: Minimum occurrences to consider a pattern (default: 2)
        days_back: Number of days to look back for patterns (default: 14)
        timezone: Timezone for date calculations (default: UTC)

    Returns:
        List of TimeWindow objects sorted by confidence
    """
    if not workout_logs:
        return []

    if timezone is None:
        timezone = ZoneInfo("UTC")

    cutoff_date = datetime.now(timezone) - __import__("datetime").timedelta(days=days_back)

    # Group patterns
    pattern_counts: Dict[tuple, List[datetime]] = defaultdict(list)

    for log in workout_logs:
        # Extract timestamp
        timestamp_raw = log.get("timestamp") or log.get("created_at") or log.get("logged_at")
        if not timestamp_raw:
            continue

        # Parse timestamp
        try:
            if isinstance(timestamp_raw, str):
                # Handle ISO format with or without timezone
                if timestamp_raw.endswith("Z"):
                    timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.fromisoformat(timestamp_raw)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
            elif isinstance(timestamp_raw, datetime):
                timestamp = timestamp_raw
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=ZoneInfo("UTC"))
            else:
                continue
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse timestamp: {timestamp_raw}, error: {e}")
            continue

        # Convert to target timezone
        timestamp = timestamp.astimezone(timezone)

        # Skip if outside lookback window
        if timestamp < cutoff_date:
            continue

        # Extract exercise name
        exercise_name = log.get("exercise_name") or log.get("name") or log.get("activity")
        if not exercise_name:
            continue

        # Calculate pattern key
        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        hour_bucket = get_hour_bucket(timestamp.hour)

        # Skip "night" bucket (late night/early morning workouts are less predictable)
        if hour_bucket == "night":
            continue

        key = (exercise_name, day_of_week, hour_bucket)
        pattern_counts[key].append(timestamp)

    # Build TimeWindow objects for patterns meeting minimum frequency
    windows: List[TimeWindow] = []

    for (exercise_name, day_of_week, hour_bucket), timestamps in pattern_counts.items():
        frequency = len(timestamps)
        if frequency < min_frequency:
            continue

        # Calculate confidence based on frequency and recency
        # More recent and more frequent = higher confidence
        last_occurrence = max(timestamps)

        # Confidence formula:
        # - Base confidence from frequency (max 0.7 for 5+ occurrences)
        # - Bonus for recency (up to 0.3)
        freq_confidence = min(0.7, frequency * 0.14)  # 0.14 per occurrence, max 0.7

        # Recency bonus: most recent within 3 days = 0.3, decays to 0 over 14 days
        days_since_last = (datetime.now(timezone) - last_occurrence).days
        recency_bonus = max(0, 0.3 * (1 - days_since_last / 14))

        confidence = freq_confidence + recency_bonus

        window = TimeWindow(
            exercise_name=exercise_name,
            day_of_week=day_of_week,
            hour_bucket=hour_bucket,
            frequency=frequency,
            confidence=round(confidence, 2),
            last_occurrence=last_occurrence,
        )
        windows.append(window)

    # Sort by confidence descending
    windows.sort(key=lambda w: w.confidence, reverse=True)

    logger.info(f"Detected {len(windows)} time windows from {len(workout_logs)} logs")
    return windows


def get_current_matching_windows(
    time_windows: List[TimeWindow],
    current_time: Optional[datetime] = None,
    timezone: Optional[ZoneInfo] = None,
) -> List[TimeWindow]:
    """
    Filter time windows that match the current day and hour bucket.

    Args:
        time_windows: List of detected time windows
        current_time: Current datetime (default: now)
        timezone: Timezone for calculations (default: UTC)

    Returns:
        List of matching TimeWindow objects
    """
    if not time_windows:
        return []

    if timezone is None:
        timezone = ZoneInfo("UTC")

    if current_time is None:
        current_time = datetime.now(timezone)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone)

    current_day = current_time.weekday()
    current_bucket = get_hour_bucket(current_time.hour)

    # Filter matching windows
    matching = [
        window for window in time_windows
        if window.day_of_week == current_day and window.hour_bucket == current_bucket
    ]

    return matching


def format_time_window_message(window: TimeWindow, user_name: str) -> str:
    """
    Generate a human-readable message for a time window.

    Args:
        window: The detected time window
        user_name: User's display name

    Returns:
        Formatted message string
    """
    day_name = DAY_NAMES[window.day_of_week]
    bucket_display = window.hour_bucket.capitalize()

    return (
        f"Hi {user_name}! Based on your pattern of doing "
        f"{window.exercise_name} on {day_name} {bucket_display}s "
        f"({window.frequency} times recently), thought I'd check in!"
    )
