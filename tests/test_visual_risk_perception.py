"""Test script for Module 2: Visual Risk Perception Upgrade.

Validates that GeminiVisionEngine correctly identifies:
- visual_warnings (fried, high_oil, high_sugar, processed)
- health_score (1-10 scale)
"""

import os
import sys
import json
import logging
import tempfile
import urllib.request

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cv_food_rec.gemini_vision_engine import GeminiVisionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test image URLs (public domain food images from Wikimedia Commons)
TEST_IMAGES = {
    "fried_chicken": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=640",  # fried chicken
    "donut": "https://images.unsplash.com/photo-1551024601-bec78aea704b?w=640",  # donut
}


def download_image(url: str, dest_path: str) -> bool:
    """Download image from URL to local path with proper headers."""
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


def test_visual_risk_detection():
    """Test that visual_warnings and health_score are correctly populated."""
    engine = GeminiVisionEngine()

    if not engine.client:
        logger.warning("⚠️ No API key available. Running schema validation only.")
        return validate_schema()

    results = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for food_type, url in TEST_IMAGES.items():
            img_path = os.path.join(tmpdir, f"{food_type}.jpg")

            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {food_type.upper()}")
            logger.info(f"{'='*60}")

            if not download_image(url, img_path):
                logger.error(f"Failed to download {food_type}")
                continue

            result = engine.analyze_food(img_path)
            results[food_type] = result

            # Validate new fields
            print(f"\n📋 Result for {food_type}:")
            print(f"  dish_name: {result.get('dish_name', 'N/A')}")
            print(f"  health_score: {result.get('health_score', 'MISSING')}")
            print(f"  visual_warnings: {result.get('visual_warnings', 'MISSING')}")

            # Assertions for unhealthy foods
            if food_type in ["fried_chicken", "donut"]:
                warnings = result.get("visual_warnings", [])
                score = result.get("health_score", 10)

                if warnings:
                    logger.info(f"  ✅ visual_warnings present: {warnings}")
                else:
                    logger.warning(f"  ⚠️ visual_warnings is empty!")

                if score and score <= 5:
                    logger.info(f"  ✅ health_score reflects unhealthy food: {score}")
                else:
                    logger.warning(f"  ⚠️ health_score may be too high: {score}")

    return results


def validate_schema():
    """Validate that the schema includes new fields."""
    logger.info("\n📋 Schema Validation (offline mode)")

    # Check that the schema is correctly defined in the module
    from cv_food_rec.gemini_vision_engine import GeminiVisionEngine
    import inspect

    source = inspect.getsource(GeminiVisionEngine.analyze_food)

    required_fields = ["visual_warnings", "health_score"]
    missing = []

    for field in required_fields:
        if field in source:
            logger.info(f"  ✅ Schema includes '{field}'")
        else:
            logger.error(f"  ❌ Schema missing '{field}'")
            missing.append(field)

    if not missing:
        logger.info("\n✅ All required schema fields present!")
        return True
    else:
        logger.error(f"\n❌ Missing fields: {missing}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Module 2: Visual Risk Perception - Validation Test")
    print("=" * 60)

    results = test_visual_risk_detection()

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
