"""
Enhanced Fitness Agent with personalized recommendations, goal setting, and preference learning.

Provides exercise recommendations based on:
- User health profile (age, weight, limitations)
- Nutrition data from Nutrition Agent (calories, macros)
- Exercise preferences learned over time
- Scientific MET values for accurate calorie calculations
"""

import logging
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from src.agents.base_agent import BaseAgent
from health_butler.data.user_profiles import UserProfile, FitnessGoal, get_user_profile, save_user_profile
from health_butler.data_rag.exercise_rag_tool import ExerciseRagTool

logger = logging.getLogger(__name__)


class FitnessAgent(BaseAgent):
    """
    Enhanced specialist agent for personalized fitness guidance.
    
    Capabilities:
    - Personalized exercise recommendations based on health limitations
    - SMART goal setting and tracking
    - Preference learning from completion history
    - Calorie-to-exercise calculations using MET values
    - Context-aware suggestions (time of day, equipment available)
    """
    
    def __init__(self):
        super().__init__(
            role="fitness",
            system_prompt="""You are an expert Fitness Coach and Wellness Assistant with deep knowledge of exercise science.

Your responsibilities:
1. **Personalized Recommendations**: Suggest exercises tailored to the user's:
   - Health limitations (avoid contraindicated activities)
   - Fitness level (beginner, intermediate, advanced)
   - Available equipment (home, gym, outdoor)
   - Preferred activities (learn from completion history)
   - Current context (time of day, weather considerations)

2. **Goal Setting**: Help users create SMART fitness goals:
   - Specific: Clear, well-defined objectives
   - Measurable: Track with numbers (kg, km, days, reps)
   - Achievable: Realistic given user's current state
   - Relevant: Aligned with user's health objectives
   - Time-bound: Set clear deadlines

3. **Calorie Balance**: Calculate exercise recommendations based on nutritional intake:
   - Use precise MET values for calorie burn calculations
   - Example: "You ate 850 calories. Try a 45-min brisk walk (burns ~280 cal) plus 20-min yoga."
   - Consider daily totals, not just individual meals

4. **Motivational Coaching**:
   - Be encouraging and supportive, never judgmental
   - Celebrate progress and milestones
   - Provide evidence-based fitness advice
   - Adapt advice to user feedback

5. **Safety First**:
   - Always consider health limitations
   - Recommend warm-up and cool-down when appropriate
   - Suggest modifications for different fitness levels
   - Advise medical consultation for new exercisers

When you receive nutrition data, integrate it seamlessly into your recommendations.
When suggesting exercises, always query the exercise database for accurate MET values.
Keep advice concise, actionable, and scientifically grounded.
"""
        )
        
        # Initialize tools
        try:
            self.exercise_rag = ExerciseRagTool()
        except Exception as e:
            logger.warning(f"Exercise RAG not available: {e}. Will use LLM knowledge only.")
            self.exercise_rag = None
        
        # User profile loaded per session (passed in context)
        self.user_profile: Optional[UserProfile] = None

    def execute(self, task: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute fitness coaching task with enhanced capabilities.
        
        Args:
            task: User request or nutrition handoff data
            context: Optional context including user_profile, nutrition_data, etc.
            
        Returns:
            Personalized fitness recommendation
        """
        logger.info(f"[FitnessAgent] Analyzing task: {task}")
        
        # Parse context for user profile and nutrition data
        self.user_profile = self._extract_user_profile(context)
        nutrition_data = self._extract_nutrition_data(context)
        
        # Check if this is a goal-setting request
        if any(keyword in task.lower() for keyword in ["set goal", "create goal", "new goal", "fitness goal"]):
            return self._handle_goal_setting(task)
        
        # Check if this is a goal progress check
        if any(keyword in task.lower() for keyword in ["progress", "how am i doing", "goal status"]):
            return self._handle_goal_progress()
        
        # Check if completing an exercise
        if any(keyword in task.lower() for keyword in ["completed", "finished", "done with"]):
            return self._handle_exercise_completion(task)
        
        # Standard recommendation with enhanced context
        enriched_task = self._enrich_task_with_tools(task, nutrition_data)
        
        return super().execute(enriched_task, context)
    
    def _extract_user_profile(self, context: Optional[List[Dict]]) -> Optional[UserProfile]:
        """Extract user profile from context or load from disk."""
        if context:
            for msg in context:
                if msg.get("type") == "user_profile":
                    profile_data = msg.get("content")
                    if isinstance(profile_data, dict):
                        return UserProfile.from_dict(profile_data)
        
        # Fallback: try to load from disk
        try:
            return get_user_profile()
        except Exception as e:
            logger.warning(f"Could not load user profile: {e}")
            return None
    
    def _extract_nutrition_data(self, context: Optional[List[Dict]]) -> Optional[Dict]:
        """Extract nutrition analysis data from context."""
        if context:
            for msg in context:
                if msg.get("from") == "nutrition" or msg.get("type") == "nutrition_data":
                    content = msg.get("content")
                    if isinstance(content, dict):
                        return content
        return None
    
    def _enrich_task_with_tools(self, task: str, nutrition_data: Optional[Dict]) -> str:
        """Enrich the task with exercise database queries and user context."""
        enriched_parts = [task]
        
        # Add user profile context
        if self.user_profile:
            enriched_parts.append(f"\n\n**User Profile Context:**")
            enriched_parts.append(f"- Age: {self.user_profile.age}, Weight: {self.user_profile.weight_kg}kg")
            enriched_parts.append(f"- Fitness Level: {self.user_profile.fitness_level}")
            if self.user_profile.health_limitations:
                enriched_parts.append(f"- Health Limitations: {', '.join(self.user_profile.health_limitations)}")
            if self.user_profile.available_equipment:
                enriched_parts.append(f"- Available Equipment: {', '.join(self.user_profile.available_equipment)}")
            if self.user_profile.active_goals:
                enriched_parts.append(f"- Active Goals: {len(self.user_profile.active_goals)}")
            
            # Add top preferences
            top_prefs = self.user_profile.get_top_preferences(3)
            if top_prefs:
                pref_str = ", ".join([f"{ex} ({count}x)" for ex, count in top_prefs])
                enriched_parts.append(f"- Preferred Activities: {pref_str}")
        
        # Add nutrition context
        if nutrition_data:
            enriched_parts.append(f"\n\n**Nutrition Context:**")
            if "total_calories" in nutrition_data:
                enriched_parts.append(f"- Just consumed: {nutrition_data['total_calories']} calories")
            if "macros" in nutrition_data:
                macros = nutrition_data["macros"]
                enriched_parts.append(f"- Macros: {macros.get('protein', 0)}g protein, {macros.get('carbs', 0)}g carbs, {macros.get('fat', 0)}g fat")
        
        # Query exercise database for recommendations
        if self.exercise_rag and self.user_profile:
            exercise_suggestions = self._query_suitable_exercises()
            if exercise_suggestions:
                enriched_parts.append(f"\n\n**Available Exercises (from database):**")
                for ex in exercise_suggestions[:5]:  # Top 5
                    meta = ex['metadata']
                    enriched_parts.append(
                        f"- {meta['activity'].replace('_', ' ').title()}: "
                        f"{meta['met_value']} METs, {meta['category']}, {meta['intensity']} intensity"
                    )
                    
                    # Calculate calorie burn example
                    if nutrition_data and "total_calories" in nutrition_data:
                        duration = self.exercise_rag.suggest_duration_for_calories(
                            meta['met_value'],
                            self.user_profile.weight_kg,
                            nutrition_data['total_calories'] * 0.3  # Suggest burning 30% of intake
                        )
                        calories_burned = self.exercise_rag.calculate_calorie_burn(
                            meta['met_value'],
                            self.user_profile.weight_kg,
                            duration
                        )
                        enriched_parts.append(f"  → {duration} min burns ~{calories_burned} calories")
        
        return "\n".join(enriched_parts)
    
    def _query_suitable_exercises(self) -> List[Dict]:
        """Query exercise database for exercises suitable for the user."""
        if not self.exercise_rag or not self.user_profile:
            return []
        
        try:
            # Determine query based on context
            query_text = "cardio exercises"  # Default
            
            # Use weighted preferences
            if self.user_profile.exercise_preferences:
                top_pref = self.user_profile.get_top_preferences(1)
                if top_pref:
                    preferred_type = top_pref[0][0]
                    # 70% chance to query preferred category
                    if random.random() < 0.7:
                        query_text = f"{preferred_type} exercises"
            
            # Query with filters
            results = self.exercise_rag.query_exercises(
                query_text=query_text,
                top_k=10,
                equipment=self.user_profile.available_equipment,
                exclude_contraindications=self.user_profile.health_limitations
            )
            
            return results
        except Exception as e:
            logger.error(f"Exercise query failed: {e}")
            return []
    
    def _handle_goal_setting(self, task: str) -> str:
        """Handle goal setting requests."""
        if not self.user_profile:
            return "I need your user profile to set fitness goals. Please complete your profile setup first."
        
        # Use LLM to parse goal details from task
        prompt = f"""Based on this user request, extract goal details:
"{task}"

User info: {self.user_profile.age} years old, {self.user_profile.weight_kg}kg, {self.user_profile.fitness_level} level

Provide goal details in this format:
Type: [weight_loss/muscle_gain/endurance/consistency]
Description: [specific goal]
Target: [numeric value]
Unit: [kg/km/days/etc]
Deadline: [weeks from now]

Keep it realistic and achievable."""
        
        # Get LLM response
        goal_details = super().execute(prompt, None)
        
        # For MVP, create a sample goal (in production, parse LLM response)
        new_goal = FitnessGoal(
            goal_id=str(uuid.uuid4()),
            goal_type="weight_loss",  # Would parse from LLM response
            description=f"Fitness goal: {task[:50]}",
            target_value=5.0,  # Would parse from LLM response
            unit="kg",
            deadline=datetime.now() + timedelta(weeks=8)
        )
        
        self.user_profile.add_goal(new_goal)
        save_user_profile(self.user_profile)
        
        return f"""✓ Goal Created!

{new_goal.description}
Target: {new_goal.target_value} {new_goal.unit}
Deadline: {new_goal.deadline.strftime('%B %d, %Y')}
Days Remaining: {new_goal.days_remaining}

I'll help you track your progress. Keep logging your activities and I'll tailor my recommendations to help you achieve this goal!"""
    
    def _handle_goal_progress(self) -> str:
        """Handle goal progress check requests."""
        if not self.user_profile:
            return "No user profile found. Please complete profile setup first."
        
        active_goals = self.user_profile.active_goals
        
        if not active_goals:
            return "You don't have any active fitness goals. Would you like to set one?"
        
        progress_report = ["**Your Fitness Goals Progress:**\n"]
        
        for goal in active_goals:
            status_emoji = "🟢" if goal.is_on_track else "🟡"
            progress_report.append(f"{status_emoji} **{goal.description}**")
            progress_report.append(f"  Progress: {goal.current_value}/{goal.target_value} {goal.unit} ({goal.progress_percent:.1f}%)")
            progress_report.append(f"  Days Remaining: {goal.days_remaining}")
            progress_report.append(f"  Status: {'On track!' if goal.is_on_track else 'Need to pick up the pace'}")
            progress_report.append("")
        
        return "\n".join(progress_report)
    
    def _handle_exercise_completion(self, task: str) -> str:
        """Handle exercise completion tracking."""
        if not self.user_profile:
            return "Exercise logged! (Note: Profile not loaded for preference tracking)"
        
        # Extract exercise name from task (simple heuristic)
        # In production, use better NLP parsing
        task_lower = task.lower()
        
        # Common exercise keywords
        exercises = ["walk", "run", "swim", "cycle", "yoga", "pilates", "gym", "lift", "cardio"]
        
        tracked_exercise = None
        for exercise in exercises:
            if exercise in task_lower:
                tracked_exercise = exercise
                break
        
        if tracked_exercise:
            self.user_profile.increment_exercise_preference(tracked_exercise)
            save_user_profile(self.user_profile)
            
            count = self.user_profile.exercise_preferences.get(tracked_exercise.lower(), 0)
            
            return f"""✓ Excellent work! I've tracked your {tracked_exercise} session.

This is session #{count} for {tracked_exercise}. I'll remember that you enjoy this activity and suggest it more often in the future.

Keep up the great work! 💪"""
        
        return "Great job completing your exercise! Keep up the momentum. 💪"


if __name__ == "__main__":
    # Test the enhanced fitness agent
    logging.basicConfig(level=logging.INFO)
    
    agent = FitnessAgent()
    
    # Test with sample context
    test_context = [
        {
            "type": "nutrition_data",
            "content": {
                "total_calories": 850,
                "macros": {"protein": 35, "carbs": 90, "fat": 28}
            }
        }
    ]
    
    response = agent.execute("I just ate a burger and fries. What exercise should I do?", test_context)
    print(response)
