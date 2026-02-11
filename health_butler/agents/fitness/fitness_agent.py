
"""Fitness Agent for exercise and wellness advice.

Provides personalized activity suggestions based on calorie intake,
user goals, and restrictions. Integrates with Nutrition Agent
output for contextual recommendations.
"""

import logging
from typing import Optional, List, Dict, Any
from src.agents.base_agent import BaseAgent

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
    It suggests activities based on calorie intake and user goals.
    
    Features (Prototype):
    - Uses a mock user profile for personalized advice.
    - Context-aware recommendations based on nutrition input.
    """
    
    def __init__(self):
        # Inject profile into system prompt
        profile_str = "\n".join([f"- {k}: {v}" for k, v in MOCK_USER_PROFILE.items()])
        
        super().__init__(
            role="fitness",
            system_prompt=f"""You are an expert Fitness Coach and Wellness Assistant.

CURRENT USER PROFILE:
{profile_str}

Your responsibilities:
1. Suggest post-meal activities to manage blood sugar and digestion.
2. Recommend specific exercises based on calculated calorie intake.
3. Motivate the user to stay active without being judgmental.
4. Adapt advice to the user's restrictions (e.g., if knee pain, suggest low impact).

LOGIC:
- If calorie intake is high -> Suggest calorie-burning activities (Walking, Swimming, Cycling).
- If intake is balanced -> Suggest maintenance activities.
- Always check 'restrictions' before suggesting exercises.

Keep your advice short, encouraging, and scientifically grounded. Speak directly to {MOCK_USER_PROFILE['name']}.
            """
        )

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute fitness advice task. Use context from Nutrition Agent if available.
        """
        logger.info("[FitnessAgent] Analyzing task: %s", task)
        
        # Check context for nutrition info to augment the prompt
        nutrition_context = ""
        if context:
            for msg in context:
                if msg.get("from") == "nutrition":
                    nutrition_context += f"\n[Context from Nutrition Agent]: {msg.get('content')}\n"
        
        full_task = task
        if nutrition_context:
            full_task = f"{task}\n\nRELEVANT NUTRITION DATA:{nutrition_context}\n\nBased on this meal and my profile, what should I do?"
            
        return super().execute(full_task, context)
