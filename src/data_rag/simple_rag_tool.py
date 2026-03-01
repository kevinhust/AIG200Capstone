"""Simple RAG Tool for reliable, memory-based safety and nutrition retrieval.

Replaces vector database complexity with direct JSON filtering for
Capstone/MVP scale. Uses rapidfuzz for robust keyword matching.

Module 3: Dynamic Risk Filtering
- Supports dynamic_risks parameter for real-time safety filtering
- Blocks high-intensity exercises when user consumed fried/high_oil food
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

from .api_client import ExerciseAPIClient
from src.api_client.wger_client import WgerClient

try:
    from rapidfuzz import process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)

# Dynamic risk to exercise intensity mapping
# These exercise types are blocked when dynamic_risks contain certain warnings
HIGH_INTENSITY_KEYWORDS = [
    "sprint", "hiit", "high intensity", "fast run", "running fast",
    "burpee", "jump squat", "box jump", "plyometric",
    "max effort", "all-out", "vigorous", "intense cardio"
]

MODERATE_INTENSITY_KEYWORDS = [
    "run", "jog", "running", "jump", "jumping", "skip", "skipping"
]

# Risk to blocked intensity mapping
DYNAMIC_RISK_BLOCKS = {
    "fried": {
        "blocked": HIGH_INTENSITY_KEYWORDS,
        "reason": "High-fat/fried food digestion requires blood flow to stomach"
    },
    "high_oil": {
        "blocked": HIGH_INTENSITY_KEYWORDS,
        "reason": "Heavy oil content may cause discomfort during vigorous exercise"
    },
    "high_sugar": {
        "blocked": HIGH_INTENSITY_KEYWORDS + MODERATE_INTENSITY_KEYWORDS,
        "reason": "Blood sugar spike may cause energy crash during intense exercise"
    },
    "processed": {
        "blocked": HIGH_INTENSITY_KEYWORDS,
        "reason": "Processed food may cause digestive issues during intense activity"
    }
}

class SimpleRagTool:
    """
    Lightweight RAG tool that loads JSONs into memory.
    Phase 7: Integrated with rapidfuzz for robust matching.
    Phase 11: Added nutritional database support.
    """
    
    def __init__(self, data_dir: str = "health_butler/data"):
        self.data_dir = data_dir
        
        # Initialize the new Hybrid Caching API Client
        cache_path = os.path.join(data_dir, "rag", "exercise_cache.json")
        self.api_client = ExerciseAPIClient(cache_file=cache_path)
        
        # Try to load cache, fallback to API if missing
        self.api_client.hydrate_cache()
        self.exercises = self.api_client.get_exercises()

        # If API and cache both fail (extreme fallback), load local static file
        if not self.exercises:
             logger.warning("⚠️ API and Cache empty. Falling back to static exercises.json")
             self.exercises = self._load_json("rag/exercises.json")
        
        self.safety_protocols = self._load_json("rag/safety_protocols.json")
        
        # Load Nutritional Data
        self.usda_foods = self._load_json("raw/usda_common_foods.json")
        
        # Async Wger Client for on-the-fly image fetching
        self.wger_client = WgerClient()
        
        logger.info(f"✅ SimpleRagTool initialized: {len(self.exercises)} exercises, {len(self.usda_foods)} foods, {FUZZY_AVAILABLE=}")

    async def attach_exercise_images_async(self, exercises: List[Dict]) -> List[Dict]:
        """
        Asynchronously fetches and attaches images to a list of exercises if missing.
        """
        import asyncio
        
        async def _fetch_and_attach(ex):
            if not ex.get("image_url"):
                # Search on wger
                img = await self.wger_client.search_exercise_image_async(ex["name"])
                if img:
                    ex["image_url"] = img
            return ex

        tasks = [_fetch_and_attach(ex) for ex in exercises]
        return await asyncio.gather(*tasks)

    def _load_json(self, relative_path: str) -> List[Dict[str, Any]]:
        """Load structured data from JSON files."""
        potential_paths = [
            os.path.join(self.data_dir, relative_path),
            os.path.join(os.getcwd(), self.data_dir, relative_path),
            os.path.join(os.path.dirname(__file__), "..", "data", relative_path),
        ]
        for path in potential_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"❌ Failed to parse {path}: {e}")
                    return []
        
        # logger.warning(f"⚠️ Data file not found: {relative_path}")
        return []

    def search_food(self, query: str, min_score: int = 75, limit: int = 1) -> Optional[Dict[str, Any]]:
        """Search for food items with nutritional data."""
        if not self.usda_foods or not query:
            return None
        
        query = query.lower().strip()
        
        if FUZZY_AVAILABLE:
            # Search space: queries and descriptions
            search_space = [f"{f.get('query', '')} {f.get('description', '')}".lower() for f in self.usda_foods]
            
            results = process.extract(
                query,
                search_space,
                scorer=fuzz.WRatio,
                limit=limit
            )
            
            if results and results[0][1] >= min_score:
                idx = results[0][2]
                food_item = self.usda_foods[idx]
                
                # Normalize results
                nutrients = food_item.get("nutrients", {})
                return {
                    "name": food_item.get("description", "Unknown").title(),
                    "calories": nutrients.get("calories", {}).get("value", 0),
                    "protein": nutrients.get("protein", {}).get("value", 0),
                    "carbs": nutrients.get("carbs", {}).get("value", 0),
                    "fat": nutrients.get("fat", {}).get("value", 0),
                    "confidence": results[0][1],
                    "source": "USDA"
                }
        
        return None

    def search_exercises(self, query: str, min_score: int = 60, limit: int = 5) -> List[Dict]:
        """Search exercises with fuzzy matching logic."""
        query = query.lower().strip()
        if not query:
            return self.exercises[:limit]

        if FUZZY_AVAILABLE:
            search_space = []
            for ex in self.exercises:
                text = f"{ex.get('name', '')} {ex.get('category', '')} {' '.join(ex.get('tags', []))}".lower()
                search_space.append(text)
            
            results = process.extract(
                query,
                search_space,
                scorer=fuzz.WRatio,
                limit=limit * 2
            )
            
            matched = []
            for res in results:
                score = res[1]
                idx = res[2]
                if score >= min_score:
                    matched.append(self.exercises[idx])
            return matched[:limit]
        
        return []

    def get_safe_recommendations(self,
                                 user_query: str,
                                 user_conditions: List[str],
                                 top_k: int = 5,
                                 dynamic_risks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Safety-First Retrieval Algorithm.

        Args:
            user_query: The exercise query from user
            user_conditions: Static health conditions (e.g., knee injury)
            top_k: Number of recommendations to return
            dynamic_risks: Dynamic risks from Health Memo (e.g., fried, high_oil)

        Returns:
            Dict with safe_exercises, safety_warnings, dynamic_adjustments
        """
        active_conditions = [c.lower() for c in user_conditions]
        dynamic_risks = dynamic_risks or []
        dynamic_risks_lower = [r.lower() for r in dynamic_risks]

        # Collect blocked exercise keywords from dynamic risks
        blocked_keywords = set()
        dynamic_warnings = []

        for risk in dynamic_risks_lower:
            if risk in DYNAMIC_RISK_BLOCKS:
                blocked_keywords.update(DYNAMIC_RISK_BLOCKS[risk]["blocked"])
                dynamic_warnings.append(DYNAMIC_RISK_BLOCKS[risk]["reason"])

        # Log dynamic filtering
        if blocked_keywords:
            logger.info(f"[DynamicRisk] Blocking keywords: {blocked_keywords}")
            logger.info(f"[DynamicRisk] Reasons: {dynamic_warnings}")

        # Filter exercises
        safe_list = []
        for ex in self.exercises:
            is_safe = True
            block_reason = None

            # Check static contraindications
            for contra in ex.get("contraindications", []):
                if contra.lower() in active_conditions:
                    is_safe = False
                    block_reason = f"Contraindicated for: {contra}"
                    break

            # Check dynamic risks (intensity-based filtering)
            if is_safe and blocked_keywords:
                ex_name = ex.get("name", "").lower()
                ex_tags = " ".join(ex.get("tags", [])).lower()
                ex_category = ex.get("category", "").lower()
                ex_text = f"{ex_name} {ex_category} {ex_tags}"

                for keyword in blocked_keywords:
                    if keyword in ex_text:
                        is_safe = False
                        block_reason = f"Blocked by dynamic risk (keyword: {keyword})"
                        logger.info(f"[DynamicRisk] Blocked '{ex.get('name')}': {block_reason}")
                        break

            if is_safe:
                safe_list.append(ex)

        # Search within safe exercises
        original_exercises = self.exercises
        self.exercises = safe_list
        recs = self.search_exercises(user_query, limit=top_k)
        self.exercises = original_exercises

        # Build safety warnings
        safety_warnings = []
        if dynamic_warnings:
            unique_reasons = list(set(dynamic_warnings))
            safety_warnings.extend(unique_reasons)

        # Build dynamic adjustments message
        dynamic_adjustments = None
        if blocked_keywords:
            dynamic_adjustments = {
                "blocked_keywords": list(blocked_keywords),
                "reasons": dynamic_warnings,
                "disclaimer": "Due to the recent consumption of fried/high-sugar food, "
                              "I've adjusted your plan to lower intensity for your safety."
            }

        return {
            "safe_exercises": recs,
            "safety_warnings": safety_warnings,
            "dynamic_adjustments": dynamic_adjustments
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = SimpleRagTool()
    # Test food search
    test_food = "pork ribs"
    res = tool.search_food(test_food)
    if res:
        print(f"✅ RAG Food Search found: {res['name']} | Calories: {res['calories']}")
    else:
        print(f"❌ RAG Food Search failed for: {test_food}")
