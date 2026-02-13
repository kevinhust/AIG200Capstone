import logging
import json
import re
from typing import Optional, List, Dict, Any
from src.agents.base_agent import BaseAgent
from src.config import settings
from google.genai.types import GenerateContentConfig
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.cv_food_rec.gemini_vision_engine import GeminiVisionEngine
from health_butler.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

class NutritionAgent(BaseAgent):
    """
    Specialist agent for food analysis.
    
    Phase 11: RAG Nutritional Integration.
    - Uses SimpleRagTool.search_food to anchor vision estimates in ground truth.
    """
    
    def __init__(self, vision_tool: Optional[VisionTool] = None):
        super().__init__(
            role="nutrition",
            system_prompt="""You are an expert Nutritionist AI.
Your goal is to synthesize food analysis into a structured format.

OUTPUT FORMAT:
You MUST return a valid JSON object:
{
  "dish_name": "Main dish identified",
  "total_macros": {
    "calories": 0,
    "protein": 0,
    "carbs": 0,
    "fat": 0
  },
  "confidence_score": 0.0,
  "composition_analysis": "Detailed breakdown of ingredients and portions.",
  "health_tip": "A brief actionable tip.",
  "items_detected": []
}

CRITICAL RULES:
- Use 'RAG_MATCHES' to ground your 'total_macros' calculation.
- If a high-confidence RAG match exists, prioritize its per-100g data calibrated by the estimated portion size.
- DO NOT return 0 for macros if food is detected.
""",
            use_openai_api=False
        )
        self.vision_tool = vision_tool or VisionTool()
        self.gemini_engine = GeminiVisionEngine()
        self.rag = SimpleRagTool()

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Robustly extract JSON from a string."""
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                return json.loads(text[first_brace:last_brace+1])
            return None
        except Exception as e:
            logger.error(f"[NutritionAgent] JSON extraction failed: {e}")
            return None

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute nutrition analysis with RAG grounding.
        """
        logger.info("[NutritionAgent] Executing nutrition synthesis with RAG grounding...")
        
        image_path = None
        user_context_str = "{}"
        if context:
            for msg in context:
                if msg.get("type") == "image_path":
                    image_path = msg.get("content")
                elif msg.get("type") == "user_context":
                    user_context_str = msg.get("content", "{}")
        
        vision_info = {}
        if image_path:
            vision_result = self.gemini_engine.analyze_food(image_path, user_context_str)
            if "error" not in vision_result:
                vision_info = vision_result
            else:
                logger.error(f"[NutritionAgent] Vision analysis failed: {vision_result.get('error')}")
        
        # Phase 11: RAG Grounding
        rag_matches = []
        items = vision_info.get("items", [])
        if not items and vision_info.get("dish_name"):
            items = [{"name": vision_info["dish_name"], "portion": "1 serving"}]
            
        for item in items:
            name = item.get("name", "")
            match = self.rag.search_food(name)
            if match:
                match["original_item"] = name
                match["estimated_portion"] = item.get("portion", "unknown")
                rag_matches.append(match)
                logger.info(f"[NutritionAgent] RAG Match Found: {match['name']} for {name}")

        # Final Synthesis Prompt
        synthesis_input = f"""
TASK: {task}
VISION_RESULT: {json.dumps(vision_info)}
RAG_MATCHES (Ground Truth Data): {json.dumps(rag_matches)}

Synthesize the final nutritional analysis. 
IMPORTANT: 
- If RAG_MATCHES or VISION_RESULT contains calorie/macro data, 'total_macros' MUST reflect this. NEVER return 0 if food is visible.
- Use the RAG_MATCHES as the most reliable source for 'per 100g' data, scaling by the portion size estimated in VISION_RESULT.
- Ensure the 'composition_analysis' explains exactly why these specific numbers were chosen.
- For 'ingredients_with_portions', estimate weight/quantity (e.g., '135g x3', '270g total').
- For 'detailed_nutrients', provide estimates for Sodium (mg), Fiber (g), Sugar (g), and Saturated Fat (g) based on common nutritional data.
"""
        
        try:
            # Phase 13: Structured Synthesis (Expanded for User Design)
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=self.system_prompt + "\n\n" + synthesis_input,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "dish_name": {"type": "STRING"},
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
                            "detailed_nutrients": {
                                "type": "OBJECT",
                                "properties": {
                                    "sodium_mg": {"type": "NUMBER"},
                                    "fiber_g": {"type": "NUMBER"},
                                    "sugar_g": {"type": "NUMBER"},
                                    "saturated_fat_g": {"type": "NUMBER"}
                                }
                            },
                            "confidence_score": {"type": "NUMBER"},
                            "composition_analysis": {"type": "STRING"},
                            "health_tip": {"type": "STRING"},
                            "ingredients_with_portions": {
                                "type": "ARRAY", 
                                "items": {"type": "STRING"}
                            },
                            "items_detected": {"type": "ARRAY", "items": {"type": "STRING"}}
                        },
                        "required": ["dish_name", "total_macros", "composition_analysis", "ingredients_with_portions"]
                    }
                )
            )
            data = response.parsed
        except Exception as e:
            logger.error(f"[NutritionAgent] Structured synthesis failed: {e}")
            # Text fallback
            result_str = super().execute(synthesis_input, context)
            data = self._extract_json(result_str)
        
        if data:
            # Numeric safety
            if "total_macros" in data:
                for target in ["calories", "protein", "carbs", "fat"]:
                    val = data["total_macros"].get(target, 0)
                    try: data["total_macros"][target] = float(val) if val is not None else 0
                    except: data["total_macros"][target] = 0

            # Fallback to RAG sum if synthesis is weak
            if data.get("total_macros", {}).get("calories", 0) == 0 and rag_matches:
                logger.info("[NutritionAgent] Synthesis failed macro grounding. calculating from RAG...")
                data["total_macros"]["calories"] = sum(m.get("calories", 0) for m in rag_matches)
                data["total_macros"]["protein"] = sum(m.get("protein", 0) for m in rag_matches)
                data["total_macros"]["carbs"] = sum(m.get("carbs", 0) for m in rag_matches)
                data["total_macros"]["fat"] = sum(m.get("fat", 0) for m in rag_matches)

            return json.dumps(data)
            
        return json.dumps({"dish_name": vision_info.get("dish_name", "Meal"), "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}, "items_detected": items})
