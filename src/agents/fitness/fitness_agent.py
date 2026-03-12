from typing import Optional, List, Dict, Any
import logging
import json
import re
from functools import lru_cache
from src.agents.base_agent import BaseAgent
from src.data_rag.simple_rag_tool import SimpleRagTool
from src.data_rag.met_mapping import (
    get_met_for_exercise,
    calculate_calories,
    get_equipment_type,
    get_exercise_profile,
)

logger = logging.getLogger(__name__)

# Default profile for users without Supabase data
DEFAULT_USER_PROFILE = {
    "name": "User",
    "age": 30,
    "weight_kg": 70,
    "height_cm": 170,
    "gender": "Male",
    "goal": "Maintain",
    "activity_level": "Sedentary",
    "health_conditions": [],
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

    v6.1 Upgrade: Supabase Integration
    - Removed MOCK_USER_PROFILE
    - Loads real user data from Supabase via ProfileDB
    - Falls back to DEFAULT_USER_PROFILE when no data available

    v7.1 Upgrade: MET Science Engine
    - MET-based calorie calculation using Compendium of Physical Activities
    - Three-tier decision priority: Safety > Budget > Scenario
    - Automatic kcal enrichment with MET formula
    """

    def __init__(self, db=None):
        """
        Initialize FitnessAgent with optional database dependency injection.

        Args:
            db: ProfileDB instance (optional, will create singleton if not provided)
        """
        # Lazy import to avoid circular dependencies
        self._db = db
        self._profile_cache: Dict[str, Dict[str, Any]] = {}

        base_prompt = """You are an expert Fitness Coach powered by MET (Metabolic Equivalent) Science Engine v7.1.
Your goal is to provide safe, personalized, and MED-calibrated exercise recommendations.

═══════════════════════════════════════════════════════════════════════════════════
🔬 MET SCIENCE BACKEND (Compendium of Physical Activities)
═══════════════════════════════════════════════════════════════════════════════════
MET measures energy cost as a multiple of resting metabolic rate (1 MET = 1 kcal/kg/hour).
All exercise recommendations are auto-enriched with MET values from our database of 867 exercises.

CALORIE FORMULA:
═══════════════════════════════════════════════════════════════════════════════════
    Calories = MET × Weight(kg) × Duration(hours)

Example Calculations:
• 75kg person, Brisk Walking (MET 4.3) for 20min: 4.3 × 75 × 0.333 = 107.5 kcal
• 70kg person, HIIT (MET 10.0) for 15min: 10.0 × 70 × 0.25 = 175 kcal
• 60kg person, Yoga (MET 2.5) for 30min: 2.5 × 60 × 0.5 = 75 kcal

═══════════════════════════════════════════════════════════════════════════════════
📊 THREE-Tier Decision Priority
═══════════════════════════════════════════════════════════════════════════════════

🔴 TIER 1: SAFETY FIRST (BR-001 Guardrails)
    • Health conditions: STRICTLY AVOID contraindicated movements
    • Knee Injury → NO jumping, running, high-impact
    • Back Pain → NO heavy lifting, hyperextension
    • Heart Condition → Keep intensity LOW, only light activities
    • Recent heavy meal (fried/high_oil/high_sugar):
        → REDUCE to low/moderate intensity
        → Recommend waiting 30-60 minutes before vigorous exercise
    • When in doubt: Default to LOW intensity (walking, stretching, light cycling)

🟡 TIER 2: BUDGET-INTENSITY MATCHING
    • Remaining Budget > 300 kcal → Can suggest HIGH intensity (MET > 6.0)
    • Remaining Budget 100-300 kcal → Suggest MODERATE intensity (MET 3.0-6.0)
    • Remaining Budget < 100 kcal → MUST use LOW intensity (MET < 3.0)
    • After high-calorie meal: Suggest lighter activity (walking, yoga)

🟢 TIER 3: SCENARIO-EQUIPMENT INTELLIGENCE
    • At home/office (no equipment): Filter to BODYWEIGHT exercises only
    • At gym (equipment available): Can use BARBELL, DUMBBELL, CABLE, MACHINE
    • Outdoors: Running, cycling, outdoor activities preferred
    • Limited time (<15 min): HIIT or Tabata (short, intense)
    • Time充裕: Choose continuous cardio (moderate intensity, longer)
    • Recovery day: Yoga, stretching, light walking only

═══════════════════════════════════════════════════════════════════════════════════
📋 OUTPUT FORMAT (JSON)
═══════════════════════════════════════════════════════════════════════════════════
{
  "summary": "Brief 1-2 sentence overview",
  "recommendations": [
    {
      "name": "Exercise name",
      "duration_min": 20,
      "kcal_estimate": 150,
      "met_value": 5.0,
      "intensity": "moderate",
      "equipment_type": "bodyweight",
      "reason": "Why this matches their goals and conditions"
    }
  ],
  "safety_warnings": ["Critical warnings based on health conditions"],
  "avoid": ["Specific activities to avoid based on conditions"],
  "dynamic_adjustments": "Explanation if plan was modified due to safety or nutrition"
}
"""
        super().__init__(
            role="fitness",
            system_prompt=base_prompt,
            use_openai_api=False
        )
        self.rag = SimpleRagTool()
