#!/usr/bin/env python3
"""
Exercise Data Enrichment using Gemini 2.5 Flash

This script loads the cached exercise data from `data/rag/exercise_cache.json`
and uses Google's Gemini API to extract rich structured metadata from the 
wger.de HTML descriptions, drastically improving RAG search precision 
and Health Memo safety filtering.

Prerequisites:
    pip install google-genai
    export GEMINI_API_KEY="your-api-key"
"""

import os
import json
import logging
import time
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_cache(filepath: str) -> dict:
    if not os.path.exists(filepath):
        logger.error(f"Cannot find cache file at {filepath}. Run update_exercise_cache.py first.")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_cache(filepath: str, data: dict):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
def enrich_exercises(cache_data: dict, limit: int = 10):
    """
    Passes exercise descriptions to Gemini to extract structured metadata.
    """
    if "data" not in cache_data:
        logger.error("Invalid cache format. Please test with the latest api_client.py schema.")
        return

    client = genai.Client()
    
    # Define a clear schema for Structured Outputs
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "mechanics": {"type": "STRING", "description": "Either 'compound' or 'isolation'"},
            "impact_level": {"type": "STRING", "description": "low, medium, or high"},
            "common_mistakes_tags": {
                "type": "ARRAY", 
                "items": {"type": "STRING"},
                "description": "Short tags for mistakes e.g. ['knee valgus', 'spinal flexion']"
            },
            "contraindications": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Medical conditions that make this exercise unsafe (e.g., 'knee injury', 'lower back pain')"
            }
        },
        "required": ["mechanics", "impact_level", "common_mistakes_tags", "contraindications"]
    }

    exercises = cache_data["data"]
    enriched_count = 0
    
    for ex in exercises[:limit]:
        # Skip if already enriched or has no description
        if ex.get("impact_level") or not ex.get("description", "").strip():
            continue
            
        logger.info(f"Enriching: {ex['name']}")
        prompt = f"""
        Analyze the following exercise description:
        {ex['description']}
        
        Extract the mechanics (compound/isolation), physical impact level (low/medium/high), 
        common mistakes (as short tags), and contraindications (body parts/injuries that make this unsafe).
        """
        
        try:
            # Note: We use gemini-2.5-flash for rapid, cost-effective extraction
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.1
                )
            )
            
            structured_data = json.loads(response.text)
            
            # Update the original dict
            ex["mechanics"] = structured_data.get("mechanics", "unknown")
            ex["impact_level"] = structured_data.get("impact_level", "medium")
            ex["common_mistakes_tags"] = structured_data.get("common_mistakes_tags", [])
            ex["contraindications"] = structured_data.get("contraindications", [])
            
            # Also append tags into the flat tags array for RapidFuzz matching in SimpleRagTool
            ex["tags"].extend(ex["common_mistakes_tags"])
            ex["tags"].append(f"{structured_data.get('impact_level')} impact")
            ex["tags"].append(structured_data.get('mechanics'))
            
            enriched_count += 1
            logger.info(f"✅ Extracted: Impact={ex['impact_level']}, Contraindications={ex['contraindications']}")
            
            # Rate limiting for public tier
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Failed to parse Gemini response for {ex['name']}: {e}")

    logger.info(f"Successfully enriched {enriched_count} exercises.")

if __name__ == "__main__":
    # Adjust path if running from inside scripts/
    filepath = "data/rag/exercise_cache.json"
    if os.path.basename(os.getcwd()) == "scripts":
        filepath = os.path.join("..", filepath)
        
    cache = load_cache(filepath)
    if cache:
        # We limit to 5 here to avoid burning your quotas during testing. 
        # Increase `limit` when ready to process the entire database!
        enrich_exercises(cache, limit=10)
        save_cache(filepath, cache)
        logger.info("Saved enriched cache back to disk.")
