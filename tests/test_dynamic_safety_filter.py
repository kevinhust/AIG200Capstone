"""Test script for Module 3: Dynamic Safety Filtering.

Validates end-to-end flow with dynamic risk filtering:
1. FitnessAgent extracts visual warnings from Health Memo
2. SimpleRagTool filters high-intensity exercises based on dynamic_risks
3. BR-001 safety disclaimer is included when adjustments are made
4. Alternative low-intensity exercises are recommended

Expected input: "I just ate a donut, can I go for a 5km fast run?"
Expected result:
  - fried/high_sugar warnings detected
  - "Fast Run" blocked as unsafe
  - "Brisk Walking" or "Light Cycling" recommended
  - BR-001 disclaimer included
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

from src.agents.fitness.fitness_agent import FitnessAgent, BR001_DISCLAIMER, VISUAL_WARNING_PATTERNS
from src.data_rag.simple_rag_tool import SimpleRagTool, DYNAMIC_RISK_BLOCKS

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger(__name__)


def test_visual_warning_extraction():
    """Test extraction of visual warnings from task description."""
    print("\n" + "=" * 60)
    print("TEST 1: Visual Warning Extraction")
    print("=" * 60)

    agent = FitnessAgent()

    test_cases = [
        (
            "[Health Memo] Warnings: fried, high_oil. User ate fried chicken.",
            ["fried", "high_oil"]
        ),
        (
            "The user consumed deep-fried, high-sugar food.",
            ["fried", "high_sugar"]
        ),
        (
            "No warnings here, just a regular task.",
            []
        ),
        (
            "visual_warnings: ['fried', 'processed']",
            ["fried", "processed"]
        ),
    ]

    all_passed = True
    for task, expected in test_cases:
        result = agent._extract_visual_warnings_from_task(task)
        passed = set(result) == set(expected)
        status = "✅" if passed else "❌"
        if not passed:
            all_passed = False

        print(f"\n{status} Task: '{task[:50]}...'")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")

    return all_passed


def test_rag_dynamic_filtering():
    """Test SimpleRagTool dynamic risk filtering."""
    print("\n" + "=" * 60)
    print("TEST 2: RAG Dynamic Risk Filtering")
    print("=" * 60)

    rag = SimpleRagTool()

    # Test without dynamic risks
    print("\n📋 Query: 'fast run' (no dynamic risks)")
    result_normal = rag.get_safe_recommendations("fast run", [], dynamic_risks=None)
    print(f"   Safe exercises found: {len(result_normal['safe_exercises'])}")
    print(f"   Dynamic adjustments: {result_normal.get('dynamic_adjustments')}")

    # Test with fried risk
    print("\n📋 Query: 'fast run' (with fried risk)")
    result_fried = rag.get_safe_recommendations("fast run", [], dynamic_risks=["fried"])
    print(f"   Safe exercises found: {len(result_fried['safe_exercises'])}")
    print(f"   Safety warnings: {result_fried.get('safety_warnings')}")
    print(f"   Dynamic adjustments: {result_fried.get('dynamic_adjustments')}")

    # Test with high_sugar risk
    print("\n📋 Query: 'sprint' (with high_sugar risk)")
    result_sugar = rag.get_safe_recommendations("sprint", [], dynamic_risks=["high_sugar"])
    print(f"   Safe exercises found: {len(result_sugar['safe_exercises'])}")
    print(f"   Safety warnings: {result_sugar.get('safety_warnings')}")

    # Verify dynamic adjustments were made
    checks = [
        (result_fried.get('dynamic_adjustments') is not None, "Fried risk triggers adjustments"),
        (result_sugar.get('dynamic_adjustments') is not None, "High sugar risk triggers adjustments"),
    ]

    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        if not check:
            all_passed = False
        print(f"\n{status} {desc}")

    return all_passed


def test_recommendation_validation():
    """Test double-validation of recommendations against warnings."""
    print("\n" + "=" * 60)
    print("TEST 3: Recommendation Validation")
    print("=" * 60)

    agent = FitnessAgent()

    # Test recommendations with high-intensity activities
    recommendations = [
        {"name": "Fast Running", "duration_min": 30, "kcal_estimate": 300, "reason": "Cardio"},
        {"name": "HIIT Workout", "duration_min": 20, "kcal_estimate": 250, "reason": "Intensity"},
        {"name": "Walking", "duration_min": 30, "kcal_estimate": 100, "reason": "Light cardio"},
    ]

    warnings = ["fried", "high_oil"]

    validated, was_adjusted = agent._validate_recommendations_against_warnings(
        recommendations, warnings
    )

    print(f"\n📋 Original recommendations: {[r['name'] for r in recommendations]}")
    print(f"📋 Visual warnings: {warnings}")
    print(f"📋 Validated recommendations: {[r['name'] for r in validated]}")
    print(f"📋 Was adjusted: {was_adjusted}")

    # Verify high-intensity was replaced
    validated_names = [r['name'].lower() for r in validated]
    checks = [
        ("fast running" not in validated_names, "Fast Running blocked"),
        ("hiit" not in " ".join(validated_names).lower(), "HIIT blocked"),
        (was_adjusted, "Adjustment flag set"),
        (any("walking" in name.lower() or "brisk" in name.lower() for name in validated_names), "Low-intensity alternative offered"),
    ]

    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        if not check:
            all_passed = False
        print(f"{status} {desc}")

    return all_passed


def test_br001_disclaimer():
    """Test that BR-001 disclaimer is correctly included."""
    print("\n" + "=" * 60)
    print("TEST 4: BR-001 Safety Disclaimer")
    print("=" * 60)

    print(f"\n📋 BR-001 Disclaimer:")
    print(f"   {BR001_DISCLAIMER}")

    checks = [
        ("fried" in BR001_DISCLAIMER.lower() or "high-sugar" in BR001_DISCLAIMER.lower(),
         "Mentions food type"),
        ("adjusted" in BR001_DISCLAIMER.lower() or "lower intensity" in BR001_DISCLAIMER.lower(),
         "Mentions adjustment"),
        ("safety" in BR001_DISCLAIMER.lower(),
         "Mentions safety"),
    ]

    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        if not check:
            all_passed = False
        print(f"{status} {desc}")

    return all_passed


def test_end_to_end_donut_run():
    """Full end-to-end test with donut + fast run scenario."""
    print("\n" + "=" * 60)
    print("TEST 5: End-to-End - 'I just ate a donut, can I go for a 5km fast run?'")
    print("=" * 60)

    agent = FitnessAgent()

    # Simulate enhanced task from Coordinator with Health Memo
    enhanced_task = """[Health Memo - Nutrition Context]
