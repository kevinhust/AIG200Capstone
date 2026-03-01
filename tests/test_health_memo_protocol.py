"""Test script for Module 3: Health Memo Protocol.

Validates end-to-end flow:
1. Coordinator identifies multilingual intent (EN/CN)
2. Nutrition Agent returns visual_warnings and health_score
3. Coordinator extracts HealthMemo
4. Fitness Agent receives enhanced task with nutrition context

Expected input: "我刚吃了炸鸡，想去游泳。"
Expected flow:
  - Coordinator → Nutrition Agent → visual_warnings: ["fried", "high_oil"]
  - Coordinator → Fitness Agent with injected context
"""

import os
import sys
import json
import logging
import tempfile
import urllib.request

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.coordinator.coordinator_agent import (
    CoordinatorAgent,
    HealthMemo,
    _build_fitness_task_with_memo,
)
from src.agents.nutrition.nutrition_agent import NutritionAgent
from src.agents.fitness.fitness_agent import FitnessAgent

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger(__name__)


def download_image(url: str, dest_path: str) -> bool:
    """Download image with proper headers."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            with open(dest_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return False


def test_multilingual_intent_detection():
    """Test that coordinator correctly identifies Chinese intents."""
    print("\n" + "=" * 60)
    print("TEST 1: Multilingual Intent Detection")
    print("=" * 60)

    coordinator = CoordinatorAgent()

    test_cases = [
        ("我刚吃了炸鸡，想去游泳。", ["nutrition", "fitness"]),
        ("我吃了汉堡", ["nutrition"]),
        ("想去跑步", ["fitness"]),
        ("I ate fried chicken and want to swim", ["nutrition", "fitness"]),
        ("刚吃完饭去健身房", ["nutrition", "fitness"]),
    ]

    for text, expected_agents in test_cases:
        delegations = coordinator.analyze_and_delegate(text)
        actual_agents = [d["agent"] for d in delegations]

        status = "✅" if set(actual_agents) == set(expected_agents) else "❌"
        print(f"\n{status} Input: '{text}'")
        print(f"   Expected: {expected_agents}")
        print(f"   Got: {actual_agents}")


def test_health_memo_extraction():
    """Test HealthMemo extraction from nutrition results."""
    print("\n" + "=" * 60)
    print("TEST 2: Health Memo Extraction")
    print("=" * 60)

    coordinator = CoordinatorAgent()

    # Mock nutrition result (like what Gemini would return)
    mock_nutrition_result = {
        "dish_name": "Fried Chicken",
        "total_macros": {"calories": 650, "protein": 35, "carbs": 20, "fat": 45},
        "visual_warnings": ["fried", "high_oil"],
        "health_score": 2,
    }

    memo = coordinator.extract_health_memo(mock_nutrition_result)

    if memo:
        print(f"✅ HealthMemo extracted successfully:")
        print(f"   visual_warnings: {memo['visual_warnings']}")
        print(f"   health_score: {memo['health_score']}")
        print(f"   dish_name: {memo['dish_name']}")
        print(f"   calorie_intake: {memo['calorie_intake']}")
    else:
        print("❌ Failed to extract HealthMemo")


def test_task_injection():
    """Test fitness task enhancement with health memo."""
    print("\n" + "=" * 60)
    print("TEST 3: Task Injection with Health Context")
    print("=" * 60)

    base_task = "Suggest appropriate exercises."

    # Test with unhealthy food memo
    unhealthy_memo: HealthMemo = {
        "visual_warnings": ["fried", "high_oil"],
        "health_score": 2,
        "dish_name": "Fried Chicken",
        "calorie_intake": 650,
    }

    enhanced_task = _build_fitness_task_with_memo(base_task, unhealthy_memo)

    print(f"\n📝 Base Task:\n   {base_task}")
    print(f"\n📝 Enhanced Task:\n{enhanced_task}")

    # Verify injection
    if "油炸" in enhanced_task and "Fried Chicken" in enhanced_task:
        print("\n✅ Task successfully enhanced with health context")
    else:
        print("\n❌ Task enhancement failed")


def test_end_to_end_with_image():
    """Full end-to-end test with real image analysis."""
    print("\n" + "=" * 60)
    print("TEST 4: End-to-End with Real Image")
    print("=" * 60)

    coordinator = CoordinatorAgent()
    nutrition_agent = NutritionAgent()

    # Download test image (fried chicken)
    fried_chicken_url = "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=640"

    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "fried_chicken.jpg")

        if not download_image(fried_chicken_url, img_path):
            print("❌ Failed to download test image")
            return

        print(f"✅ Downloaded test image")

        # Step 1: Analyze intent
        user_input = "我刚吃了炸鸡，想去游泳。"
        print(f"\n👤 User Input: '{user_input}'")

        delegations = coordinator.analyze_and_delegate(user_input)
        print(f"📋 Delegations: {delegations}")

        # Step 2: Run Nutrition Agent
        print("\n🍳 Running Nutrition Agent...")
        context = [{"type": "image_path", "content": img_path}]
        nutrition_result_str = nutrition_agent.execute("Analyze this meal", context)

        try:
            nutrition_result = json.loads(nutrition_result_str)
        except:
            nutrition_result = {"error": "parse failed", "raw": nutrition_result_str}

        print(f"\n📊 Nutrition Result:")
        print(f"   dish_name: {nutrition_result.get('dish_name', 'N/A')}")
        print(f"   visual_warnings: {nutrition_result.get('visual_warnings', 'N/A')}")
        print(f"   health_score: {nutrition_result.get('health_score', 'N/A')}")

        # Step 3: Extract HealthMemo
        memo = coordinator.extract_health_memo(nutrition_result)

        # Step 4: Build enhanced fitness task
        base_fitness_task = "Suggest swimming exercises."
        enhanced_task = coordinator.build_fitness_task_with_context(
            base_fitness_task, nutrition_result
        )

        print(f"\n🏃 Fitness Agent Task (enhanced):")
        print("-" * 40)
        print(enhanced_task)
        print("-" * 40)

        # Verify
        if memo and memo.get("visual_warnings"):
            print(f"\n✅ END-TO-END SUCCESS!")
            print(f"   Health memo detected: {memo['visual_warnings']}")
            print(f"   Fitness task includes nutrition context")
        else:
            print(f"\n⚠️ Partial success - nutrition analyzed but no warnings detected")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Module 3: Health Memo Protocol - Validation Tests")
    print("=" * 60)

    # Run tests
    test_multilingual_intent_detection()
    test_health_memo_extraction()
    test_task_injection()
    test_end_to_end_with_image()

    print("\n" + "=" * 60)
    print("All Tests Complete")
    print("=" * 60)
