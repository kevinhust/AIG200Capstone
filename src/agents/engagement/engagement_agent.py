import json
from typing import Dict, Any, List, Optional
from src.agents.base_agent import BaseAgent

class EngagementAgent(BaseAgent):
    """
    Agent specialized in proactive engagement, daily summaries, and health coaching.
    """
    def __init__(self, **kwargs):
        system_prompt = """You are the Engagement Agent for the Personal Health Butler.
Your role is to be a proactive, supportive, and data-driven health companion.

Responsibilities:
1. Morning Check-in: Provide a warm greeting, mention the importance of today's health goals, and give a quick motivational tip.
2. Daily Summary: Analyze a user's nutrition and workout logs (provided in context) to summarize their progress.
3. Proactive Reminders: Generate friendly nudges for hydration or movement based on idle patterns.
4. Tomorrow's Strategy: Suggest one specific area of focus for the next day based on today's gaps.

Tone: Professional yet warm (Premium Digital Butler). Use precise metrics when available.
Format: Respond in structured JSON when possible to assist the Discord Bot in rendering Embeds.
"""
        super().__init__(role="engagement", system_prompt=system_prompt, **kwargs)

    async def generate_morning_greeting(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a personalized morning greeting prompt result.
        """
        prompt = f"""Generate a morning check-in for this user.
Context: {json.dumps(user_context)}
Include:
- A warm greeting using their name.
- A reminder of their primary goal.
- A small 'Butler Tip' for the day.
Return JSON: {{"greeting": "...", "tip": "...", "focus_goal": "..."}}
"""
        response = await self.execute_async(prompt)
        try:
            return json.loads(self._extract_json(response))
        except:
            return {"greeting": response, "tip": "Consistency is key!", "focus_goal": "Stay active"}

    async def generate_daily_report(self, daily_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarizes the day's performance based on logs.
        """
        prompt = f"""Analyze today's health data for this user and provide a summary.
Daily Data: {json.dumps(daily_data)}
User Profile: {json.dumps(user_context)}

Include:
- Calories Consumed vs Target.
- Calories Burned via Workout.
- Net Calories.
- A 1-sentence assessment of the day.
- One 'Tomorrow Optimization' suggestion.

Return JSON: {{"summary_text": "...", "status": "on_track|over_limit|under_target", "burned": 0, "consumed": 0, "net": 0, "tomorrow_tip": "..."}}
"""
        response = await self.execute_async(prompt)
        try:
            return json.loads(self._extract_json(response))
        except:
            return {"summary_text": response, "status": "completed", "burned": 0, "consumed": 0, "net": 0, "tomorrow_tip": "Reflect on today's success."}

    def _extract_json(self, response: str) -> str:
        """Helper to extract JSON from markdown blocks if necessary."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        if "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()
