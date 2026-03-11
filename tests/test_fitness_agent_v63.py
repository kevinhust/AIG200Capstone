"""
Unit tests for Fitness Agent v6.3 Preference Learning.

Tests:
1. User habits extraction from workout logs
2. Top activities frequency counting
3. Intensity classification
4. Recent trend detection
5. Empty history handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestFitnessAgentV63:
    """Test suite for v6.3 Preference Learning."""

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
            "restrictions": ""
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

    def test_get_user_habits_success(self, agent, mock_db):
        """Test successful habit extraction from workout logs."""
        # Mock workout logs with variety
        mock_logs = [
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Walking", "duration_min": 45, "kcal_estimate": 150, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "HIIT", "duration_min": 20, "kcal_estimate": 250, "status": "completed", "created_at": (datetime.now() - timedelta(days=5)).isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": (datetime.now() - timedelta(days=7)).isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)

        habits = agent._get_user_habits("123456789", days=14)

        # Verify top activities (Yoga appears twice, Walking twice, HIIT once)
        assert "Yoga" in habits["top_activities"]
        assert "Walking" in habits["top_activities"]
        assert habits["total_workouts"] == 5
        assert habits["avg_duration_min"] > 0
        assert habits["avg_intensity"] in ["low", "moderate", "high"]

    def test_get_user_habits_empty_history(self, agent, mock_db):
        """Test handling of empty workout history."""
        mock_db.get_workout_logs = Mock(return_value=[])

        habits = agent._get_user_habits("123456789", days=14)

        assert habits["top_activities"] == []
        assert habits["total_workouts"] == 0
        assert habits["avg_intensity"] == "unknown"
        assert habits["recent_trend"] == "unknown"

    def test_get_user_habits_intensity_high(self, agent, mock_db):
        """Test high intensity classification."""
        mock_logs = [
            {"exercise_name": "HIIT", "duration_min": 25, "kcal_estimate": 300, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Running", "duration_min": 30, "kcal_estimate": 350, "status": "completed", "created_at": datetime.now().isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)

        habits = agent._get_user_habits("123456789", days=14)

        # High intensity: > 200 kcal per 30 min
        assert habits["avg_intensity"] == "high"

    def test_get_user_habits_intensity_low(self, agent, mock_db):
        """Test low intensity classification."""
        mock_logs = [
            {"exercise_name": "Stretching", "duration_min": 20, "kcal_estimate": 50, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 80, "status": "completed", "created_at": datetime.now().isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)

        habits = agent._get_user_habits("123456789", days=14)

        # Low intensity: < 100 kcal per 30 min
        assert habits["avg_intensity"] == "low"

    def test_get_user_habits_trend_increasing(self, agent, mock_db):
        """Test increasing trend detection."""
        now = datetime.now()
        mock_logs = [
            # Recent (last 3 days) - 3 workouts
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": now.isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": (now - timedelta(days=1)).isoformat()},
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": (now - timedelta(days=2)).isoformat()},
            # Older (5+ days ago) - 1 workout
            {"exercise_name": "Running", "duration_min": 30, "kcal_estimate": 200, "status": "completed", "created_at": (now - timedelta(days=7)).isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)

        habits = agent._get_user_habits("123456789", days=14)

        # 3 recent vs 1 older = increasing trend
        assert habits["recent_trend"] == "increasing"

    def test_get_user_habits_db_error(self, agent, mock_db):
        """Test graceful handling of database errors."""
        mock_db.get_workout_logs = Mock(side_effect=Exception("Connection timeout"))

        habits = agent._get_user_habits("123456789", days=14)

        # Should return default/unknown values
        assert habits["avg_intensity"] == "unknown"
        assert habits["recent_trend"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Unit tests for Fitness Agent v6.3 Preference Learning.

Tests:
1. User habits extraction from workout logs
2. Top activities frequency counting
3. Intensity classification
4. Recent trend detection
5. Empty history handling
6. Empathy strategy conflict detection
7. Empathy message generation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestFitnessAgentV63:
    """Test suite for v6.3 Preference Learning."""

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
            "restrictions": ""
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

    # ============================================
    # User Habits Tests
    # ============================================

    def test_get_user_habits_success(self, agent, mock_db):
        """Test successful habit extraction from workout logs."""
        # Mock workout logs with variety
        mock_logs = [
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "HIIT", "duration_min": 45, "kcal_estimate": 300, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)

        habits = agent._get_user_habits("123456789", days=14)
        # Verify top activities (Yoga appears twice, Walking twice, HIIT once)
        assert "Yoga" in habits["top_activities"]
        assert "Walking" in habits["top_activities"]
        assert habits["total_workouts"] == 5
        assert habits["avg_duration_min"] > 0
        assert habits["avg_intensity"] in ["low", "moderate", "high"]

    def test_get_user_habits_empty_history(self, agent, mock_db):
        """Test handling of empty workout history."""
        mock_db.get_workout_logs = Mock(return_value=[])
        habits = agent._get_user_habits("123456789", days=14)
        assert habits["top_activities"] == []
        assert habits["total_workouts"] == 0
        assert habits["avg_intensity"] == "unknown"
        assert habits["recent_trend"] == "unknown"

    def test_get_user_habits_intensity_high(self, agent, mock_db):
        """Test high intensity classification."""
        mock_logs = [
            {"exercise_name": "HIIT", "duration_min": 30, "kcal_estimate": 300, "status": "completed", "created_at": datetime.now().isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)
        habits = agent._get_user_habits("123456789", days=14)
        # High intensity: >= 200 kcal per 30 min
        assert habits["avg_intensity"] == "high"
        assert len(habits["top_activities"]) == 1
        assert "HIIT" in habits["top_activities"]

    def test_get_user_habits_intensity_low(self, agent, mock_db):
        """Test low intensity classification."""
        mock_logs = [
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 80, "status": "completed", "created_at": datetime.now().isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)
        habits = agent._get_user_habits("123456789", days=14)
        # Low intensity: < 100 kcal per 30 min
        assert habits["avg_intensity"] == "low"
        assert len(habits["top_activities"]) == 1
        assert "Walking" in habits["top_activities"]

    def test_get_user_habits_trend_increasing(self, agent, mock_db):
        """Test increasing trend detection."""
        now = datetime.now()
        mock_logs = [
            # Recent (last 3 days) - 3 workouts
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": now.isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": (now - timedelta(days=1)).isoformat()},
            {"exercise_name": "Yoga", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": (now - timedelta(days=7)).isoformat()},
        ]
        mock_db.get_workout_logs = Mock(return_value=mock_logs)
        habits = agent._get_user_habits("123456789", days=14)
        assert habits["recent_trend"] == "increasing"
        assert len(habits["top_activities"]) == 2
        assert "Yoga" in habits["top_activities"]

    def test_get_user_habits_db_error(self, agent, mock_db):
        """Test graceful handling of database errors."""
        mock_db.get_workout_logs = Mock(side_effect=Exception("Connection timeout"))
        habits = agent._get_user_habits("123456789", days=14)
        # Should return default/unknown values
        assert habits["avg_intensity"] == "unknown"
        assert habits["recent_trend"] == "unknown"

    # ============================================
    # Empathy Strategy Tests (v6.3)
    # ============================================

    def test_empathy_preference_vs_safety(self, agent, mock_db):
        """Test empathy strategy when preference conflicts with safety."""
        # User likes HIIT but ate fried food
        user_habits = {"top_activities": ["HIIT", "Running"], "avg_intensity": "high", "total_workouts": 10}
        budget_progress = {"status": "good", "remaining_pct": 60.0}
        visual_warnings = ["fried", "high_oil"]

        strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings)

        assert strategy["conflict_type"] == "preference_vs_safety"
        assert strategy["intensity_modifier"] == "reduce"
        assert "HIIT" in strategy["empathy_message"]
        # Check for switching/alternative keywords (message uses "switching" not "pivot")
        assert "switch" in strategy["empathy_message"].lower()
        assert strategy["suggested_pivot"] is not None

    def test_empathy_preference_vs_budget(self, agent, mock_db):
        """Test empathy strategy when preference conflicts with budget."""
        # User likes running but budget is critical
        user_habits = {"top_activities": ["Running", "Jogging"], "avg_intensity": "moderate", "total_workouts": 8}
        budget_progress = {"status": "critical", "remaining_pct": 25.0}
        visual_warnings = []

        strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings)

        assert strategy["conflict_type"] == "preference_vs_budget"
        assert strategy["intensity_modifier"] == "reduce"
        assert "budget" in strategy["empathy_message"].lower()
        assert strategy["suggested_pivot"] is not None

    def test_empathy_habit_vs_goal(self, agent, mock_db):
        """Test empathy strategy for sedentary user with good budget."""
        # Sedentary user with plenty of budget
        user_habits = {"top_activities": [], "avg_intensity": "low", "total_workouts": 2}
        budget_progress = {"status": "good", "remaining_pct": 75.0}
        visual_warnings = []

        strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings)

        assert strategy["conflict_type"] == "habit_vs_goal"
        assert strategy["intensity_modifier"] == "increase"
        assert "foundation" in strategy["empathy_message"].lower()
        assert strategy["suggested_pivot"] is not None

    def test_empathy_no_conflict(self, agent, mock_db):
        """Test when there's no conflict - normal flow."""
        # Active user, good budget, no warnings
        user_habits = {"top_activities": ["Yoga", "Walking"], "avg_intensity": "moderate", "total_workouts": 10}
        budget_progress = {"status": "good", "remaining_pct": 60.0}
        visual_warnings = []

        strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings)

        assert strategy["conflict_type"] is None
        assert strategy["intensity_modifier"] == "maintain"
        assert strategy["empathy_message"] == ""
        assert strategy["suggested_pivot"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
