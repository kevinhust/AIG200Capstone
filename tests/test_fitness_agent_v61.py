"""
Unit tests for Fitness Agent v6.1 Supabase Integration.

Tests:
1. Profile loading with cache
2. Discord ID extraction
3. Fallback to default profile
4. Real-time stats integration
5. Budget progress tracking (v6.2)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import date


class TestFitnessAgentV61:
    """Test suite for v6.1 Supabase integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock ProfileDB instance."""
        db = Mock()
        db.get_profile = Mock(return_value={
            "id": "123456789",
            "full_name": "Test User",
            "age": 28,
            "gender": "Male",
            "weight_kg": 75,
            "height_cm": 175,
            "goal": "Lose Weight",
            "activity": "Moderately Active",
            "restrictions": "Knee Injury, Hypertension"
        })
        db.get_today_stats = Mock(return_value={
            "total_calories": 1200,
            "total_protein": 65
        })
        db.get_daily_aggregation = Mock(return_value={
            "calories_in": 1200,
            "calories_out": 300,
            "net_calories": 900,
            "protein_g": 65,
            "active_minutes": 45
        })
        return db

    @pytest.fixture
    def agent(self, mock_db):
        """Create a FitnessAgent with mocked DB."""
        with patch('src.discord_bot.profile_db.get_profile_db', return_value=mock_db):
            from src.agents.fitness.fitness_agent import FitnessAgent
            agent = FitnessAgent(db=mock_db)
            yield agent

    def test_load_user_context_success(self, agent, mock_db):
        """Test successful profile loading from Supabase."""
        profile = agent._load_user_context("123456789")

        assert profile["name"] == "Test User"
        assert profile["age"] == 28
        assert "Knee Injury" in profile["health_conditions"]
        assert "Hypertension" in profile["health_conditions"]
        mock_db.get_profile.assert_called_once_with("123456789")

    def test_load_user_context_cache(self, agent, mock_db):
        """Test that profile is cached after first load."""
        # First call
        profile1 = agent._load_user_context("123456789")
        # Second call (should hit cache)
        profile2 = agent._load_user_context("123456789")

        # DB should only be called once
        mock_db.get_profile.assert_called_once()

        # Both profiles should be identical
        assert profile1 == profile2

    def test_load_user_context_fallback(self, agent, mock_db):
        """Test fallback to default profile when Supabase returns None."""
        mock_db.get_profile.return_value = None

        profile = agent._load_user_context("nonexistent_user")

        assert profile["name"] == "User"  # Default value
        assert profile["health_conditions"] == []

    def test_extract_discord_id_from_context(self, agent):
        """Test extracting discord_user_id from context."""
        context = [
            {"type": "user_context", "content": json.dumps({"user_id": "987654321"})}
        ]

        discord_id = agent._extract_discord_id(context, "test task")

        assert discord_id == "987654321"

    def test_extract_discord_id_from_direct_field(self, agent):
        """Test extracting discord_user_id from direct field."""
        context = [
            {"discord_user_id": "111222333"}
        ]

        discord_id = agent._extract_discord_id(context, "test task")

        assert discord_id == "111222333"

    def test_extract_discord_id_fallback(self, agent):
        """Test fallback to 'default_user' when no ID found."""
        context = []

        discord_id = agent._extract_discord_id(context, "test task")

        assert discord_id == "default_user"

    def test_get_today_stats(self, agent, mock_db):
        """Test getting today's stats from Supabase."""
        stats = agent._get_today_stats("123456789")

        assert stats["total_calories"] == 1200
        assert stats["total_protein"] == 65
        mock_db.get_today_stats.assert_called_once_with("123456789")

    def test_get_daily_aggregation(self, agent, mock_db):
        """Test getting daily aggregation from Supabase."""
        agg = agent._get_daily_aggregation("123456789")

        assert agg["calories_in"] == 1200
        assert agg["calories_out"] == 300
        assert agg["net_calories"] == 900
        mock_db.get_daily_aggregation.assert_called_once()

    def test_health_conditions_parsing(self, agent, mock_db):
        """Test that health conditions are correctly parsed from restrictions string."""
        profile = agent._load_user_context("123456789")

        # Should parse "Knee Injury, Hypertension" into list
        assert len(profile["health_conditions"]) == 2
        assert "Knee Injury" in profile["health_conditions"]
        assert "Hypertension" in profile["health_conditions"]

    def test_empty_restrictions(self, agent, mock_db):
        """Test handling of empty restrictions."""
        mock_db.get_profile.return_value = {
            "id": "123456789",
            "full_name": "Healthy User",
            "age": 25,
            "restrictions": ""
        }

        profile = agent._load_user_context("123456789")

        assert profile["health_conditions"] == []

    def test_db_error_handling(self, agent, mock_db):
        """Test graceful handling of database errors."""
        mock_db.get_profile.side_effect = Exception("Connection timeout")

        profile = agent._load_user_context("123456789")

        # Should fallback to default profile
        assert profile["name"] == "User"
        assert profile["discord_user_id"] == "123456789"

    # ============================================
    # Budget Progress Tests (v6.2)
    # ============================================

    def test_budget_progress_normal(self, agent, mock_db):
        """Test budget progress generation with normal consumption."""
        daily_agg = {
            "calories_in": 1500,
            "calories_out": 300,
            "protein_g": 80
        }
        user_profile = {
            "goal": "Lose Weight",
            "activity_level": "Moderate"
        }

        # Mock BMR calculation (TDEE = BMR = 2000 for simplicity)
        with patch.object(agent, '_calculate_bmr', return_value=2000.0):
            progress = agent._generate_budget_progress(daily_agg, user_profile)

            assert "calorie_bar" in progress
            assert "remaining" in progress
            # remaining = tdee - calories_in + calories_out = 2000 - 1500 + 300 = 800
            assert progress["remaining"] == 800
            # remaining_pct = 800/2000 = 40% -> status is "good" (>= 40%)
            assert progress["status"] == "good"

            assert "🟢" in progress["calorie_bar"]

    def test_budget_progress_over_budget(self, agent, mock_db):
        """Test budget progress when over budget."""
        daily_agg = {
            "calories_in": 2500,
            "calories_out": 100,
            "protein_g": 50
        }
        user_profile = {"goal": "Lose Weight"}

        with patch.object(agent, '_calculate_bmr', return_value=2000.0):
            progress = agent._generate_budget_progress(daily_agg, user_profile)

            assert progress["status"] == "critical"
            assert progress["remaining"] < 0
            # Should have red color for calories
            assert "🔴" in progress["calorie_bar"]

    def test_budget_progress_under_budget(self, agent, mock_db):
        """Test budget progress when significantly under budget (eating too little).

        Note: From a calorie budget perspective, having lots of remaining calories
        is actually 'good' - you have room to eat more. The status reflects budget
        remaining, not health concerns about undereating.
        """
        daily_agg = {
            "calories_in": 800,
            "calories_out": 200,
            "protein_g": 30
        }
        user_profile = {"goal": "Gain Muscle"}

        with patch.object(agent, '_calculate_bmr', return_value=2500.0):
            progress = agent._generate_budget_progress(daily_agg, user_profile)

            # remaining = 2500 - 800 + 200 = 1900 (76% remaining)
            # This is "good" from a budget perspective
            assert progress["remaining"] == 1900
            assert progress["remaining_pct"] == 76.0
            assert progress["status"] == "good"  # 76% remaining is good

    def test_progress_bar_colors(self, agent):
        """Test progress bar color coding."""
        # 100% = red (over budget)
        with patch.object(agent, '_calculate_bmr', return_value=2000.0):
            bar_100 = agent._generate_budget_progress(
                {"calories_in": 2000, "calories_out": 0},
                {"goal": "Maintain"}
            )
            assert "🔴" in bar_100["calorie_bar"]

        # 85% = yellow (warning zone)
        with patch.object(agent, '_calculate_bmr', return_value=2000.0):
            bar_85 = agent._generate_budget_progress(
                {"calories_in": 1700, "calories_out": 0},
                {"goal": "Maintain"}
            )
            assert "🟡" in bar_85["calorie_bar"]

        # 50% = green (good)
        with patch.object(agent, '_calculate_bmr', return_value=2000.0):
            bar_50 = agent._generate_budget_progress(
                {"calories_in": 1000, "calories_out": 0},
                {"goal": "Maintain"}
            )
            assert "🟢" in bar_50["calorie_bar"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
