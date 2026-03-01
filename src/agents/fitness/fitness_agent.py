from typing import Optional, List, Dict, Any
import logging
import json
import re
from src.agents.base_agent import BaseAgent
from src.data_rag.simple_rag_tool import SimpleRagTool

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

# BR-001 Safety Disclaimer
BR001_DISCLAIMER = (
    "⚠️ Due to the recent consumption of fried/high-sugar food, "
    "I've adjusted your plan to lower intensity for your safety."
)

# Visual warning patterns to extract from task description
VISUAL_WARNING_PATTERNS = {
    "fried": [r"\bfried\b", r"\bdeep-fried\b", r"\bfried food\b"],
    "high_oil": [r"\bhigh[-_ ]?oil\b", r"\bhigh[-_ ]?fat\b", r"\bgreasy\b"],
    "high_sugar": [r"\bhigh[-_ ]?sugar\b", r"\bsugary\b", r"\bsweet\b", r"\bglazed\b"],
    "processed": [r"\bprocessed\b", r"\bprocessed food\b"]
}

class FitnessAgent(BaseAgent):
    """
    Specialist agent for providing exercise and wellness advice.

    Safety-First Evolution (Phase 7):
    - Real-time Context: Uses actual user profile and daily calorie status.
    - Simple RAG: Filters exercises based on JSON data (no vector DB).
    - Structured Output: Returns JSON for interactive Discord UI.

    Module 3: Dynamic Risk Filtering
    - Extracts visual warnings from Health Memo in task description
    - Passes dynamic_risks to RAG for intensity-based filtering
    - Double-validation before output
    - BR-001 safety disclaimer when adjustments made
    """

    def __init__(self):
        # Inject profile into system prompt
        profile_str = "\n".join([f"- {k}: {v}" for k, v in MOCK_USER_PROFILE.items()])

        base_prompt = """You are an expert Fitness Coach and Wellness Assistant.
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
  "avoid": ["Specific activities to avoid"],
  "dynamic_adjustments": "Optional: explanation if plan was adjusted due to nutrition"
}

SAFETY POLICY:
- If a user has a condition (e.g., Knee Injury), NEVER suggest high-impact movements.
- Prioritize the "Safe Exercises" provided in the context.
- If Health Memo indicates fried/high_oil/high_sugar food, REDUCE exercise intensity.
- After eating heavy meals, recommend waiting 30-60 minutes before vigorous exercise.
- When in doubt, suggest lower intensity alternatives (walking, light cycling, stretching).

DYNAMIC RISK VALIDATION:
Before finalizing recommendations, verify:
- Does this recommendation violate the visual warnings identified earlier?
- If user ate fried food, is the suggested intensity appropriate?
- If warnings present, have I included the BR-001 safety disclaimer?
"""

        system_prompt = (
            base_prompt
            + "\n\nDEFAULT USER PROFILE (for prototype/testing; may be overridden by context):\n"
            + profile_str
        )

        super().__init__(
            role="fitness",
            system_prompt=system_prompt,
            use_openai_api=False
        )
        self.rag = SimpleRagTool()

    def _extract_visual_warnings_from_task(self, task: str) -> List[str]:
        """
        Extract visual warning labels from Health Memo in task description.

        Looks for patterns like:
        - "Warnings: fried, high_oil"
        - "Health warnings: deep-fried, high-sugar"
        - "visual_warnings: ['fried', 'high_oil']"
        """
        warnings = []
        task_lower = task.lower()

        # Method 1: Look for explicit warning labels
        for warning, patterns in VISUAL_WARNING_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, task_lower):
                    warnings.append(warning)
                    break

        # Method 2: Parse JSON-like warning lists
        json_pattern = r"(?:warnings?|visual_warnings?)\s*[:=]\s*\[([^\]]+)\]"
        match = re.search(json_pattern, task_lower)
        if match:
            warning_str = match.group(1)
            for warning in ["fried", "high_oil", "high_sugar", "processed"]:
                if warning in warning_str and warning not in warnings:
                    warnings.append(warning)

        if warnings:
            logger.info(f"[FitnessAgent] Extracted visual warnings: {warnings}")

        return warnings

    def _validate_recommendations_against_warnings(
        self,
        recommendations: List[Dict],
        warnings: List[str]
    ) -> tuple:
        """
        Double-validation: Check if recommendations violate visual warnings.

        Returns:
            Tuple of (validated_recommendations, was_adjusted)
        """
        if not warnings:
            return recommendations, False

        # High-intensity keywords to check
        high_intensity = ["sprint", "fast run", "hiit", "jump", "burpee", "intense", "vigorous", "running"]

        validated = []
        was_adjusted = False

        for rec in recommendations:
            name = rec.get("name", "").lower()
            is_safe = True

            # Check if recommendation violates warnings
            for keyword in high_intensity:
                if keyword in name:
                    if "fried" in warnings or "high_oil" in warnings or "high_sugar" in warnings:
                        is_safe = False
                        was_adjusted = True
                        logger.info(f"[FitnessAgent] Blocked high-intensity: {rec.get('name')}")
                        break

            if is_safe:
                validated.append(rec)
            else:
                # Replace with lower intensity alternative
                validated.append({
                    "name": "Brisk Walking",
                    "duration_min": 20,
                    "kcal_estimate": 100,
                    "reason": "Lower intensity alternative - recent meal requires lighter activity"
                })

        return validated, was_adjusted

    def _calculate_bmi(self, profile: Dict[str, Any]) -> float:
        """Helper to calculate BMI from profile data."""
        try:
            height_m = float(profile.get('height', profile.get('height_cm', 170))) / 100
            weight_kg = float(profile.get('weight', profile.get('weight_kg', 70)))
            return round(weight_kg / (height_m * height_m), 1)
        except:
            return 22.0

    def _calculate_bmr(self, profile: Dict[str, Any]) -> float:
        """Calculate BMR using Mifflin-St Jeor Equation."""
        try:
            weight = float(profile.get('weight', profile.get('weight_kg', 70)))
            height = float(profile.get('height', profile.get('height_cm', 170)))
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

    def _extract_calories_from_nutrition_info(self, nutrition_info: str) -> Optional[float]:
        """Extract calories from nutrition handoff text or JSON payload."""
        if not nutrition_info:
            return None

        try:
            parsed = json.loads(nutrition_info)
            if isinstance(parsed, dict):
                total_macros = parsed.get("total_macros", {})
                calories = total_macros.get("calories")
                if calories is not None:
                    return float(calories)
        except Exception:
            pass

        regex_patterns = [
            r"Total Calories:\s*(\d+(?:\.\d+)?)",
            r'"calories"\s*:\s*(\d+(?:\.\d+)?)',
            r"(\d+(?:\.\d+)?)\s*kcal",
            r"(\d+(?:\.\d+)?)\s*calories",
        ]
        for pattern in regex_patterns:
            match = re.search(pattern, nutrition_info, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except Exception:
                    continue

        return None

    def _determine_calorie_status(self, bmr: float, nutrition_info: str) -> str:
        """Extract calorie count from nutrition info and compare to BMR."""
        if not nutrition_info:
            return "Maintenance (No nutrition data)"

        intake = self._extract_calories_from_nutrition_info(nutrition_info)
        if intake is not None:
            if intake > (bmr * 0.4):
                return f"Surplus Detected ({int(intake)} kcal meal)"
            if intake < (bmr * 0.15):
                return f"Deficit/Light Meal ({int(intake)} kcal)"
        
        return "Maintenance/Balanced"

    async def execute_async(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Asynchronous execution for fitness advice.
        Includes on-the-fly image fetching for recommended exercises.
        """
        logger.info("[FitnessAgent] Executing async task: %s", task[:100] + "...")
        
        # 1. Extract visual warnings
        visual_warnings = self._extract_visual_warnings_from_task(task)
        
        # 2. Extract context
        user_profile = {}
        health_conditions = []
        nutrition_info = ""

        if context:
            for msg in context:
                if msg.get("type") in ("user_context", "user_profile"):
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
                elif msg.get("from") == "nutrition" or msg.get("type") == "nutrition_summary":
                    nutrition_info = msg.get("content", "")

        # 3. Get recommendations from RAG
        # Note: SimpleRagTool.get_safe_recommendations is still sync for core matching
        rag_data = self.rag.get_safe_recommendations(
            task,
            health_conditions,
            dynamic_risks=visual_warnings
        )
        
        # 4. Attach images asynchronously
        safe_exercises = await self.rag.attach_exercise_images_async(rag_data['safe_exercises'])
        
        safe_ex_list = []
        for e in safe_exercises:
            img_snippet = f" [Image: {e['image_url']}]" if e.get('image_url') else ""
            safe_ex_list.append(f"{e['name']}{img_snippet} (Reason: {e.get('description', '')})")
            
        # 5. Dynamic Calculations
        bmr = self._calculate_bmr(user_profile)
        calorie_status = self._determine_calorie_status(bmr, nutrition_info)
        bmi = self._calculate_bmi(user_profile)
        
        # 6. Build Prompt
        health_memo_section = ""
        if visual_warnings:
            health_memo_section = f"\nHEALTH MEMO ALERT: Warnings detected {visual_warnings}. Reduce intensity. Include BR-001 disclaimer.\n"

        dynamic_context = f"""
{health_memo_section}
USER PROFILE: BMI {bmi}, Calorie Maintenance {round(bmr)} kcal, Conditions: {health_conditions}.
CALORIE STATUS: {calorie_status}.
RAG SAFE EXERCISES: {safe_ex_list}.
"""
        full_task = f"{task}\n\nCONTEXT:\n{dynamic_context}\n\nReturn EXACTLY a JSON object."
        
        # Call base agent's execute (which is synchronous but we can run it in a thread or just call it)
        # BaseAgent.execute usually calls the LLM.
        import asyncio
        result_str = await asyncio.to_thread(super().execute, full_task, context)
        
        # 7. Post-process and inject images into JSON recommendations if missing
        try:
            clean_str = result_str.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            result_json = json.loads(clean_str)
            
            # Map images back to recommendations based on name matching
            img_map = {e['name'].lower(): e.get('image_url') for e in safe_exercises}
            for rec in result_json.get("recommendations", []):
                rec_name = rec.get("name", "").lower()
                if not rec.get("image_url") and rec_name in img_map:
                    rec["image_url"] = img_map[rec_name]
                elif not rec.get("image_url"):
                    # Last resort: try to fetch for the specific name returned by LLM
                    rec["image_url"] = await self.rag.wger_client.search_exercise_image_async(rec.get("name"))

            # Safety validation (Restored from sync version)
            if visual_warnings and "recommendations" in result_json:
                validated_recs, was_adjusted = self._validate_recommendations_against_warnings(
                    result_json["recommendations"],
                    visual_warnings
                )
                result_json["recommendations"] = validated_recs
                if was_adjusted:
                    result_json["safety_warnings"] = result_json.get("safety_warnings", []) + [BR001_DISCLAIMER]
                    result_json["dynamic_adjustments"] = BR001_DISCLAIMER

            return json.dumps(result_json)
            
        except Exception as e:
            logger.error(f"[FitnessAgent] Async post-process failed: {e}")
            return result_str

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute fitness advice task and return structured JSON.

        Module 3: Now includes dynamic risk filtering based on Health Memo.
        """
        logger.info("[FitnessAgent] Analyzing task: %s", task[:100] + "...")

        # 1. Extract visual warnings from task (Health Memo)
        visual_warnings = self._extract_visual_warnings_from_task(task)
        if visual_warnings:
            logger.info(f"[FitnessAgent] Health Memo warnings detected: {visual_warnings}")

        # 2. Extract Context
        user_profile = {}
        health_conditions = []
        nutrition_info = ""

        if context:
            for msg in context:
                if msg.get("type") in ("user_context", "user_profile"):
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

                elif msg.get("from") == "nutrition" or msg.get("type") == "nutrition_summary":
                    nutrition_info = msg.get("content", "")

        # 3. Get Safe Recommendations from RAG with dynamic risks
        rag_data = self.rag.get_safe_recommendations(
            task,
            health_conditions,
            dynamic_risks=visual_warnings  # Module 3: Pass dynamic risks
        )
        safe_ex_list = [f"{e['name']} (Reason: {e.get('description', '')})" for e in rag_data['safe_exercises']]
        warnings = rag_data.get('safety_warnings', [])
        dynamic_adjustments = rag_data.get('dynamic_adjustments')

        # 4. Dynamic Calculation
        bmr = self._calculate_bmr(user_profile)
        calorie_status = self._determine_calorie_status(bmr, nutrition_info)
        bmi = self._calculate_bmi(user_profile)
        nutrition_snippet = nutrition_info or ""
        if len(nutrition_snippet) > 1500:
            nutrition_snippet = nutrition_snippet[:1500] + "...(truncated)"

        # 5. Build Dynamic Prompt Supplement
        health_memo_section = ""
        if visual_warnings:
            health_memo_section = f"""
HEALTH MEMO ALERT:
- Visual warnings detected: {visual_warnings}
- User recently consumed food with health concerns
- MUST reduce exercise intensity accordingly
- MUST include BR-001 disclaimer in response
"""

        dynamic_context = f"""
{health_memo_section}
USER PROFILE: BMI {bmi}, Calorie Maintenance {round(bmr)} kcal, Conditions: {health_conditions}.
CALORIE STATUS: {calorie_status}.
RELEVANT NUTRITION DATA: {nutrition_snippet}
RAG SAFE EXERCISES: {safe_ex_list}.
RAG SAFETY WARNINGS: {warnings}.
DYNAMIC ADJUSTMENTS: {dynamic_adjustments}.
"""

        full_task = f"{task}\n\nCONTEXT:\n{dynamic_context}\n\nBased on this, return EXACTLY a JSON object with keys: summary, recommendations, safety_warnings, avoid, dynamic_adjustments."

        result_str = super().execute(full_task, context)

        # 6. Validation/Cleanup
        try:
            clean_str = result_str.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[-1].split("```")[0].strip()

            # Verify valid JSON
            result_json = json.loads(clean_str)

            # 7. Double-validation: Check recommendations against visual warnings
            if visual_warnings and "recommendations" in result_json:
                validated_recs, was_adjusted = self._validate_recommendations_against_warnings(
                    result_json["recommendations"],
                    visual_warnings
                )
                result_json["recommendations"] = validated_recs

                # Add BR-001 disclaimer if adjustments were made
                if was_adjusted or dynamic_adjustments:
                    if "safety_warnings" not in result_json:
                        result_json["safety_warnings"] = []
                    result_json["safety_warnings"].append(BR001_DISCLAIMER)
                    result_json["dynamic_adjustments"] = BR001_DISCLAIMER

            return json.dumps(result_json)

        except Exception as e:
            logger.error(f"[FitnessAgent] Failed to parse structured output: {e}. Raw: {result_str}")
            raw = (result_str or "").strip()
            if raw:
                return raw
            # Return a minimal safe JSON payload with disclaimer if warnings present
            fallback = {
                "summary": "Stay active safely!",
                "recommendations": [
                    {
                        "name": "Walking",
                        "duration_min": 20,
                        "kcal_estimate": 80,
                        "reason": "General mobility - safe for all conditions",
                    }
                ],
                "safety_warnings": ["Consult a professional."],
                "avoid": [],
            }
            if visual_warnings:
                fallback["safety_warnings"].append(BR001_DISCLAIMER)
                fallback["dynamic_adjustments"] = BR001_DISCLAIMER
            return json.dumps(fallback)
