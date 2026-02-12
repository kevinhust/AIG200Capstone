from typing import Optional, List, Dict, Any
import logging
import json
import re
from src.agents.base_agent import BaseAgent
from health_butler.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

# Mock User Profile for Prototype Phase
MOCK_USER_PROFILE = {
    "name": "Kevin",
    "age": 30,
    "weight_kg": 80,
    "height_cm": 178,
    "goal": "Weight Loss",
    "activity_level": "Sedentary (Office Job)",
    "daily_calorie_target": 2200,
    "restrictions": "Knee pain (avoid high impact jumping)"
}

class FitnessAgent(BaseAgent):
    """
    Specialist agent for providing exercise and wellness advice.
    
    Safety-First Evolution (Phase 7):
    - Real-time Context: Uses actual user profile and daily calorie status.
    - Simple RAG: Filters exercises based on JSON data (no vector DB).
    - Structured Output: Returns JSON for interactive Discord UI.
    """
    
    def __init__(self):
        # Inject profile into system prompt
        profile_str = "\n".join([f"- {k}: {v}" for k, v in MOCK_USER_PROFILE.items()])
        
        super().__init__(
            role="fitness",
            system_prompt="""You are an expert Fitness Coach and Wellness Assistant.
Your goal is to provide safe, actionable exercise advice.

OUTPUT FORMAT:
You MUST return a valid JSON object with the following structure:
{
  "summary": "A concise overview of the advice (1-2 sentences).",
  "recommendations": [
    {
      "name": "Exercise name",
      "duration_min": 20,
      "kcal_estimate": 150,
      "reason": "Why this is good for them today."
    }
  ],
  "safety_warnings": ["List of critical warnings based on their health conditions"],
  "avoid": ["Specific activities to avoid"]
}

SAFETY POLICY:
- If a user has a condition (e.g., Knee Injury), NEVER suggest high-impact movements.
- Prioritize the "Safe Exercises" provided in the context.
            """
        )
        self.rag = SimpleRagTool()

    def _calculate_bmi(self, profile: Dict[str, Any]) -> float:
        """Helper to calculate BMI from profile data."""
        try:
            height_m = float(profile.get('height', 170)) / 100
            weight_kg = float(profile.get('weight', 70))
            return round(weight_kg / (height_m * height_m), 1)
        except:
            return 22.0

    def _calculate_bmr(self, profile: Dict[str, Any]) -> float:
        """Calculate BMR using Mifflin-St Jeor Equation."""
        try:
            weight = float(profile.get('weight', 70))
            height = float(profile.get('height', 170))
            age = float(profile.get('age', 30))
            gender = profile.get('gender', 'Male').lower()
            
            bmr = (10 * weight) + (6.25 * height) - (5 * age)
            if 'female' in gender:
                bmr -= 161
            else:
                bmr += 5
            
            # Map activity level to factor
            activity_map = {
                "sedentary": 1.2,
                "lightly active": 1.375,
                "moderately active": 1.55,
                "very active": 1.725,
                "extra active": 1.9
            }
            factor = activity_map.get(profile.get('activity', '').lower(), 1.2)
            return bmr * factor
        except:
            return 2000.0

    def _determine_calorie_status(self, bmr: float, nutrition_info: str) -> str:
        """Extract calorie count from nutrition info and compare to BMR."""
        if not nutrition_info:
            return "Maintenance (No nutrition data)"
        
        match = re.search(r"Total Calories:\s*(\d+)", nutrition_info)
        if match:
            intake = int(match.group(1))
            if intake > (bmr * 0.4):
                return f"Surplus Detected ({intake} kcal meal)"
            elif intake < (bmr * 0.15):
                return f"Deficit/Light Meal ({intake} kcal)"
        
        return "Maintenance/Balanced"

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute fitness advice task and return structured JSON.
        """
        logger.info("[FitnessAgent] Analyzing task: %s", task)
        
        # 1. Extract Context
        user_profile = {}
        health_conditions = []
        nutrition_info = ""

        if context:
            for msg in context:
                if msg.get("type") == "user_context":
                    try:
                        content = msg.get("content", "{}")
                        if isinstance(content, str):
                            content = content.replace("'", '"')
                            user_profile = json.loads(content)
                        else:
                            user_profile = content
                        
                        health_conditions = user_profile.get("conditions", [])
                    except Exception as e:
                        logger.warning(f"[FitnessAgent] Failed to parse user_context: {e}")
                
                elif msg.get("from") == "nutrition":
                    nutrition_info = msg.get("content", "")
        
        # 2. Get Safe Recommendations from RAG
        rag_data = self.rag.get_safe_recommendations(task, health_conditions)
        safe_ex_list = [f"{e['name']} (Reason: {e.get('description', '')})" for e in rag_data['safe_exercises']]
        warnings = rag_data['safety_warnings']
        
        # 3. Dynamic Calculation
        bmr = self._calculate_bmr(user_profile)
        calorie_status = self._determine_calorie_status(bmr, nutrition_info)
        bmi = self._calculate_bmi(user_profile)
        
        # 4. Build Dynamic Prompt Supplement
        dynamic_context = f"""
USER PROFILE: BMI {bmi}, Calorie Maintenance {round(bmr)} kcal, Conditions: {health_conditions}.
CALORIE STATUS: {calorie_status}.
RAG SAFE EXERCISES: {safe_ex_list}.
RAG SAFETY WARNINGS: {warnings}.
"""
        
        full_task = f"{task}\n\nCONTEXT:\n{dynamic_context}\n\nBased on this, return EXACTLY a JSON object with keys: summary, recommendations, safety_warnings, avoid."
        
        result_str = super().execute(full_task, context)
        
        # Validation/Cleanup
        try:
            clean_str = result_str.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[-1].split("```")[0].strip()
            
            # Verify valid JSON
            json.loads(clean_str)
            return clean_str
        except Exception as e:
            logger.error(f"[FitnessAgent] Failed to parse structured output: {e}. Raw: {result_str}")
            return json.dumps({
                "summary": "Stay active safely!",
                "recommendations": [{"name": "Walking", "duration_min": 20, "kcal_estimate": 80, "reason": "General mobility"}],
                "safety_warnings": ["Consult a professional."],
                "avoid": []
            })
