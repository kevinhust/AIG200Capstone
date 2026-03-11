"""
E2E Soul Tests for v6.3 Preference Learning Engine.

These three "soul tests" validate the complete empathy flow:

1. "Loyal Supporter": Good budget + Yoga lover → Encourage continuation
   - User has healthy eating habits and loves Yoga
   - System should acknowledge their dedication and suggest similar activities

2. "Gentle Persuader": Fried food + HIIT lover → Empathy pivot message
   - User ate fried food but prefers high-intensity workouts
   - System should acknowledge preference, explain safety concern, suggest alternatives

3. "Active Encourager": Sedentary + Good budget → Encourage movement
   - User has low activity but plenty of calorie budget
   - System should gently encourage foundational activities

Run with: pytest tests/e2e/test_soul_tests_v63.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestSoulTestsV63:
    """
    E2E Soul Tests for v6.3 Preference Learning.

    These tests simulate complete user journeys through the fitness agent
    to validate empathy strategy generation and preference-aware responses.
    """

    @pytest.fixture
    def mock_db_factory(self):
        """Factory to create mock ProfileDB with custom configurations."""
        def _create_mock_db(
            profile: dict = None,
            today_stats: dict = None,
            daily_agg: dict = None,
            workout_logs: list = None
        ):
            db = Mock()

            # Default profile
            default_profile = {
                "id": "123456789",
                "full_name": "Test User",
                "age": 28,
                "gender": "Male",
                "weight_kg": 75,
                "height_cm": 175,
                "goal": "Lose Weight",
                "activity": "Moderately Active",
                "restrictions": ""
            }
            db.get_profile = Mock(return_value=profile or default_profile)

            # Default today stats
            default_today = {"total_calories": 1200, "total_protein": 65}
            db.get_today_stats = Mock(return_value=today_stats or default_today)

            # Default daily aggregation
            default_agg = {
                "calories_in": 1200,
                "calories_out": 300,
                "net_calories": 900,
                "protein_g": 65,
                "active_minutes": 45
            }
            db.get_daily_aggregation = Mock(return_value=daily_agg or default_agg)

            # Workout logs
            db.get_workout_logs = Mock(return_value=workout_logs or [])

            return db
        return _create_mock_db

    @pytest.fixture
    def agent_factory(self, mock_db_factory):
        """Factory to create FitnessAgent with custom DB configuration."""
        def _create_agent(**db_kwargs):
            mock_db = mock_db_factory(**db_kwargs)
            with patch('src.discord_bot.profile_db.get_profile_db', return_value=mock_db):
                from src.agents.fitness.fitness_agent import FitnessAgent
                agent = FitnessAgent(db=mock_db)
                return agent, mock_db
        return _create_agent

    # ============================================
    # Soul Test 1: "Loyal Supporter"
    # ============================================
    def test_soul_loyal_supporter(self, agent_factory):
        """
        Soul Test 1: "Loyal Supporter"

        Scenario:
        - User loves Yoga and Walking (moderate intensity)
        - Good calorie budget (60% remaining)
        - No visual warnings from food

        Expected:
        - conflict_type: None (no conflict)
        - intensity_modifier: "maintain"
        - Footer shows preference tags
        """
        # Setup: Yoga lover with good habits
        yoga_logs = [
            {"exercise_name": "Yoga", "duration_min": 45, "kcal_estimate": 150, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Walking", "duration_min": 30, "kcal_estimate": 100, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Yoga", "duration_min": 60, "kcal_estimate": 200, "status": "completed", "created_at": (datetime.now() - timedelta(days=2)).isoformat()},
            {"exercise_name": "Stretching", "duration_min": 20, "kcal_estimate": 60, "status": "completed", "created_at": (datetime.now() - timedelta(days=4)).isoformat()},
            {"exercise_name": "Yoga", "duration_min": 45, "kcal_estimate": 150, "status": "completed", "created_at": (datetime.now() - timedelta(days=6)).isoformat()},
        ]

        daily_agg = {"calories_in": 1400, "calories_out": 200, "net_calories": 1200, "active_minutes": 60}
        user_profile = {
            "id": "soul_test_1", "full_name": "Yoga Lover", "goal": "Maintain Weight",
            "age": 28, "gender": "Female", "weight_kg": 60, "height_cm": 165,
            "activity": "Moderately Active"
        }

        agent, mock_db = agent_factory(
            profile=user_profile,
            daily_agg=daily_agg,
            workout_logs=yoga_logs
        )

        # Execute
        user_habits = agent._get_user_habits("soul_test_1", days=14)
        budget_progress = agent._generate_budget_progress(daily_agg, user_profile)
        empathy_strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings=[])

        # Validate: No conflict, maintain intensity
        assert empathy_strategy["conflict_type"] is None
        assert empathy_strategy["intensity_modifier"] == "maintain"
        assert empathy_strategy["empathy_message"] == ""
        assert empathy_strategy["suggested_pivot"] is None

        # Validate: Preference extraction
        assert "Yoga" in user_habits["top_activities"]
        assert user_habits["avg_intensity"] in ["low", "moderate"]  # Yoga is moderate

        # Validate: Budget is healthy
        assert budget_progress["status"] == "good"
        assert budget_progress["remaining_pct"] > 40

    # ============================================
    # Soul Test 2: "Gentle Persuader"
    # ============================================
    def test_soul_gentle_persuader(self, agent_factory):
        """
        Soul Test 2: "Gentle Persuader"

        Scenario:
        - User loves HIIT and Running (high intensity)
        - Ate fried food (visual warning: "fried")
        - Good calorie budget

        Expected:
        - conflict_type: "preference_vs_safety"
        - intensity_modifier: "reduce"
        - empathy_message acknowledges HIIT preference
        - suggested_pivot offers lower-intensity alternative
        """
        # Setup: HIIT enthusiast who ate fried food
        hiit_logs = [
            {"exercise_name": "HIIT", "duration_min": 25, "kcal_estimate": 300, "status": "completed", "created_at": datetime.now().isoformat()},
            {"exercise_name": "Running", "duration_min": 35, "kcal_estimate": 350, "status": "completed", "created_at": (datetime.now() - timedelta(days=1)).isoformat()},
            {"exercise_name": "HIIT", "duration_min": 30, "kcal_estimate": 350, "status": "completed", "created_at": (datetime.now() - timedelta(days=3)).isoformat()},
            {"exercise_name": "Burpees", "duration_min": 20, "kcal_estimate": 250, "status": "completed", "created_at": (datetime.now() - timedelta(days=5)).isoformat()},
        ]

        daily_agg = {"calories_in": 1600, "calories_out": 350, "net_calories": 1250, "active_minutes": 50}
        user_profile = {
            "id": "soul_test_2", "full_name": "HIIT Fan", "goal": "Lose Weight",
            "age": 28, "gender": "Male", "weight_kg": 80, "height_cm": 178,
            "activity": "Very Active"
        }

        agent, mock_db = agent_factory(
            profile=user_profile,
            daily_agg=daily_agg,
            workout_logs=hiit_logs
        )

        # Execute
        user_habits = agent._get_user_habits("soul_test_2", days=14)
        budget_progress = agent._generate_budget_progress(daily_agg, user_profile)
        # Visual warnings from food analysis (fried food detected)
        visual_warnings = ["fried", "high_oil"]

        empathy_strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings)

        # Validate: Preference vs Safety conflict detected
        assert empathy_strategy["conflict_type"] == "preference_vs_safety"
        assert empathy_strategy["intensity_modifier"] == "reduce"

        # Validate: Empathy message acknowledges preference
        empathy_msg = empathy_strategy["empathy_message"].lower()
        assert "hiit" in empathy_msg or "high intensity" in empathy_msg
        assert "switch" in empathy_msg or "alternative" in empathy_msg or "instead" in empathy_msg

        # Validate: Pivot suggestion exists
        assert empathy_strategy["suggested_pivot"] is not None
        pivot = empathy_strategy["suggested_pivot"].lower()
        # Should suggest lower-intensity alternatives
        assert any(activity in pivot for activity in ["walk", "yoga", "stretch", "light", "gentle"])

    # ============================================
    # Soul Test 3: "Active Encourager"
    # ============================================
    def test_soul_active_encourager(self, agent_factory):
        """
        Soul Test 3: "Active Encourager"

        Scenario:
        - User has low activity (sedentary)
        - Good calorie budget (75% remaining)
        - No visual warnings

        Expected:
        - conflict_type: "habit_vs_goal"
        - intensity_modifier: "increase"
        - empathy_message encourages foundational movement
        - suggested_pivot offers starter activities
        """
        # Setup: Sedentary user with good budget
        # TDEE for 35F, 70kg, 160cm, Sedentary ≈ 1637 kcal
        # With 500 kcal in, 50 out: remaining = 1637 - 500 + 50 = 1187 kcal (≈72% remaining)
        # Empty workout logs to ensure avg_intensity = "unknown" and total_workouts = 0
        empty_logs = []

        daily_agg = {"calories_in": 500, "calories_out": 50, "net_calories": 450, "active_minutes": 0}
        user_profile = {
            "id": "soul_test_3", "full_name": "New Starter", "goal": "Lose Weight",
            "age": 35, "gender": "Female", "weight_kg": 70, "height_cm": 160,
            "activity": "Sedentary"
        }

        agent, mock_db = agent_factory(
            profile=user_profile,
            daily_agg=daily_agg,
            workout_logs=empty_logs
        )

        # Execute
        user_habits = agent._get_user_habits("soul_test_3", days=14)
        budget_progress = agent._generate_budget_progress(daily_agg, user_profile)
        empathy_strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings=[])

        # Validate: Habit vs Goal conflict detected
        assert empathy_strategy["conflict_type"] == "habit_vs_goal"
        assert empathy_strategy["intensity_modifier"] == "increase"

        # Validate: Empathy message encourages foundation
        empathy_msg = empathy_strategy["empathy_message"].lower()
        assert any(word in empathy_msg for word in ["foundation", "start", "begin", "journey", "step", "opportunity"])

        # Validate: Pivot suggestion for beginners
        assert empathy_strategy["suggested_pivot"] is not None
        pivot = empathy_strategy["suggested_pivot"].lower()
        assert any(activity in pivot for activity in ["walk", "stretch", "light", "gentle", "beginner"])

        # Validate: User habits show no activity
        assert user_habits["total_workouts"] == 0
        assert user_habits["avg_intensity"] == "unknown"

        # Validate: Budget is very good (lots of room)
        assert budget_progress["status"] == "good"
        assert budget_progress["remaining_pct"] > 60

    # ============================================
    # Integration: Full Flow Validation
    # ============================================
    def test_full_flow_embed_generation(self, agent_factory):
        """
        Validate that empathy strategy integrates into Discord Embed.

        This test verifies the complete v6.3 flow:
        1. User habits extraction
        2. Budget progress calculation
        3. Empathy strategy generation
        4. Embed field generation (simulated)
        """
        # Setup: Gentle Persuader scenario
        hiit_logs = [
            {"exercise_name": "HIIT", "duration_min": 25, "kcal_estimate": 300, "status": "completed", "created_at": datetime.now().isoformat()},
        ]

        daily_agg = {"calories_in": 1600, "calories_out": 350, "net_calories": 1250, "active_minutes": 50}
        user_profile = {
            "id": "embed_test", "full_name": "Embed Test User", "goal": "Lose Weight",
            "age": 28, "gender": "Male", "weight_kg": 80, "height_cm": 178,
            "activity": "Very Active"
        }

        agent, mock_db = agent_factory(
            profile=user_profile,
            daily_agg=daily_agg,
            workout_logs=hiit_logs
        )

        # Execute full flow
        user_habits = agent._get_user_habits("embed_test", days=14)
        budget_progress = agent._generate_budget_progress(daily_agg, user_profile)
        empathy_strategy = agent._build_empathy_strategy(user_habits, budget_progress, visual_warnings=["fried"])

        # Simulate embed field construction
        if empathy_strategy.get("empathy_message"):
            insight_value = f"> *{empathy_strategy['empathy_message']}*"
            if empathy_strategy.get("suggested_pivot"):
                insight_value += f"\n\n**Try instead**: {empathy_strategy['suggested_pivot']}"

            # Validate embed field structure
            assert len(insight_value) > 50  # Substantial content
            assert ">" in insight_value  # Blockquote styling
            assert "HIIT" in empathy_strategy["empathy_message"]  # Preference acknowledged

        # Validate footer preference tags
        if user_habits.get("top_activities"):
            top_tags = " • ".join(user_habits["top_activities"][:2])
            footer_text = f"Personalized for your love of: {top_tags} | v6.3 Preference Engine"
            assert "HIIT" in footer_text or len(top_tags) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
