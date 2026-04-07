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
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        """Close the shared session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint.lstrip('/')}"
        session = await self._get_session()
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
        Uses the search endpoint which returns images directly in the response.
        """
        # Use the search endpoint for fuzzy matching - it already includes image URLs
        search_results = await self._get("exercise/search/", params={"term": exercise_name})

        if not search_results or not search_results.get("suggestions"):
            logger.info(f"No fuzzy matches found for: {exercise_name}")
            return None

        # Extract image from the first suggestion that has one
        for sug in search_results["suggestions"]:
            if 'data' in sug:
                img_url = sug['data'].get('image')
                if img_url:
                    # wger images are relative paths, ensure absolute
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
