import json
from typing import Dict, Any, List, Optional
from src.agents.base_agent import BaseAgent

class AnalyticsAgent(BaseAgent):
    """
    Agent specialized in health data analytics, trend analysis, 
    anomaly detection, and goal forecasting.
    """
    def __init__(self, **kwargs):
        system_prompt = """You are the Analytics Agent for the Personal Health Butler.
Your role is to process historical health data and derive deep insights.

Responsibilities:
1. Trend Analysis: Identify if the user is trending up or down in calories, protein, or activity.
2. Anomaly Detection: Flag deviations like 3+ days of over-eating or a sudden drop in workouts.
3. Predictive Coaching: Estimate when the user will reach their target weight based on current net calorie averages.
4. Actionable Insights: Provide specific, data-backed advice (e.g., "Your protein intake has dropped 20% this week, consider adding a post-workout shake").
5. Visual Trends: Generate text-based sparklines (e.g. █▇▆▄▃▂ ) to represent data fluctuations.

Tone: Analytical, objective, encouraging. Use percentages and dates.
Format: Respond in structured JSON for the Discord Bot.
"""
        super().__init__(role="analytics", system_prompt=system_prompt, **kwargs)

    async def analyze_trends(self, historical_data: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes historical stats into a trend report.
        """
        prompt = f"""Analyze the following historical health data for this user.
Historical Data (Daily Aggregations): {json.dumps(historical_data)}
User Profile: {json.dumps(user_profile)}

Tasks:
1. Calculate average daily net calories vs maintenance (Mifflin-St Jeor).
2. Identify a '7-day trend' for calories and activity (Improving/Declining/Stable).
3. Detect any anomalies (e.g. 3-day slump).
4. Predict the 'Target Goal Achievement Date' if current trends continue.

Return JSON: 
{{
  "trend_summary": "...",
  "status_indicators": {{
     "calories": "improving|declining|stable",
     "activity": "improving|declining|stable"
  }},
  "anomalies": ["...", "..."],
  "goal_forecast": {{
     "estimated_date": "YYYY-MM-DD",
     "confidence": "high|medium|low",
     "insight": "..."
  }},
  "weekly_stats": {{
     "avg_net_calories": 0,
     "avg_active_minutes": 0,
     "protein_consistency": "high|medium|low"
  }},
   "sparklines": {{
      "calories": "█▇▆▄",
      "activity": " ▂▄▆"
   }}
}}
"""
        response = await self.execute_async(prompt)
        try:
            return json.loads(self._extract_json(response))
        except:
            return {
                "trend_summary": response,
                "status_indicators": {"calories": "stable", "activity": "stable"},
                "anomalies": [],
                "goal_forecast": {"estimated_date": "N/A", "confidence": "low", "insight": "More data needed"},
                "weekly_stats": {"avg_net_calories": 0, "avg_active_minutes": 0, "protein_consistency": "low"}
            }

    def _extract_json(self, response: str) -> str:
        """Helper to extract JSON from markdown blocks."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0].strip()
        if "```" in response:
            # Try to handle cases where it might just be a generic code block
            parts = response.split("```")
            if len(parts) >= 3:
                return parts[1].strip()
        return response.strip()