The user has just consumed: Glazed Donut
Calories: ~450 kcal
Health warnings: deep-fried, high-sugar, processed
Health score: 2/10

The user has just consumed deep-fried, high-sugar, processed food (Warnings: fried, high_sugar, processed).
Please provide exercise recommendations with appropriate intensity adjustments and safety precautions.

Original task: Can I go for a 5km fast run?"""

    print(f"\n👤 Enhanced Task (from Coordinator):")
    print("-" * 50)
    print(enhanced_task[:200] + "...")
    print("-" * 50)

    # Execute
    result_str = agent.execute(enhanced_task)

    try:
        result = json.loads(result_str)
    except:
        print(f"❌ Failed to parse result as JSON")
        return False

    print(f"\n📊 Fitness Agent Result:")
    print(f"   Summary: {result.get('summary', 'N/A')[:100]}...")
    print(f"   Recommendations: {[r['name'] for r in result.get('recommendations', [])]}")
    print(f"   Safety Warnings: {result.get('safety_warnings', [])}")
    print(f"   Avoid: {result.get('avoid', [])}")
    print(f"   Dynamic Adjustments: {result.get('dynamic_adjustments', 'N/A')}")

    # Verify
    rec_names = [r['name'].lower() for r in result.get('recommendations', [])]
    safety_warnings = " ".join(result.get('safety_warnings', [])).lower()
    dynamic_adj = (result.get('dynamic_adjustments') or "").lower()

    checks = [
        # Should NOT recommend fast run
        ("fast run" not in " ".join(rec_names), "Fast run NOT recommended"),
        # Should recommend lower intensity
        (any("walk" in name or "light" in name or "stretch" in name or "yoga" in name
             for name in rec_names), "Lower intensity alternative offered"),
        # Should include safety warning
        (len(result.get('safety_warnings', [])) > 0, "Safety warnings included"),
        # Should mention adjustment or disclaimer
        ("adjusted" in safety_warnings or "safety" in safety_warnings or
         "adjusted" in dynamic_adj or "safety" in dynamic_adj,
         "Adjustment/safety message present"),
    ]

    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        if not check:
            all_passed = False
        print(f"\n{status} {desc}")

    return all_passed


def test_dynamic_risk_blocks_configuration():
    """Test that dynamic risk blocks are properly configured."""
    print("\n" + "=" * 60)
    print("TEST 6: Dynamic Risk Configuration")
    print("=" * 60)

    print(f"\n📋 Configured Dynamic Risk Blocks:")
    for risk, config in DYNAMIC_RISK_BLOCKS.items():
        print(f"\n   Risk: {risk}")
        print(f"   Blocked keywords: {config['blocked'][:5]}...")
        print(f"   Reason: {config['reason']}")

    checks = [
        ("fried" in DYNAMIC_RISK_BLOCKS, "Fried risk configured"),
        ("high_oil" in DYNAMIC_RISK_BLOCKS, "High oil risk configured"),
        ("high_sugar" in DYNAMIC_RISK_BLOCKS, "High sugar risk configured"),
        ("processed" in DYNAMIC_RISK_BLOCKS, "Processed risk configured"),
        ("sprint" in DYNAMIC_RISK_BLOCKS["fried"]["blocked"], "Sprint blocked for fried"),
        ("hiit" in DYNAMIC_RISK_BLOCKS["high_sugar"]["blocked"], "HIIT blocked for high sugar"),
    ]

    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        if not check:
            all_passed = False
        print(f"{status} {desc}")

    return all_passed


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Module 3: Dynamic Safety Filtering - Validation Tests")
    print("=" * 60)

    results = []

    results.append(("Visual Warning Extraction", test_visual_warning_extraction()))
    results.append(("RAG Dynamic Filtering", test_rag_dynamic_filtering()))
    results.append(("Recommendation Validation", test_recommendation_validation()))
    results.append(("BR-001 Disclaimer", test_br001_disclaimer()))
    results.append(("End-to-End Donut+Run", test_end_to_end_donut_run()))
    results.append(("Dynamic Risk Configuration", test_dynamic_risk_blocks_configuration()))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED")
    print("=" * 60)
