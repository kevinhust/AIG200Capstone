#!/usr/bin/env python3
"""
Exercise Cache Updater Script

Run this script periodically (e.g., via cron) to hydrate the local exercise cache from wger.de.

Cron example (runs daily at 3 AM):
0 3 * * * /path/to/venv/bin/python /path/to/update_exercise_cache.py
"""

import sys
import os
import logging

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from data_rag.api_client import ExerciseAPIClient
except ImportError as e:
    print(f"Failed to import ExerciseAPIClient: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting exercise cache update...")
    
    # Path relative to the project root
    cache_path = os.path.join("data", "rag", "exercise_cache.json")
    
    # If ran from inside scripts directory, adjust path up one level
    if os.path.basename(os.getcwd()) == "scripts":
        cache_path = os.path.join("..", cache_path)
    
    client = ExerciseAPIClient(cache_file=cache_path)
    # Force refresh fetches from API
    success = client.hydrate_cache(force_refresh=True)
    
    if success:
        logger.info("Successfully updated exercise cache.")
    else:
        logger.error("Failed to update exercise cache.")
        sys.exit(1)

if __name__ == "__main__":
    main()
