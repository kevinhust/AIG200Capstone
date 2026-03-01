import os
import json
import time
from datetime import datetime
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ExerciseAPIClient:
    """
    Hybrid Caching Client for wger.de API to ensure < 5s latency and reliable safety filtering.
    """
    
    def __init__(self, cache_file: str = "health_butler/data/rag/exercise_cache.json"):
        self.wger_base_url = "https://wger.de/api/v2"
        # Adjust base path dynamically for robust local testing
        if os.path.exists("src"):
            self.cache_file = os.path.join(os.getcwd(), cache_file.replace("health_butler/", ""))
        else:
            self.cache_file = cache_file
        self.headers = {"User-Agent": "HealthButlerBot/3.0"}
        self._cache_in_memory: List[Dict] = []
        
        # Mapping to match SimpleRagTool expectations
        # wger categorizes by ID. We simplify by mapping directly or relying on names
        # if detailed mapping tables are needed, they can be fetched too.
        
    def hydrate_cache(self, force_refresh: bool = False) -> bool:
        """
        Loads cache from local JSON. If missing or force_refresh is True, fetches from API.
        """
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_content = json.load(f)
                
                # Handle old schema (raw list) vs new schema (dict with metadata)
                if isinstance(cache_content, list):
                    self._cache_in_memory = cache_content
                    logger.info(f"✅ Loaded {len(self._cache_in_memory)} exercises from legacy local cache.")
                elif isinstance(cache_content, dict) and "data" in cache_content:
                    self._cache_in_memory = cache_content["data"]
                    last_updated = cache_content.get("last_updated", "unknown")
                    logger.info(f"✅ Loaded {len(self._cache_in_memory)} exercises from local cache. Last Updated: {last_updated}")
                
                return True
            except Exception as e:
                logger.error(f"❌ Failed to load local cache, will fallback to API: {e}")

        # Fetch from API
        logger.info("🔄 Fetching exercise data from wger.de API to build cache...")
        new_data = self._fetch_all_wger_exercises()
        
        if new_data:
            self._cache_in_memory = new_data
            self._save_cache()
            logger.info(f"✅ Successfully hydrated cache with {len(new_data)} exercises from API.")
            return True
        else:
            logger.warning("⚠️ Failed to fetch from API. Cache hydration failed. Degraded performance possible.")
            return False

    def _fetch_all_wger_exercises(self) -> List[Dict]:
        """Fetches exercises from wger.de and maps them to the expected format."""
        
        url = f"{self.wger_base_url}/exerciseinfo/"
        # 2 = English
        params = {"language": 2, "limit": 100} 
        
        all_exercises = []
        try:
            while url:
                logger.info(f"Fetching: {url}")
                response = requests.get(url, params=params if "?" not in url else None, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                results = data.get('results', [])
                for item in results:
                    category = item.get("category", {}).get("name", "Other")
                    
                    tags = []
                    for eq in item.get("equipment", []):
                        tags.append(eq.get("name", ""))
                    for mus in item.get("muscles", []):
                        tags.append(mus.get("name", ""))
                        
                    tags = [t for t in tags if t]

                    name = item.get("name")
                    description = item.get("description", "")
                    
                    translations = item.get("translations", [])
                    # Find English translation (language 2)
                    en_translation = next((t for t in translations if t.get("language") == 2), None)
                    
                    if not name and en_translation:
                        name = en_translation.get("name")
                    if not description and en_translation:
                        description = en_translation.get("description", "")
                    
                    # Fallback for name if still missing
                    if not name and translations:
                        name = translations[0].get("name")
                    
                    if not name:
                         continue

                    mapped_ex = {
                        "id": item.get("id"),
                        "name": name,
                        "category": category,
                        "tags": tags,
                        "description": description,
                        "contraindications": [] 
                    }
                    all_exercises.append(mapped_ex)
                
                url = data.get("next")
                if url and url.startswith("http://"):
                    url = url.replace("http://", "https://")
                
                logger.info(f"Loaded {len(all_exercises)} exercises so far...")

            # --- Phase 2: Bulk Image Fetching ---
            logger.info("Fetching exercise images in bulk...")
            image_map = {}
            img_url = "https://wger.de/api/v2/exerciseimage/?limit=500"
            while img_url:
                try:
                    img_resp = requests.get(img_url, headers=self.headers, timeout=10)
                    img_resp.raise_for_status()
                    img_data = img_resp.json()
                    for img_item in img_data.get("results", []):
                        ex_id = img_item.get("exercise")
                        img_path = img_item.get("image")
                        if ex_id and img_path:
                            image_map[ex_id] = img_path
                    img_url = img_data.get("next")
                    if img_url and img_url.startswith("http://"):
                        img_url = img_url.replace("http://", "https://")
                    else:
                        img_url = None
                except Exception as e:
                    logger.warning(f"Error fetching images at {img_url}: {e}")
                    img_url = None

            # Map images to exercises
            for ex in all_exercises:
                ex_id = ex.get("id")
                ex["image_url"] = image_map.get(ex_id)

            return all_exercises
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error fetching wger exercises: {e}")
        except Exception as e:
            logger.error(f"Error fetching wger exercises: {e}")
            
        return all_exercises

    def _save_cache(self):
        """Persists the in-memory cache to disk with metadata."""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            cache_payload = {
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "data": self._cache_in_memory
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_payload, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save cache to file: {e}")

    def get_exercises(self) -> List[Dict]:
        """Returns the cached exercises."""
        return self._cache_in_memory

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = ExerciseAPIClient(cache_file="data/rag/exercise_cache.json")
    client.hydrate_cache(force_refresh=True)
    
    exs = client.get_exercises()
    if exs:
        print(f"Sample Exercise: {exs[0]}")
