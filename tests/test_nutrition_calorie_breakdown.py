"""Tests for per-item calorie breakdown generation and display normalization."""

from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.discord_bot.bot import HealthButlerDiscordBot


def test_nutrition_breakdown_aggregates_same_item_quantity() -> None:
    """Nutrition agent should produce quantity-aware subtotal for repeated same item."""
    agent = NutritionAgent.__new__(NutritionAgent)

    items = [
        {
            "name": "Avocado",
            "portion": "x2",
            "estimated_weight_grams": 70,
            "macros": {"calories": 120},
        }
    ]
    rag_matches = [
        {
            "original_item": "Avocado",
            "name": "Avocado, raw",
            "calories": 160,
        }
    ]

    rows = agent._build_calorie_breakdown(items, rag_matches)

    assert len(rows) == 1
    assert rows[0]["item"] == "Avocado"
    assert rows[0]["quantity"] == 2
    assert rows[0]["calories_each"] == 112.0
    assert rows[0]["calories_total"] == 224.0


def test_discord_breakdown_rows_aggregate_duplicates() -> None:
    """Discord view helper should aggregate duplicate items and compute overall quantities."""
    bot = HealthButlerDiscordBot.__new__(HealthButlerDiscordBot)

    rows = bot._calorie_breakdown_rows(
        {
            "calorie_breakdown": [
                {"item": "Egg", "quantity": 1, "calories_each": 78, "calories_total": 78},
                {"item": "Egg", "quantity": 2, "calories_each": 78, "calories_total": 156},
            ]
        }
    )

    assert len(rows) == 1
    assert rows[0]["item"] == "Egg"
    assert rows[0]["quantity"] == 3
    assert rows[0]["calories_total"] == 234.0
    assert rows[0]["calories_each"] == 78.0
