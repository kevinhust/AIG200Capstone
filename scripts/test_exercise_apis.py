import os
import time
import requests
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExerciseAPIClient:
    """Robust client for testing wger.de and ExerciseDB APIs."""
    
    def __init__(self, rapidapi_key: str = None):
        self.wger_base_url = "https://wger.de/api/v2"
        self.exercisedb_base_url = "https://exercisedb.p.rapidapi.com/exercises"
        self.rapidapi_key = rapidapi_key or os.getenv("RAPIDAPI_KEY", "")

    def test_wger_exercises(self, equipment_id: int = None, muscle_id: int = None) -> List[Dict]:
        """
        Test wger.de API.
        wger uses IDs for muscles (e.g., 1=Biceps) and equipment (e.g., 3=Dumbbell).
        """
        logger.info("Testing wger.de API...")
        url = f"{self.wger_base_url}/exerciseinfo/"
        params = {"language": 2} # English
        if equipment_id:
            params["equipment"] = equipment_id
        if muscle_id:
            params["muscles"] = muscle_id

        start_time = time.time()
        try:
            response = requests.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            latency = time.time() - start_time
            
            logger.info(f"[wger] Success! Latency: {latency:.3f}s, Results count: {len(data.get('results', []))}")
            if latency > 5.0:
                logger.warning("[wger] Latency is > 5s! Might fail strict latency requirements.")
                
            return data.get('results', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"[wger] API query failed: {e}")
            return []

    def test_exercisedb(self, target_muscle: str = "biceps", equipment: str = "dumbbell") -> List[Dict]:
        """
        Test ExerciseDB (via RapidAPI).
        Requires RAPIDAPI_KEY environment variable.
        """
        if not self.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not set. Skipping ExerciseDB test.")
            return []

        logger.info("Testing ExerciseDB API...")
        # Example: Filter by equipment
        url = f"{self.exercisedb_base_url}/equipment/{equipment}"
        
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
        }
        
        start_time = time.time()
        try:
            response = requests.get(url, headers=headers, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            latency = time.time() - start_time
            
            # Additional in-memory filter for muscle if API only allows 1 path parameter filter
            filtered_data = [ex for ex in data if target_muscle.lower() in ex.get('target', '').lower()]
            
            logger.info(f"[ExerciseDB] Success! Latency: {latency:.3f}s, Filtered results count: {len(filtered_data)}")
            if latency > 5.0:
                logger.warning("[ExerciseDB] Latency is > 5s!")
                
            return filtered_data
        except requests.exceptions.RequestException as e:
            logger.error(f"[ExerciseDB] API query failed: {e}")
            return []

if __name__ == "__main__":
    client = ExerciseAPIClient()
    
    # 1. Test wger.de (Public, no auth needed)
    # 3 = Dumbbell, 1 = Biceps (Example IDs, you may need to fetch the mapping from /equipment/ and /muscle/)
    wger_res = client.test_wger_exercises(equipment_id=3, muscle_id=1)
    if wger_res:
        logger.info(f"wger sample: {wger_res[0].get('name')}")
        
    print("-" * 40)
    
    # 2. Test ExerciseDB (Requires RapidAPI key)
    # Set export RAPIDAPI_KEY="your_key" in terminal before running
    edb_res = client.test_exercisedb(target_muscle="biceps", equipment="dumbbell")
    if edb_res:
         logger.info(f"ExerciseDB sample: {edb_res[0].get('name')}")
