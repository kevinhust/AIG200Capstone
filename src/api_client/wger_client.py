import aiohttp
import logging
import asyncio
from typing import Optional, Dict, Any, List
from src.config import settings

logger = logging.getLogger(__name__)

class WgerClient:
    """
    Async client for the wger.de API to fetch exercise images and data.
    """
    def __init__(self, base_url: str = settings.WGER_API_BASE_URL):
        self.base_url = base_url.rstrip("/") + "/"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "HealthButlerBot/1.0 (https://github.com/kevinhust/capstonetest)"
        }

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"Wger API error: {response.status} at {url}")
                        return None
            except Exception as e:
                logger.error(f"Wger API connection failed: {e}")
                return None

    async def search_exercise_image_async(self, exercise_name: str) -> Optional[str]:
        """
        Search for an exercise image by name.
        Uses the search endpoint for better fuzzy matching.
        """
        # Step 1: Use the search endpoint for fuzzy matching
        search_results = await self._get("exercise/search/", params={"term": exercise_name})
        
        if not search_results or not search_results.get("suggestions"):
            logger.info(f"No fuzzy matches found for: {exercise_name}, trying exact name filter")
            search_results = await self._get("exercise/", params={"name": exercise_name})
        else:
            # Re-format suggestions to look like standard results for ID extraction
            temp_results = []
            for sug in search_results["suggestions"]:
                if 'data' in sug and 'id' in sug['data']:
                    temp_results.append({"id": sug['data']['id']})
            search_results = {"results": temp_results}

        if not search_results or not search_results.get("results"):
            return None

        # Step 2: Iterate through result candidates to find one with an image
        for candidate in search_results["results"][:3]:
            exercise_id = candidate["id"]
            # The filter parameter in wger/exerciseimage is 'exercise'
            image_results = await self._get("exerciseimage/", params={"exercise": exercise_id})
            
            if image_results and image_results.get("results"):
                # wger images are relative paths sometimes, ensure absolute
                img_url = image_results["results"][0]["image"]
                if img_url.startswith("/media/"):
                    img_url = "https://wger.de" + img_url
                return img_url
        
        return None

# Simple test runner
if __name__ == "__main__":
    async def test():
        client = WgerClient()
        test_name = "Bicep Curls"
        print(f"Searching for exercise: {test_name}...")
        image_url = await client.search_exercise_image_async(test_name)
        if image_url:
            print(f"Found image: {image_url}")
        else:
            print("No image found.")

    asyncio.run(test())
