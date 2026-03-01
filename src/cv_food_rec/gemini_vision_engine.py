"""Gemini Vision Engine for semantic food analysis.

Uses the modern google-genai SDK (v2026) to identify dishes, ingredients, and estimate portions.
Updated to gemini-2.5-flash for reliability beyond March 2026.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv

load_dotenv()  # ensure .env is loaded before os.getenv reads

from google import genai
from PIL import Image

from src.config import settings

# Recommended Stable Model as of Feb 2026
DEFAULT_MODEL = "gemini-2.5-flash"

class GeminiVisionEngine:
    """
    Semantic engine for food analysis using Gemini.
    Phase 8 Refinement: Future-proofed model selection.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.client = None
        if not self.api_key:
            logger.warning("⚠️ GOOGLE_API_KEY not found (GeminiVisionEngine).")
        else:
            self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        
        # Expert recommended warning for deprecated models
        if "2.0" in self.model_name:
            logger.warning(
                f"☢️ CRITICAL: Using deprecated model {self.model_name}! "
                f"It will be shut down on 2026-03-31. Please switch to {DEFAULT_MODEL}."
            )
        else:
            logger.info(f"✅ GeminiVisionEngine initialized with stable model: {self.model_name}")

    async def analyze_food_async(
        self,
        image_path: str,
        user_context: Optional[str] = None,
        *,
        object_detections: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a food image using Gemini (Asynchronous) and return structured data.
        """
        if not self.api_key:
            return {"error": "API Key missing"}

        logger.info(f"🚀 [Async] Sending image to Gemini {self.model_name}...")

        img = None
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            prompt = """You are an expert nutritionist and chef. Analyze this food image in extreme detail.
Analyze the dish and ingredients.
CRITICAL: Ignore generic YOLO labels like 'bowl' or 'plate' if they appear in the image metadata. Focus on actual food content.

## COOKING METHOD & VISUAL RISK ANALYSIS (REQUIRED)
Carefully scan the food for these visual indicators and cooking methods:
- **Deep-fried (fried)**: Golden-brown crust, oil sheen, batter coating, crispy texture appearance
- **Heavy-oil (high_oil)**: Visible oil pooling, glossy surface, greasy appearance, oil drips
- **Heavy-syrup/Sugary (high_sugar)**: Glazed coating, crystalline sugar visible, sticky shine, caramelization
- **Processed (processed)**: Uniform artificial color, preservative appearance, factory-made look

Assign a health_score (1-10):
- 10: Raw vegetables, fresh fruits, steamed/boiled whole foods
- 7-9: Lightly cooked, minimal oil, whole ingredients
- 4-6: Moderate processing, some oil/sugar
- 1-3: Deep-fried, heavy oil, high sugar, highly processed

NUTRITION REFERENCE (per 100g):
- Banana (raw): ~89 kcal, 1.1g protein, 23g carbs, 0.3g fat
- Apple (raw): ~52 kcal, 0.3g protein, 14g carbs, 0.2g fat
- Orange (raw): ~47 kcal, 0.9g protein, 12g carbs, 0.1g fat
- Beef patty: ~250 kcal, 25g protein, 18g fat, 0g carbs
- Chicken breast: ~165 kcal, 31g protein, 3.6g fat, 0g carbs
- Burger bun: ~265 kcal, 9g protein, 50g carbs, 4g fat
- Cheese slice: ~100 kcal, 6g protein, 0.5g carbs, 9g fat
- Cooked rice: ~130 kcal, 2.7g protein, 28g carbs, 0.3g fat
- Pasta: ~131 kcal, 5g protein, 25g carbs, 1.1g fat
- Fried chicken: ~320 kcal, 18g protein, 15g carbs, 20g fat
- Donut: ~450 kcal, 5g protein, 50g carbs, 25g fat

Ensure protein, fat, and carbs are NON-ZERO if the food contains meat, cheese, oils, or cereal.

PORTION RULES:
- If there are multiple of the same item (e.g. several bananas), set `portion` to an explicit count like `x5`.
- `estimated_weight_grams` should represent the approximate weight PER ITEM (not total) when `portion` is used.
- Typical unit weights (edible): banana ~118g, apple ~182g, orange ~131g.
"""
            if user_context:
                prompt += f"\n\nUSER CONTEXT: {user_context}"
            if object_detections:
                prompt += (
                    "\n\nOBJECT_DETECTIONS (from a local detector; may be noisy—VERIFY VISUALLY): "
                    + json.dumps(object_detections)
                    + "\nUse OBJECT_DETECTIONS as hints for naming and counts, but do NOT blindly trust them."
                    + "\nKnown failure mode: the detector can confuse oranges/tangerines/mandarins with donuts."
                    + "\nIf the object is a solid citrus fruit (no hole), label it as Orange (or Tangerine), NOT Donut."
                    + "\nIf OBJECT_DETECTIONS includes banana, ensure banana is included in `items`."
                )

            from google.genai.types import GenerateContentConfig

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=[prompt, img],
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "dish_name": {"type": "STRING"},
                            "items": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "name": {"type": "STRING"},
                                        "portion": {"type": "STRING"},
                                        "main_ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
                                        "estimated_weight_grams": {"type": "NUMBER"},
                                        "visual_volume_percentage": {"type": "NUMBER"},
                                        "macros": {
                                            "type": "OBJECT",
                                            "properties": {
                                                "calories": {"type": "NUMBER"},
                                                "protein": {"type": "NUMBER"},
                                                "carbs": {"type": "NUMBER"},
                                                "fat": {"type": "NUMBER"}
                                            },
                                            "required": ["calories", "protein", "carbs", "fat"]
                                        },
                                        "confidence_score": {"type": "NUMBER"}
                                    },
                                    "required": ["name", "macros"]
                                }
                            },
                            "total_macros": {
                                "type": "OBJECT",
                                "properties": {
                                    "calories": {"type": "NUMBER"},
                                    "protein": {"type": "NUMBER"},
                                    "carbs": {"type": "NUMBER"},
                                    "fat": {"type": "NUMBER"}
                                },
                                "required": ["calories", "protein", "carbs", "fat"]
                            },
                            "total_confidence": {"type": "NUMBER"},
                            "composition_analysis": {"type": "STRING"},
                            "notes": {"type": "STRING"},
                            "visual_warnings": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "Risk labels: fried, high_oil, high_sugar, processed"
                            },
                            "health_score": {
                                "type": "INTEGER",
                                "description": "Health score 1-10 (10=healthiest, 1=least healthy)"
                            }
                        },
                        "required": ["dish_name", "total_macros", "items", "visual_warnings", "health_score"]
                    }
                )
            )
            
            data = response.parsed
            
            if isinstance(data, dict):
                if "confidence_score" not in data and "total_confidence" in data:
                    data["confidence_score"] = data["total_confidence"]
                return data
            else:
                text = response.text
                return json.loads(text)
            
        except Exception as e:
            logger.error(f"❌ Gemini async analysis failed: {e}")
            return {"error": str(e)}
        finally:
            if img is not None:
                try: img.close()
                except Exception: pass

    def analyze_food(
        self,
        image_path: str,
        user_context: Optional[str] = None,
        *,
        object_detections: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a food image using Gemini and return structured data.
        """
        if not self.api_key:
            return {"error": "API Key missing"}

        logger.info(f"🚀 Sending image to Gemini {self.model_name} for high-fidelity analysis...")

        img = None
        try:
            img = Image.open(image_path)
            
            prompt = """You are an expert nutritionist and chef. Analyze this food image in extreme detail.
Analyze the dish and ingredients.
CRITICAL: Ignore generic YOLO labels like 'bowl' or 'plate' if they appear in the image metadata. Focus on actual food content.

## COOKING METHOD & VISUAL RISK ANALYSIS (REQUIRED)
Carefully scan the food for these visual indicators and cooking methods:
- **Deep-fried (fried)**: Golden-brown crust, oil sheen, batter coating, crispy texture appearance
- **Heavy-oil (high_oil)**: Visible oil pooling, glossy surface, greasy appearance, oil drips
- **Heavy-syrup/Sugary (high_sugar)**: Glazed coating, crystalline sugar visible, sticky shine, caramelization
- **Processed (processed)**: Uniform artificial color, preservative appearance, factory-made look

Assign a health_score (1-10):
- 10: Raw vegetables, fresh fruits, steamed/boiled whole foods
- 7-9: Lightly cooked, minimal oil, whole ingredients
- 4-6: Moderate processing, some oil/sugar
- 1-3: Deep-fried, heavy oil, high sugar, highly processed

NUTRITION REFERENCE (per 100g):
- Banana (raw): ~89 kcal, 1.1g protein, 23g carbs, 0.3g fat
- Apple (raw): ~52 kcal, 0.3g protein, 14g carbs, 0.2g fat
- Orange (raw): ~47 kcal, 0.9g protein, 12g carbs, 0.1g fat
- Beef patty: ~250 kcal, 25g protein, 18g fat, 0g carbs
- Chicken breast: ~165 kcal, 31g protein, 3.6g fat, 0g carbs
- Burger bun: ~265 kcal, 9g protein, 50g carbs, 4g fat
- Cheese slice: ~100 kcal, 6g protein, 0.5g carbs, 9g fat
- Cooked rice: ~130 kcal, 2.7g protein, 28g carbs, 0.3g fat
- Pasta: ~131 kcal, 5g protein, 25g carbs, 1.1g fat
- Fried chicken: ~320 kcal, 18g protein, 15g carbs, 20g fat
- Donut: ~450 kcal, 5g protein, 50g carbs, 25g fat

Ensure protein, fat, and carbs are NON-ZERO if the food contains meat, cheese, oils, or cereal.

PORTION RULES:
- If there are multiple of the same item (e.g. several bananas), set `portion` to an explicit count like `x5`.
- `estimated_weight_grams` should represent the approximate weight PER ITEM (not total) when `portion` is used.
- Typical unit weights (edible): banana ~118g, apple ~182g, orange ~131g.
"""
            if user_context:
                prompt += f"\n\nUSER CONTEXT: {user_context}"
            if object_detections:
                prompt += (
                    "\n\nOBJECT_DETECTIONS (from a local detector; may be noisy—VERIFY VISUALLY): "
                    + json.dumps(object_detections)
                    + "\nUse OBJECT_DETECTIONS as hints for naming and counts, but do NOT blindly trust them."
                    + "\nKnown failure mode: the detector can confuse oranges/tangerines/mandarins with donuts."
                    + "\nIf the object is a solid citrus fruit (no hole), label it as Orange (or Tangerine), NOT Donut."
                    + "\nIf OBJECT_DETECTIONS includes banana, ensure banana is included in `items`."
                )

            # Phase 13: Structured Output Schema
            # This ensures 100% valid JSON and stable macro fields
            from google.genai.types import GenerateContentConfig

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, img],
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "dish_name": {"type": "STRING"},
                            "items": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "name": {"type": "STRING"},
                                        "portion": {"type": "STRING"},
                                        "main_ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
                                        "estimated_weight_grams": {"type": "NUMBER"},
                                        "visual_volume_percentage": {"type": "NUMBER"},
                                        "macros": {
                                            "type": "OBJECT",
                                            "properties": {
                                                "calories": {"type": "NUMBER"},
                                                "protein": {"type": "NUMBER"},
                                                "carbs": {"type": "NUMBER"},
                                                "fat": {"type": "NUMBER"}
                                            },
                                            "required": ["calories", "protein", "carbs", "fat"]
                                        },
                                        "confidence_score": {"type": "NUMBER"}
                                    },
                                    "required": ["name", "macros"]
                                }
                            },
                            "total_macros": {
                                "type": "OBJECT",
                                "properties": {
                                    "calories": {"type": "NUMBER"},
                                    "protein": {"type": "NUMBER"},
                                    "carbs": {"type": "NUMBER"},
                                    "fat": {"type": "NUMBER"}
                                },
                                "required": ["calories", "protein", "carbs", "fat"]
                            },
                            "total_confidence": {"type": "NUMBER"},
                            "composition_analysis": {"type": "STRING"},
                            "notes": {"type": "STRING"},
                            "visual_warnings": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": "Risk labels: fried, high_oil, high_sugar, processed"
                            },
                            "health_score": {
                                "type": "INTEGER",
                                "description": "Health score 1-10 (10=healthiest, 1=least healthy)"
                            }
                        },
                        "required": ["dish_name", "total_macros", "items", "visual_warnings", "health_score"]
                    }
                )
            )
            
            data = response.parsed
            
            # Compatibility injection
            if isinstance(data, dict):
                if "confidence_score" not in data and "total_confidence" in data:
                    data["confidence_score"] = data["total_confidence"]
                return data
            else:
                # If SDK returned something else, try manual parse of text
                text = response.text
                return json.loads(text)
            
        except Exception as e:
            logger.error(f"❌ Gemini analysis failed: {e}")
            return {"error": str(e)}
        finally:
            # BR-005: Ephemeral Storage - ensure image is closed
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = GeminiVisionEngine()
    print(f"Engine ready with model: {engine.model_name}")
