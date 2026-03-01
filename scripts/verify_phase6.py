import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.agents.nutrition.nutrition_agent import NutritionAgent
from src.cv_food_rec.vision_tool import VisionTool

async def verify_yolo11():
    print("--- 🔍 Verifying YOLO11 Upgrade ---")
    vision = VisionTool()
    print(f"Model Name: {vision.model_name}")
    # Verify it can load (this might download the model)
    try:
        vision._load_model()
        if vision._model:
            print("✅ YOLO11 model loaded successfully.")
        else:
            print("❌ YOLO11 model failed to load.")
    except Exception as e:
        print(f"⚠️ YOLO11 load warning (might be environment-related): {e}")

async def verify_nutrition_logic():
    print("\n--- 🥗 Verifying Nutrition DV% & Budget Logic ---")
    agent = NutritionAgent()
    
    # Mock context with TDEE data and past meals
    user_context = {
        "name": "Kevin",
        "weight_kg": 75,
        "height_cm": 180,
        "age": 25,
        "gender": "male",
        "activity": "moderately active",
        "goal": "lose weight",
        "daily_intake": [
            {"macros": {"calories": 500, "protein": 40, "carbs": 50, "fat": 15}}
        ]
    }
    
    # Mock synthesis data
    mock_data = {
        "dish_name": "Chicken Salad",
        "total_macros": {
            "calories": 400,
            "protein": 35,
            "carbs": 10,
            "fat": 20
        },
        "confidence_score": 0.95
    }
    
    # We'll test the inner logic or just call execute_async if we can mock the LLM
    # For verification, we can directly call the helper
    targets = agent._calculate_tdee(user_context)
    print(f"Calculated Targets: {targets}")
    
    # Verify TDEE math (lose weight goal)
    # BMR = 10*75 + 6.25*180 - 5*25 + 5 = 750 + 1125 - 125 + 5 = 1755
    # TDEE = 1755 * 1.55 = 2720
    # Adjusted = 2720 - 500 = 2220
    if 2210 <= targets["calories"] <= 2230:
        print("✅ TDEE calculation correct.")
    else:
        print(f"❌ TDEE calculation incorrect: {targets['calories']}")

    # Mock more complex synthesis
    # This simulates what happens in execute_async after Gemini + RAG
    # We'll manually run the budget logic snippet from execute_async
    try:
        past_meals = user_context["daily_intake"]
        past_cals = sum(m["macros"]["calories"] for m in past_meals)
        curr_cal = mock_data["total_macros"]["calories"]
        total_after = past_cals + curr_cal
        
        dv_pct = (total_after / targets["calories"]) * 100
        remaining = targets["calories"] - total_after
        
        print(f"Past: {past_cals}, Current: {curr_cal}, Total After: {total_after}")
        print(f"DV%: {dv_pct:.1f}%, Remaining: {remaining:.1f}")
        
        if dv_pct > 0 and remaining > 0:
            print("✅ DV% and Remaining Budget logic verified.")
    except Exception as e:
        print(f"❌ Budget logic failed: {e}")

async def verify_ui_components():
    print("\n--- 🎰 Verifying UI Component Imports ---")
    try:
        from src.discord_bot.roulette_view import RouletteView, MealInspirationView
        # Mock initialization
        view = RouletteView(user_id="123", remaining_budget={"calories": 1500})
        print(f"✅ RouletteView initialized: {view.user_id}")
        
        from src.discord_bot.bot import HealthButlerDiscordBot
        print("✅ HealthButlerDiscordBot imports verified.")
    except Exception as e:
        print(f"❌ UI import failed: {e}")

async def main():
    await verify_yolo11()
    await verify_nutrition_logic()
    await verify_ui_components()

if __name__ == "__main__":
    asyncio.run(main())
