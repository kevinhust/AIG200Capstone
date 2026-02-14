import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock


from health_butler.discord_bot import bot as discord_bot


def test_apply_serving_multiplier_scales_macros_and_breakdown() -> None:
    payload = {
        "dish_name": "Test Meal",
        "total_macros": {"calories": 200, "protein": 10, "carbs": 20, "fat": 5},
        "calorie_breakdown": [
            {"item": "Egg", "quantity": 2, "calories_each": 50, "calories_total": 100},
            {"item": "Toast", "quantity": 1, "calories_each": 100, "calories_total": 100},
        ],
    }

    out = discord_bot._apply_serving_multiplier(payload, 2.0)

    assert out["dish_name"] == "Test Meal"
    assert out["total_macros"]["calories"] == 400.0
    assert out["total_macros"]["protein"] == 20.0
    assert out["total_macros"]["carbs"] == 40.0
    assert out["total_macros"]["fat"] == 10.0

    rows = out["calorie_breakdown"]
    assert rows[0]["calories_each"] == 100.0
    assert rows[0]["calories_total"] == 200.0
    assert rows[1]["calories_each"] == 200.0
    assert rows[1]["calories_total"] == 200.0

    assert out["serving_multiplier"] == 2.0


def test_apply_serving_multiplier_can_be_updated_multiple_times_without_compounding() -> None:
    payload = {
        "dish_name": "Test Meal",
        "total_macros": {"calories": 200, "protein": 10, "carbs": 20, "fat": 5},
        "calorie_breakdown": [
            {"item": "Egg", "quantity": 2, "calories_each": 50, "calories_total": 100},
        ],
    }

    discord_bot._apply_serving_multiplier(payload, 2.0)
    assert payload["total_macros"]["calories"] == 400.0

    discord_bot._apply_serving_multiplier(payload, 1.0)
    assert payload["total_macros"]["calories"] == 200.0
    assert payload["calorie_breakdown"][0]["calories_total"] == 100.0
    assert payload["serving_multiplier"] == 1.0


def test_meal_log_view_apply_multiplier_updates_db_when_logged() -> None:
    original_db = discord_bot.profile_db
    mock_db = MagicMock()
    discord_bot.profile_db = mock_db

    async def _noop(*_args, **_kwargs):
        return None

    try:
        bot = MagicMock()
        bot._send_daily_summary_embed = _noop

        view = discord_bot.MealLogView(
            bot,
            user_id="123",
            nutrition_payload={
                "dish_name": "Pasta",
                "total_macros": {"calories": 300, "protein": 12, "carbs": 55, "fat": 7},
            },
            logged_meal={"meal_id": "m-1"},
        )

        # Avoid touching discord message edit in this unit test.
        view._refresh_message_embed = _noop

        interaction = SimpleNamespace(
            response=SimpleNamespace(send_message=_noop),
            channel=None,
            user=SimpleNamespace(id=123),
        )

        asyncio.run(view.apply_multiplier(interaction, 0.5))

        args, kwargs = mock_db.update_meal.call_args
        assert args[0] == "m-1"
        assert kwargs["dish_name"] == "Pasta"
        assert kwargs["calories"] == 150.0
        assert kwargs["protein_g"] == 6.0
        assert kwargs["carbs_g"] == 27.5
        assert kwargs["fat_g"] == 3.5
    finally:
        discord_bot.profile_db = original_db

