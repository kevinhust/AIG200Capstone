"""
Coordinator Agent for Health Butler AI system.

Routes user requests to appropriate specialist agents (Nutrition/Fitness)
based on keyword analysis and health context. Extends RouterAgent
with health-specific delegation logic.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from src.agents.router_agent import RouterAgent
from src.config import settings
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)

_PROFILE_QUERY_PATTERNS = [
    r"\bwho\s*am\s*i\b",
    r"\bwhoami\b",
    r"\bmy\s+profile\b",
    r"\bshow\s+(me\s+)?(my\s+)?profile\b",
    r"\b(profile|stats|metrics)\b\s*\??$",
    r"\bwhat('?s| is)\s+my\s+(name|age|height|weight|goal|diet|conditions|activity|preferences)\b",
    r"\bmy\s+(name|age|height|weight|goal|goals|diet|conditions|activity|preferences)\b\s*\??$",
    r"\b(daily\s+)?calorie\s+target\b",
    r"\btarget\s+calories\b",
    r"\bdaily\s+target\b",
]


def _matches_any_pattern(text_lower: str, patterns: List[str]) -> bool:
    return any(re.search(p, text_lower) for p in patterns)


class CoordinatorAgent(RouterAgent):
    """
    Health-specific Router Agent with enhanced context management.
    
    Responsibilities:
    - Route requests to Nutrition or Fitness agents
    - Load and pass user profiles to agents
    - Chain Nutrition output to Fitness input (meal → exercise advice)
    - Maintain conversation context for goal tracking
    """
    
    def __init__(self):
        system_prompt = """You are the Coordinator Agent for the Personal Health Butler AI.
Your ONLY job is to analyze the user's message and decide which specialist agent(s) should handle it.

## Available Specialist Agents

### nutrition
Handles: Food analysis, calorie counting, meal logging, dietary advice, macro tracking.
Route here when: User mentions food, eating, meals, calories, macros, recipes, ingredients, diet plans, nutritional info, or uploads a food image.
Example queries: "I ate a burger", "How many calories in rice?", "Analyze this meal", "What should I eat?"

### fitness
Handles: Exercise recommendations, workout plans, activity tracking, step counting, weight goals, body measurements, physical health metrics.
Route here when: User asks about exercise, workouts, weight loss/gain goals, BMI, body stats, height, weight, steps, running, gym, yoga, stretching, or any physical activity.
Example queries: "Suggest an exercise", "How tall am I?", "What workout should I do?", "I want to lose weight", "How many steps today?"

### profile/identity (route to fitness)
Handles: Requests about the user's own onboarding/profile details.
Route here when: User asks who they are, asks for their profile/stats, or asks about their saved goal/conditions/preferences.
Example queries: "Who am I?", "Show my profile", "What are my goals?"

