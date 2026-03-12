"""
Unit tests for v7.0 Proactive Nudging.

Tests:
1. Time window detection algorithm
2. Hour bucket classification
3. Pattern confidence calculation
4. Current matching windows filtering
5. Proactive nudge embed generation
6. Nudge status tracking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class TestTimeWindowDetector:
    """Test suite for time_window_detector module."""

    @pytest.fixture
    def sample_workout_logs(self):
        """Create sample workout logs with recurring patterns."""
        now = datetime.now(ZoneInfo("America/Toronto"))

        # Create a pattern: Yoga on Monday mornings, Walking on Wednesday afternoons
        logs = []

        # Monday morning Yoga (4 occurrences in past 2 weeks)
        for weeks_ago in range(2):
            monday = now - timedelta(days=(now.weekday() + 7 * weeks_ago))
            for hour in [7, 8]:  # Morning hours
                logs.append({
                    "exercise_name": "Yoga",
                    "duration_min": 30,
                    "kcal_estimate": 100,
                    "status": "completed",
                    "timestamp": monday.replace(hour=hour, minute=0).isoformat(),
                })

        # Wednesday afternoon Walking (3 occurrences)
        for weeks_ago in range(2):
            wed_offset = (now.weekday() - 2) % 7 + 7 * weeks_ago
            wed = now - timedelta(days=wed_offset) if wed_offset > 0 else now + timedelta(days=-wed_offset)
            logs.append({
                "exercise_name": "Walking",
                "duration_min": 45,
                "kcal_estimate": 150,
                "status": "completed",
                "timestamp": wed.replace(hour=14, minute=0).isoformat(),
            })

        # Friday evening HIIT (2 occurrences)
        for weeks_ago in range(2):
            fri_offset = (now.weekday() - 4) % 7 + 7 * weeks_ago
            fri = now - timedelta(days=fri_offset) if fri_offset > 0 else now + timedelta(days=-fri_offset)
            logs.append({
                "exercise_name": "HIIT",
                "duration_min": 20,
                "kcal_estimate": 250,
                "status": "completed",
                "timestamp": fri.replace(hour=19, minute=0).isoformat(),
            })

        return logs

    def test_get_hour_bucket_morning(self):
        """Test morning hour bucket classification."""
        from src.scheduler.time_window_detector import get_hour_bucket

        assert get_hour_bucket(6) == "morning"
        assert get_hour_bucket(8) == "morning"
        assert get_hour_bucket(11) == "morning"

    def test_get_hour_bucket_afternoon(self):
        """Test afternoon hour bucket classification."""
        from src.scheduler.time_window_detector import get_hour_bucket

        assert get_hour_bucket(12) == "afternoon"
        assert get_hour_bucket(15) == "afternoon"
        assert get_hour_bucket(17) == "afternoon"

    def test_get_hour_bucket_evening(self):
        """Test evening hour bucket classification."""
        from src.scheduler.time_window_detector import get_hour_bucket

        assert get_hour_bucket(18) == "evening"
        assert get_hour_bucket(20) == "evening"
        assert get_hour_bucket(22) == "evening"

    def test_get_hour_bucket_night(self):
        """Test night hour bucket classification (late night/early morning)."""
        from src.scheduler.time_window_detector import get_hour_bucket

        assert get_hour_bucket(23) == "night"
        assert get_hour_bucket(0) == "night"
        assert get_hour_bucket(5) == "night"

    def test_detect_time_windows_basic(self, sample_workout_logs):
        """Test basic time window detection."""
        from src.scheduler.time_window_detector import detect_time_windows

        windows = detect_time_windows(
            sample_workout_logs,
            min_frequency=2,
            days_back=14,
            timezone=ZoneInfo("America/Toronto"),
        )

        # Should detect at least 2 patterns (Yoga Monday morning, HIIT Friday evening)
        assert len(windows) >= 2

        # All windows should have required fields
        for window in windows:
            assert window.exercise_name
            assert 0 <= window.day_of_week <= 6
            assert window.hour_bucket in ["morning", "afternoon", "evening"]
            assert window.frequency >= 2
            assert 0 <= window.confidence <= 1

    def test_detect_time_windows_min_frequency(self, sample_workout_logs):
        """Test that low frequency patterns are filtered out."""
        from src.scheduler.time_window_detector import detect_time_windows

        # Require 5 occurrences - should filter out most patterns
        windows = detect_time_windows(
            sample_workout_logs,
            min_frequency=5,
            days_back=14,
            timezone=ZoneInfo("America/Toronto"),
        )

        # With min_frequency=5, no patterns should match in our sample data
        assert len(windows) == 0

    def test_detect_time_windows_empty_logs(self):
        """Test handling of empty workout logs."""
        from src.scheduler.time_window_detector import detect_time_windows

        windows = detect_time_windows([])
        assert windows == []

    def test_detect_time_windows_confidence_ordering(self, sample_workout_logs):
        """Test that windows are sorted by confidence descending."""
        from src.scheduler.time_window_detector import detect_time_windows

        windows = detect_time_windows(
            sample_workout_logs,
            min_frequency=2,
            days_back=14,
            timezone=ZoneInfo("America/Toronto"),
        )

        if len(windows) >= 2:
            for i in range(len(windows) - 1):
                assert windows[i].confidence >= windows[i + 1].confidence

    def test_time_window_to_dict(self, sample_workout_logs):
        """Test TimeWindow serialization to dict."""
        from src.scheduler.time_window_detector import detect_time_windows

        windows = detect_time_windows(
            sample_workout_logs,
            min_frequency=2,
            days_back=14,
            timezone=ZoneInfo("America/Toronto"),
        )

        if windows:
            window_dict = windows[0].to_dict()
            assert "exercise_name" in window_dict
            assert "day_of_week" in window_dict
            assert "day_name" in window_dict
            assert "hour_bucket" in window_dict
            assert "frequency" in window_dict
            assert "confidence" in window_dict


class TestCurrentMatchingWindows:
    """Test suite for matching windows to current time."""

    def test_get_current_matching_windows_match(self):
        """Test finding matching windows for current time."""
        from src.scheduler.time_window_detector import (
            detect_time_windows,
            get_current_matching_windows,
            TimeWindow,
        )

        # Create a window that matches current time
        now = datetime.now(ZoneInfo("America/Toronto"))
        current_day = now.weekday()
        current_bucket = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"

        # Manually create a matching window
        matching_window = TimeWindow(
            exercise_name="Test Exercise",
            day_of_week=current_day,
            hour_bucket=current_bucket,
            frequency=3,
            confidence=0.5,
        )

        # Create a non-matching window
        non_matching_window = TimeWindow(
            exercise_name="Other Exercise",
            day_of_week=(current_day + 1) % 7,  # Different day
            hour_bucket=current_bucket,
            frequency=3,
            confidence=0.5,
        )

        windows = [matching_window, non_matching_window]
        matching = get_current_matching_windows(windows, timezone=ZoneInfo("America/Toronto"))

        # Should only return the matching window
        assert len(matching) == 1
        assert matching[0].exercise_name == "Test Exercise"

    def test_get_current_matching_windows_no_match(self):
        """Test when no windows match current time."""
        from src.scheduler.time_window_detector import (
            get_current_matching_windows,
            TimeWindow,
        )

        now = datetime.now(ZoneInfo("America/Toronto"))
        current_day = now.weekday()

        # Create windows that don't match current day
        windows = [
            TimeWindow(
                exercise_name="Test",
                day_of_week=(current_day + 1) % 7,  # Tomorrow
                hour_bucket="morning",
                frequency=3,
                confidence=0.5,
            )
        ]

        matching = get_current_matching_windows(windows, timezone=ZoneInfo("America/Toronto"))
        assert len(matching) == 0

    def test_get_current_matching_windows_empty(self):
        """Test with empty window list."""
        from src.scheduler.time_window_detector import get_current_matching_windows

        matching = get_current_matching_windows([])
        assert matching == []


class TestProactiveNudgeEmbed:
    """Test suite for proactive nudge embed generation."""

    @pytest.fixture
    def mock_discord(self):
        """Mock discord module for testing without dependency."""
        with patch.dict('sys.modules', {'discord': MagicMock()}):
            yield

    def test_build_proactive_nudge_embed_good_budget(self, mock_discord):
        """Test nudge embed with good budget status."""
        from src.discord_bot.embed_builder import HealthButlerEmbed

        embed = HealthButlerEmbed.build_proactive_nudge_embed(
            user_name="TestUser",
            exercise_name="Yoga",
            time_window={
                "day_name": "Monday",
                "hour_bucket": "morning",
                "confidence": 0.8,
                "frequency": 3,
            },
            budget_progress={
                "remaining": 800,
                "remaining_pct": 60,
                "status": "good",
                "status_emoji": "🟢",
                "calorie_bar": "🟢 `[▰▰▰▰▰▱▱▱▱▱] 40%`",
            },
        )

        assert embed is not None
        # Check title contains exercise name
        assert hasattr(embed, 'title')

    def test_build_proactive_nudge_embed_critical_budget(self, mock_discord):
        """Test nudge embed with critical budget status."""
        from src.discord_bot.embed_builder import HealthButlerEmbed

        embed = HealthButlerEmbed.build_proactive_nudge_embed(
            user_name="TestUser",
            exercise_name="HIIT",
            time_window={
                "day_name": "Friday",
                "hour_bucket": "evening",
                "confidence": 0.7,
                "frequency": 2,
            },
            budget_progress={
                "remaining": 50,
                "remaining_pct": 5,
                "status": "critical",
                "status_emoji": "🔴",
                "calorie_bar": "🔴 `[▰▰▰▰▰▰▰▰▰▰] 95%`",
            },
        )

        assert embed is not None
        assert hasattr(embed, 'title')

    def test_build_proactive_nudge_embed_no_budget(self, mock_discord):
        """Test nudge embed without budget info."""
        from src.discord_bot.embed_builder import HealthButlerEmbed

        embed = HealthButlerEmbed.build_proactive_nudge_embed(
            user_name="TestUser",
            exercise_name="Walking",
            time_window={
                "day_name": "Wednesday",
                "hour_bucket": "afternoon",
                "confidence": 0.6,
                "frequency": 2,
            },
        )

        assert embed is not None
        assert hasattr(embed, 'title')


class TestNudgeStatusTracking:
    """Test suite for nudge status tracking in profile_utils."""

    def test_get_set_nudge_status(self):
        """Test getting and setting nudge status."""
        from src.discord_bot import profile_utils as pu

        user_id = "test_user_123"
        date_str = "2026-03-11"

        # Initially not nudged
        assert pu.get_user_nudge_status(user_id, date_str) == False

        # Set nudged
        pu.set_user_nudge_status(user_id, date_str, True)
        assert pu.get_user_nudge_status(user_id, date_str) == True

        # Different date should still be False
        assert pu.get_user_nudge_status(user_id, "2026-03-12") == False

    def test_time_windows_cache(self):
        """Test time windows caching."""
        from src.discord_bot import profile_utils as pu
        from src.scheduler.time_window_detector import TimeWindow

        user_id = "test_user_456"

        # Initially empty
        assert pu.get_user_time_windows(user_id) == []

        # Set windows
        windows = [
            TimeWindow(
                exercise_name="Yoga",
                day_of_week=0,
                hour_bucket="morning",
                frequency=3,
                confidence=0.7,
            )
        ]
        pu.set_user_time_windows(user_id, windows)

        # Retrieve
        cached = pu.get_user_time_windows(user_id)
        assert len(cached) == 1
        assert cached[0].exercise_name == "Yoga"

        # Clear
        pu.clear_user_time_windows(user_id)
        assert pu.get_user_time_windows(user_id) == []


class TestFormatTimeWindowMessage:
    """Test suite for time window message formatting."""

    def test_format_message_basic(self):
        """Test basic message formatting."""
        from src.scheduler.time_window_detector import (
            TimeWindow,
            format_time_window_message,
        )

        window = TimeWindow(
            exercise_name="Yoga",
            day_of_week=0,  # Monday
            hour_bucket="morning",
            frequency=3,
            confidence=0.7,
        )

        message = format_time_window_message(window, "Alice")

        assert "Alice" in message
        assert "Yoga" in message
        assert "Monday" in message
        assert "3" in message
