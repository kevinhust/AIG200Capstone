"""Live Supabase smoke test for Discord persistence paths.

This test is intentionally integration-only and runs only when the required
Supabase environment variables are present.
"""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest


def _supabase_env_ready() -> bool:
    """Return True only when connection credentials are available."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return bool(url and key)


@pytest.mark.skipif(not _supabase_env_ready(), reason="Supabase env vars are not set")
def test_supabase_live_persistence_smoke() -> None:
    """Verify real inserts for profile/chat/daily/meals/workout tables with cleanup.

    The flow mirrors demo + message persistence in a minimal way:
    1) Create profile
    2) Save chat message
    3) Upsert daily log
    4) Insert meal
    5) Insert workout log
    6) Insert routine item
    7) Assert each row exists and type-shape is compatible
    8) Cleanup all inserted rows
    """
    pytest.importorskip("supabase")
    from health_butler.discord_bot.profile_db import get_profile_db

    db = get_profile_db()
    test_user_id = f"it-smoke-{uuid.uuid4().hex[:12]}"

    try:
        profile = db.create_profile(
            discord_user_id=test_user_id,
            full_name="Integration Smoke User",
            age=31,
            gender="Male",
            height_cm=178.5,
            weight_kg=82.2,
            goal="Maintain",
            conditions=["None"],
            activity="Moderately Active",
            diet=["None"],
        )
        assert profile is not None
        assert profile.get("id") == test_user_id
        assert isinstance(profile.get("age"), int)

        msg = db.save_message(
            discord_user_id=test_user_id,
            role="user",
            content="Integration smoke message",
        )
        assert msg is not None
        assert msg.get("user_id") == test_user_id
        assert msg.get("role") == "user"
        assert isinstance(msg.get("content"), str)

        daily = db.create_daily_log(
            discord_user_id=test_user_id,
            log_date=date.today(),
            calories_intake=510.7,
            protein_g=24.2,
            steps_count=3200,
        )
        assert daily is not None
        assert daily.get("user_id") == test_user_id
        assert float(daily.get("calories_intake", 0)) > 0
        assert float(daily.get("protein_g", 0)) > 0
        assert int(daily.get("steps_count", 0)) == 3200

        meal = db.create_meal(
            discord_user_id=test_user_id,
            dish_name="Avocado",
            calories=299.0,
            protein_g=1.3,
            carbs_g=5.2,
            fat_g=30.3,
            confidence_score=0.9,
        )
        assert meal is not None
        assert meal.get("user_id") == test_user_id
        assert meal.get("dish_name") == "Avocado"
        assert float(meal.get("calories", 0)) == pytest.approx(299.0)
        assert float(meal.get("confidence_score", 0)) == pytest.approx(0.9)

        workout = db.log_workout_event(
            discord_user_id=test_user_id,
            exercise_name="Walking",
            duration_min=20,
            kcal_estimate=95.0,
            status="completed",
            source="integration_smoke_test",
            raw_payload={"origin": "pytest"},
        )
        assert workout is not None
        assert workout.get("user_id") == test_user_id
        assert int(workout.get("duration_min", 0)) == 20
        assert float(workout.get("kcal_estimate", 0)) == pytest.approx(95.0)

        routine = db.add_routine_exercise(
            discord_user_id=test_user_id,
            exercise_name="Walking",
            target_per_week=4,
            metadata={"origin": "pytest"},
        )
        assert routine is not None
        assert routine.get("user_id") == test_user_id
        assert routine.get("exercise_name") == "Walking"
        assert int(routine.get("target_per_week", 0)) == 4

        progress = db.get_workout_progress(test_user_id, days=7)
        assert isinstance(progress, dict)
        assert progress.get("routine_count", 0) >= 1

    finally:
        # Child tables first due FK constraints, then profile.
        db.client.table("workout_logs").delete().eq("user_id", test_user_id).execute()
        db.client.table("workout_routines").delete().eq("user_id", test_user_id).execute()
        db.client.table("meals").delete().eq("user_id", test_user_id).execute()
        db.client.table("daily_logs").delete().eq("user_id", test_user_id).execute()
        db.client.table("chat_messages").delete().eq("user_id", test_user_id).execute()
        db.client.table("profiles").delete().eq("id", test_user_id).execute()