## Routing Rules
1. If the message is about FOOD or EATING → route to "nutrition"
2. If the message is about EXERCISE, BODY STATS, or FITNESS → route to "fitness"
3. If the message mentions EATING + wants exercise advice → route to BOTH: first "nutrition", then "fitness"
4. If the message is about the USER'S PROFILE / IDENTITY → route to "fitness"
5. If the message is a general health question → route to the MOST relevant agent
6. If truly ambiguous → route to "nutrition" (the app's primary focus)

## IMPORTANT
- Do NOT always default to nutrition. Read the user's intent carefully.
- Questions about body measurements (height, weight, BMI) → fitness
- Questions about food, meals, diet → nutrition
- "How tall am I?" → fitness (body stats)
- "What did I eat?" → nutrition (meal history)

You MUST respond with a valid JSON planning object.
"""
        # Initialize BaseAgent directly to override Router's role
        super(CoordinatorAgent, self).__init__(role="coordinator", system_prompt=system_prompt, use_openai_api=False)

    def analyze_and_delegate(self, user_task: str) -> List[Dict[str, Any]]:
        """
        Analyze task using Gemini Structured Output for 100% reliable JSON.
        """
        task_lower = (user_task or "").strip().lower()
        if task_lower and _matches_any_pattern(task_lower, _PROFILE_QUERY_PATTERNS):
            # Avoid routing profile/identity queries to nutrition.
            return [
                {
                    "agent": "fitness",
                    "task": "Show the user's saved profile details and current goals/preferences.",
                }
            ]

        if not self.client:
            logger.warning("Coordinator client is None, using keyword fallback")
            return self._simple_delegate(user_task)

        prompt = f"""Analyze the following user message and decide which agent(s) should handle it.

USER MESSAGE: "{user_task}"

Decide: should this go to "nutrition", "fitness", or both?
Return a JSON object with a "delegations" array."""

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=self.system_prompt + "\n\n" + prompt,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "delegations": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "agent": {"type": "STRING"},
                                        "task": {"type": "STRING"}
                                    },
                                    "required": ["agent", "task"]
                                }
                            }
                        },
                        "required": ["delegations"]
                    }
                )
            )
            
            data = response.parsed
            if isinstance(data, dict) and "delegations" in data:
                # Validate agent names — only allow known agents
                valid_delegations = []
                for d in data["delegations"]:
                    agent = d.get("agent", "").lower().strip()
                    if agent in ("nutrition", "fitness"):
                        valid_delegations.append({"agent": agent, "task": d.get("task", user_task)})
                
                if valid_delegations:
                    return valid_delegations
            
            return self._simple_delegate(user_task)
            
        except Exception as e:
            logger.error(f"CoordinatorAgent delegation failed: {e}")
            return self._simple_delegate(user_task)

    def _simple_delegate(self, task: str) -> List[Dict[str, Any]]:
        """
        Enhanced health-specific fallback delegation with chaining support.
        Uses comprehensive keyword matching when LLM routing is unavailable.
        """
        task_lower = task.lower()
        delegations = []

        # ── Profile / identity queries should not go to nutrition ──
        if task_lower and _matches_any_pattern(task_lower, _PROFILE_QUERY_PATTERNS):
            delegations.append({"agent": "fitness", "task": task})
            return delegations
        
        # ── Fitness-first keywords (body stats, exercise, goals) ──
        fitness_keywords = [
            # Exercise & workout
            'exercise', 'workout', 'work out', 'gym', 'fitness', 'training',
            'stretch', 'yoga', 'cardio', 'hiit', 'plank', 'squat', 'pushup',
            'push-up', 'pull-up', 'pullup', 'deadlift', 'bench press',
            # Activity tracking
            'walk', 'run', 'jog', 'swim', 'bike', 'cycling', 'steps',
            'activity', 'active', 'sedentary',
            # Body stats & measurement
            'tall', 'height', 'weight', 'bmi', 'body', 'muscle', 'fat percentage',
            # Goals
            'goal', 'progress', 'track', 'lose weight', 'gain muscle',
            'weight loss', 'weight gain', 'bulk', 'cut',
            # Recommendations
            'suggest exercise', 'recommend exercise', 'what exercise',
            'what workout', 'how to burn',
            # Completion tracking
            'completed', 'finished', 'done with',
        ]
        
        # ── Nutrition-first keywords (food, meals, calories) ──
        nutrition_keywords = [
            # Food & eating
            'food', 'eat', 'ate', 'eating', 'eaten',
            'calorie', 'calories', 'kcal',
            'meal', 'meals', 'dish',
            'nutrition', 'nutrient', 'nutritional',
            'diet', 'dietary',
            # Meals of the day
            'lunch', 'dinner', 'breakfast', 'brunch', 'snack', 'supper',
            # Food items
            'recipe', 'ingredient', 'cook', 'cooking',
            'protein', 'carb', 'carbs', 'fat', 'fiber', 'sugar', 'sodium',
            # Macro tracking
            'macro', 'macros', 'intake', 'portion',
            # Analysis
            'analyze this meal', 'what did i eat', 'how many calories',
        ]
        
        has_fitness = any(word in task_lower for word in fitness_keywords)
        has_nutrition = any(word in task_lower for word in nutrition_keywords)
        
        # ── Both detected: check for chaining (ate → exercise) ──
        if has_nutrition and has_fitness:
            delegations.append({'agent': 'nutrition', 'task': task})
            delegations.append({'agent': 'fitness', 'task': 'Based on the previous nutrition analysis, suggest appropriate exercises.'})
            return delegations
        
        # ── Meal + "ate" pattern → chain both ──
        if has_nutrition and ('ate' in task_lower or 'just ate' in task_lower or 'i ate' in task_lower):
            delegations.append({'agent': 'nutrition', 'task': task})
            delegations.append({'agent': 'fitness', 'task': 'Suggest exercises to balance this meal intake'})
            return delegations
        
        # ── Fitness only ──
        if has_fitness:
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations
        
        # ── Nutrition only ──
        if has_nutrition:
            delegations.append({'agent': 'nutrition', 'task': task})
            return delegations
        
        # ── Default to nutrition if truly ambiguous ──
        delegations.append({'agent': 'nutrition', 'task': task})
        return delegations
    
    def supports_chaining(self) -> bool:
        """Indicate that this coordinator supports agent chaining."""
        return True
