#!/usr/bin/env python3
"""
Exercise Cache Enrichment Script.

Processes the existing exercise_cache.json and adds scientific attributes:
- met_value: MET (Metabolic Equivalent of Task) for calorie calculation
- intensity: "low", "moderate", or "high"
- equipment_type: "bodyweight", "dumbbell", "barbell", etc.
- primary_muscles: Simplified muscle group list

Usage:
    python scripts/enrich_exercise_cache.py [--force]

Options:
    --force    Force re-enrichment even if already enriched
"""

import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_rag.met_mapping import enrich_exercise_data, batch_enrich_exercises

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_cache(cache_path: str) -> Dict:
    """Load exercise cache from JSON file."""
    if not os.path.exists(cache_path):
        logger.error(f"Cache file not found: {cache_path}")
        return {}

    with open(cache_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_cache(cache_path: str, cache_data: Dict) -> bool:
    """Save enriched cache to JSON file."""
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")
        return False


def is_already_enriched(exercise: Dict) -> bool:
    """Check if exercise already has scientific attributes."""
    return "met_value" in exercise and "intensity" in exercise


def enrich_cache(cache_path: str, force: bool = False) -> Dict:
    """
    Enrich the exercise cache with scientific attributes.

    Args:
        cache_path: Path to exercise_cache.json
        force: Force re-enrichment even if already enriched

    Returns:
        Statistics about the enrichment process
    """
    logger.info(f"📂 Loading cache from: {cache_path}")
    cache_data = load_cache(cache_path)

    if not cache_data:
        return {"error": "Failed to load cache"}

    # Handle both old (list) and new (dict) cache formats
    if isinstance(cache_data, list):
        exercises = cache_data
        metadata = {}
    else:
        exercises = cache_data.get("data", [])
        metadata = {
            "last_updated": cache_data.get("last_updated", "unknown"),
            "source": cache_data.get("source", "wger"),
        }

    logger.info(f"📊 Found {len(exercises)} exercises in cache")

    # Check if already enriched
    if not force:
        enriched_count = sum(1 for ex in exercises if is_already_enriched(ex))
        if enriched_count == len(exercises):
            logger.info("✅ Cache already enriched. Use --force to re-enrich.")
            return {"status": "already_enriched", "count": enriched_count}

    # Enrich exercises
    logger.info("🔬 Enriching exercises with scientific attributes...")
    enriched_exercises = batch_enrich_exercises(exercises, verbose=True)

    # Build new cache with metadata
    new_cache = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": "wger",
        "enrichment_version": "1.0",
        "enrichment_date": datetime.utcnow().isoformat() + "Z",
        "total_exercises": len(enriched_exercises),
        "data": enriched_exercises,
    }

    # Calculate statistics
    stats = {
        "total": len(enriched_exercises),
        "intensity": {"low": 0, "moderate": 0, "high": 0},
        "equipment": {},
        "met_range": {"min": 100, "max": 0, "avg": 0},
    }

    met_sum = 0
    for ex in enriched_exercises:
        # Intensity stats
        intensity = ex.get("intensity", "moderate")
        stats["intensity"][intensity] = stats["intensity"].get(intensity, 0) + 1

        # Equipment stats
        equipment = ex.get("equipment_type", "other")
        stats["equipment"][equipment] = stats["equipment"].get(equipment, 0) + 1

        # MET stats
        met = ex.get("met_value", 3.5)
        met_sum += met
        stats["met_range"]["min"] = min(stats["met_range"]["min"], met)
        stats["met_range"]["max"] = max(stats["met_range"]["max"], met)

    stats["met_range"]["avg"] = round(met_sum / len(enriched_exercises), 2)

    # Save enriched cache
    logger.info(f"💾 Saving enriched cache to: {cache_path}")
    if save_cache(cache_path, new_cache):
        logger.info("✅ Cache enrichment complete!")
        return stats
    else:
        return {"error": "Failed to save enriched cache"}


def print_stats(stats: Dict):
    """Print enrichment statistics in a nice format."""
    print("\n" + "=" * 60)
    print("📈 ENRICHMENT STATISTICS")
    print("=" * 60)

    if "error" in stats:
        print(f"❌ Error: {stats['error']}")
        return

    if stats.get("status") == "already_enriched":
        print(f"✅ Already enriched: {stats['count']} exercises")
        return

    print(f"\n📊 Total Exercises: {stats['total']}")

    print("\n🎯 Intensity Distribution:")
    for intensity, count in stats["intensity"].items():
        pct = (count / stats["total"]) * 100
        bar = "█" * int(pct / 5)
        print(f"   {intensity.upper():10} {count:4} ({pct:5.1f}%) {bar}")

    print("\n🏋️ Equipment Distribution:")
    for equipment, count in sorted(stats["equipment"].items(), key=lambda x: -x[1]):
        pct = (count / stats["total"]) * 100
        print(f"   {equipment:12} {count:4} ({pct:5.1f}%)")

    print(f"\n🔥 MET Range:")
    print(f"   Min: {stats['met_range']['min']}")
    print(f"   Max: {stats['met_range']['max']}")
    print(f"   Avg: {stats['met_range']['avg']}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Enrich exercise cache with scientific attributes")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment")
    parser.add_argument("--cache-path", default="data/rag/exercise_cache.json", help="Path to cache file")
    args = parser.parse_args()

    # Resolve cache path
    cache_path = args.cache_path
    if not os.path.isabs(cache_path):
        # Try relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_path = os.path.join(project_root, cache_path)

    logger.info("🚀 Starting Exercise Cache Enrichment")
    logger.info(f"   Cache path: {cache_path}")
    logger.info(f"   Force: {args.force}")

    stats = enrich_cache(cache_path, force=args.force)
    print_stats(stats)


if __name__ == "__main__":
    main()
