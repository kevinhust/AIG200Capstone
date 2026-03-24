from typing import Optional, List, Dict, Any
import logging
import json
import re
from functools import lru_cache
from src.agents.base_agent import BaseAgent
from src.data_rag.simple_rag_tool import SimpleRagTool

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

        super().__init__(
            role="fitness",
            system_prompt=base_prompt,
            use_openai_api=False
        )
        self.rag = SimpleRagTool()

    @property
    def db(self):
        """Lazy-load ProfileDB to avoid circular import issues."""
        if self._db is None:
            from src.discord_bot.profile_db import get_profile_db
            self._db = get_profile_db()
        return self._db

    def _load_user_context(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Load user profile from Supabase with in-memory caching.

        Args:
            discord_user_id: Discord user ID (as string)

        Returns:
            Standardized user profile dict
        """
        # Check cache first (valid for single session)
        if discord_user_id in self._profile_cache:
            logger.debug(f"[FitnessAgent] Cache hit for user {discord_user_id}")
            return self._profile_cache[discord_user_id]

        try:
            profile = self.db.get_profile(discord_user_id)

            if profile:
                # Parse restrictions field
                restrictions_str = profile.get("restrictions", "") or ""
                health_conditions = [
                    r.strip() for r in restrictions_str.split(",")
                    if r.strip() and r.strip().lower() != "none"
                ]

                user_context = {
                    "discord_user_id": discord_user_id,
                    "name": profile.get("full_name", "User"),
                    "age": profile.get("age", 30),
                    "weight_kg": profile.get("weight_kg", 70),
                    "height_cm": profile.get("height_cm", 170),
                    "gender": profile.get("gender", "Male"),
                    "goal": profile.get("goal", "Maintain"),
                    "activity_level": profile.get("activity", "Sedentary"),
                    "health_conditions": health_conditions,
                }

                logger.info(f"[FitnessAgent] Loaded profile for {discord_user_id}: {user_context.get('name')}, conditions={health_conditions}")
            else:
                # Fallback to default profile
                user_context = {**DEFAULT_USER_PROFILE, "discord_user_id": discord_user_id}
                logger.warning(f"[FitnessAgent] No profile found for {discord_user_id}, using defaults")

            # Cache for session
            self._profile_cache[discord_user_id] = user_context
            return user_context

        except Exception as e:
            logger.error(f"[FitnessAgent] Failed to load profile for {discord_user_id}: {e}")
            return {**DEFAULT_USER_PROFILE, "discord_user_id": discord_user_id}

    def _extract_discord_id(self, context: Optional[List[Dict]], task: str) -> str:
        """
        Extract discord_user_id from context or task.

        Priority:
        1. Context with explicit discord_user_id
        2. Context with user_context containing user_id
        3. Fallback to "default_user"

        Args:
            context: Agent context list
            task: Task string (for fallback extraction)

        Returns:
            Discord user ID as string
        """
        if context:
            for msg in context:
                # Direct discord_user_id field
                if msg.get("discord_user_id"):
                    return str(msg["discord_user_id"])

                # user_context JSON blob
                if msg.get("type") == "user_context":
                    try:
                        content = msg.get("content", "{}")
                        if isinstance(content, str):
                            data = json.loads(content)
                        else:
                            data = content

                        # Check multiple possible field names
                        for key in ["user_id", "discord_user_id", "id"]:
                            if data.get(key):
                                return str(data[key])
                    except Exception:
                        pass

        logger.warning("[FitnessAgent] No discord_user_id found in context, using default_user")
        return "default_user"

    def _get_today_stats(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Get today's nutrition stats from Supabase.

        Args:
            discord_user_id: Discord user ID

        Returns:
            Dict with calories_in, protein_g, etc.
        """
        try:
            stats = self.db.get_today_stats(discord_user_id)
            return stats
        except Exception as e:
            logger.warning(f"[FitnessAgent] Failed to get today stats: {e}")
            return {"total_calories": 0, "total_protein": 0}

    def _get_daily_aggregation(self, discord_user_id: str) -> Dict[str, Any]:
        """
        Get daily aggregation including calories in/out.

        Args:
            discord_user_id: Discord user ID

        Returns:
            Dict with calories_in, calories_out, net_calories
        """
        try:
            from datetime import date
            agg = self.db.get_daily_aggregation(discord_user_id, date.today())
            return agg
        except Exception as e:
            logger.warning(f"[FitnessAgent] Failed to get daily aggregation: {e}")
            return {"calories_in": 0, "calories_out": 0, "net_calories": 0}

    def _get_user_habits(self, discord_user_id: str, days: int = 14) -> Dict[str, Any]:
        """
        Extract user workout preferences from historical data (v6.3 Preference Learning).

        Analyzes the past N days of workout logs to identify:
        - Top activities by frequency
        - Intensity preferences (low/moderate/high based on duration and calories)
        - Recent trends (last 3 days vs overall)

        Args:
            discord_user_id: Discord user ID
            days: Number of days to analyze (default 14)

        Returns:
            Dict with preference insights:
            {
                "top_activities": ["Yoga", "Walking", "Stretching"],
                "avg_duration_min": 25,
                "avg_intensity": "moderate",  # "low", "moderate", "high"
                "total_workouts": 12,
                "preferred_times": ["morning", "evening"],  # Based on timestamps
                "recent_trend": "increasing",  # "increasing", "stable", "decreasing"
            }
        """
        from collections import Counter
        from datetime import datetime, timedelta

        try:
            # Fetch workout logs from ProfileDB
            logs = self.db.get_workout_logs(discord_user_id, days=days)

            if not logs:
                logger.info(f"[FitnessAgent] No workout history found for user {discord_user_id}")
                return {
                    "top_activities": [],
                    "avg_duration_min": 0,
                    "avg_intensity": "unknown",
                    "total_workouts": 0,
                    "preferred_times": [],
                    "recent_trend": "unknown"
                }

            # 1. Count activity frequency
            activity_names = [log.get("exercise_name", "Unknown") for log in logs if log.get("exercise_name")]
            activity_counter = Counter(activity_names)
            top_activities = [item[0] for item in activity_counter.most_common(3)]

            # 2. Calculate average duration
            durations = [log.get("duration_min", 0) for log in logs if log.get("duration_min")]
            avg_duration = sum(durations) / len(durations) if durations else 0

            # 3. Determine intensity preference based on kcal/duration ratio
            kcal_values = [log.get("kcal_estimate", 0) for log in logs if log.get("kcal_estimate")]
            avg_kcal = sum(kcal_values) / len(kcal_values) if kcal_values else 0

            # Intensity classification (kcal per 30 min session)
            kcal_rate = (avg_kcal / avg_duration * 30) if avg_duration > 0 else 0
            if kcal_rate >= 200:
                avg_intensity = "high"
            elif kcal_rate >= 100:
                avg_intensity = "moderate"
            else:
                avg_intensity = "low"

            # 4. Analyze time preferences (based on created_at timestamps)
            time_counts = {"morning": 0, "afternoon": 0, "evening": 0}
            for log in logs:
                created_at = log.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            dt = created_at
                        hour = dt.hour
                        if 6 <= hour < 12:
                            time_counts["morning"] += 1
                        elif 12 <= hour < 18:
                            time_counts["afternoon"] += 1
                        else:
                            time_counts["evening"] += 1
                    except Exception:
                        pass

            preferred_times = [t for t, c in sorted(time_counts.items(), key=lambda x: x[1], reverse=True) if c > 0]

            # 5. Detect recent trend (last 3 days vs previous period)
            now = datetime.now()
            recent_cutoff = now - timedelta(days=3)

            recent_count = 0
            older_count = 0
            for log in logs:
                created_at = log.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            dt = created_at
                        if dt >= recent_cutoff:
                            recent_count += 1
                        else:
                            older_count += 1
                    except Exception:
                        pass

            if recent_count > older_count * 0.5:  # More than 50% in last 3 days
                recent_trend = "increasing"
            elif recent_count < older_count * 0.25:  # Less than 25% in last 3 days
                recent_trend = "decreasing"
            else:
                recent_trend = "stable"

            habits = {
                "top_activities": top_activities,
                "avg_duration_min": round(avg_duration, 1),
                "avg_intensity": avg_intensity,
                "total_workouts": len(logs),
                "preferred_times": preferred_times[:2],  # Top 2 time slots
                "recent_trend": recent_trend,
            }

            logger.info(f"[FitnessAgent] User habits extracted: {habits}")
            return habits

        except Exception as e:
            logger.error(f"[FitnessAgent] Failed to extract user habits: {e}")
            return {
                "top_activities": [],
                "avg_duration_min": 0,
                "avg_intensity": "unknown",
                "total_workouts": 0,
                "preferred_times": [],
                "recent_trend": "unknown"
            }

    def _build_empathy_strategy(
        self,
        user_habits: Dict[str, Any],
        budget_progress: Dict[str, Any],
        visual_warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Build empathy strategy for preference-safety conflict resolution (v6.3).

        This method detects conflicts between user preferences and current constraints,
        then generates appropriate empathy messaging for the LLM prompt.

        Conflict Matrix:
        | Scenario | Signal | Action | Empathy Strategy |
        |----------|--------|--------|------------------|
        | Preference vs Safety | HIIT habit + fried food | Block HIIT | Acknowledge habit, pivot for safety |
        | Preference vs Budget | Long runs + low energy | Downgrade intensity | Celebrate habit, suggest alternative |
        | Habit vs Goal | Sedentary + fat loss goal | Guide increase frequency | Gentle encouragement |

        Args:
            user_habits: Extracted preferences from workout history
            budget_progress: Current calorie budget status
            visual_warnings: Health memo warnings (e.g., fried, high_sugar)

        Returns:
            Dict with:
            - conflict_type: "preference_vs_safety" | "preference_vs_budget" | "habit_vs_goal" | None
            - empathy_message: Human-readable empathy string for LLM prompt
            - suggested_pivot: Alternative exercise suggestion
            - intensity_modifier: "reduce" | "maintain" | "increase"
        """
        conflict_type = None
        empathy_message = ""
        suggested_pivot = None
        intensity_modifier = "maintain"

        top_activities = user_habits.get("top_activities", [])
        avg_intensity = user_habits.get("avg_intensity", "unknown")
        budget_status = budget_progress.get("status", "good")
        remaining_pct = budget_progress.get("remaining_pct", 100)

        # ============================================
        # Conflict 1: Preference vs Safety
        # User likes high-intensity but has visual warnings (fried/oily food)
        # ============================================
        high_intensity_activities = ["hiit", "sprint", "burpee", "jump squat", "plyometric"]
        user_likes_high_intensity = any(
            act.lower() in high_intensity_activities
            for act in top_activities
        )

        if visual_warnings and user_likes_high_intensity:
            conflict_type = "preference_vs_safety"
            intensity_modifier = "reduce"

            # Build specific empathy message
            liked_activity = next(
                (act for act in top_activities if act.lower() in high_intensity_activities),
                "high-intensity exercise"
            )
            warning_reason = self._get_warning_reason(visual_warnings)

            empathy_message = (
                f"I know you've been crushing your **{liked_activity}** goals lately! ⚡ "
                f"However, since you've consumed {warning_reason}, "
                f"let's protect your digestion by switching to **low-impact alternatives** today. "
                f"Your streak stays alive, just with a gentler pace."
            )
            suggested_pivot = "Walking, Yoga, or Light Stretching"

            logger.info(f"[EmpathyStrategy] Preference vs Safety: {liked_activity} blocked due to {visual_warnings}")

        # ============================================
        # Conflict 2: Preference vs Budget
        # User likes long workouts but has critical/warning budget
        # ============================================
        elif budget_status in ["critical", "warning"] and remaining_pct < 40:
            # Check if user prefers endurance/long activities
            endurance_activities = ["running", "jogging", "cycling", "swimming", "long walk"]
            user_likes_endurance = any(
                act.lower() in endurance_activities
                for act in top_activities
            )

            if user_likes_endurance:
                conflict_type = "preference_vs_budget"
                intensity_modifier = "reduce"

                liked_activity = next(
                    (act for act in top_activities if act.lower() in endurance_activities),
                    "endurance training"
                )

                empathy_message = (
                    f"Your **{liked_activity}** dedication is inspiring! 🏃 "
                    f"However, with only **{remaining_pct:.0f}%** of your calorie budget remaining, "
                    f"a full session might be too taxing today. "
                    f"Let's try a **shorter, moderate session** to keep your momentum without overstraining."
                )
                suggested_pivot = "15-min brisk walk or Light Yoga"

                logger.info(f"[EmpathyStrategy] Preference vs Budget: {liked_activity} adjusted due to {remaining_pct:.1f}% budget")

        # ============================================
        # Conflict 3: Habit vs Goal
        # User is sedentary but has active weight loss goal
        # ============================================
        elif user_habits.get("total_workouts", 0) < 3 and remaining_pct > 60:
            # Check if user has weight loss goal
            user_goal = user_habits.get("goal", "").lower() if "goal" in user_habits else ""
            # Get from profile instead
            # For now, use a heuristic based on low activity

            if avg_intensity in ["low", "unknown"]:
                conflict_type = "habit_vs_goal"
                intensity_modifier = "increase"

                empathy_message = (
                    f"I notice you're building your fitness foundation! 🌱 "
                    f"Since you have plenty of energy budget today (**{remaining_pct:.0f}% remaining**), "
                    f"this is a perfect opportunity to try a **gentle 10-minute activity**. "
                    f"Small steps lead to big transformations!"
                )
                suggested_pivot = "10-min Walk, Light Stretching, or Desk Exercises"

                logger.info(f"[EmpathyStrategy] Habit vs Goal: Encouraging sedentary user with {remaining_pct:.1f}% budget")

        # No conflict - maintain normal flow
        if not conflict_type:
            empathy_message = ""
            suggested_pivot = None
            intensity_modifier = "maintain"

        return {
            "conflict_type": conflict_type,
            "empathy_message": empathy_message,
            "suggested_pivot": suggested_pivot,
            "intensity_modifier": intensity_modifier
        }

    def _get_warning_reason(self, visual_warnings: List[str]) -> str:
        """Convert visual warning codes to human-readable reason."""
        warning_reasons = {
            "fried": "fried food",
            "high_oil": "high-oil food",
            "high_sugar": "high-sugar food",
            "processed": "processed food"
        }

        reasons = []
        for warning in visual_warnings:
            warning_lower = warning.lower()
            if warning_lower in warning_reasons:
                reasons.append(warning_reasons[warning_lower])

        if not reasons:
            return "heavy food"

        if len(reasons) == 1:
            return reasons[0]
        elif len(reasons) == 2:
            return f"{reasons[0]} and {reasons[1]}"
        else:
            return ", ".join(reasons[:-1]) + f", and {reasons[-1]}"

    def _generate_budget_progress(
        self,
        daily_agg: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a visual budget progress summary for UI display.

        Args:
            daily_agg: Daily aggregation data from Supabase
            user_profile: User profile with TDEE and macro goals

        Returns:
            Dict with progress bars, remaining budget, and recommendations
        """
        # Calculate TDEE from profile
        tdee = self._calculate_bmr(user_profile)

        # Get consumed values from aggregation
        calories_in = daily_agg.get("calories_in", 0)
        calories_out = daily_agg.get("calories_out", 0)
        net_calories = daily_agg.get("net_calories", 0)

        # Calculate remaining budget
        remaining = tdee - calories_in + calories_out

        # Macro targets (default: 30% P, 40% C, 30% F of TDEE)
        protein_target = user_profile.get("protein_goal", (tdee * 0.3) / 4)  # 30% of        carb_target = user_profile.get("carb_goal", (tdee * 0.4) / 4)  # 40%
        fat_target = user_profile.get("fat_goal", (tdee * 0.3) / 9)  # 30%

        # Get consumed macros (from today's meals)
        protein_in = daily_agg.get("protein_g", 0)
        # Note: carbs and fat not tracked in daily_agg yet

        carbs_in = 0
        fat_in = 0

        # Calculate DV% for each macro
        protein_pct = min(100, (protein_in / protein_target * 100)) if protein_target > 0 else 0
        calories_pct = min(100, (calories_in / tdee * 100))
        remaining_pct = max(0, (remaining / tdee * 100))

        # Generate progress bars
        calorie_bar = self._create_progress_bar(calories_pct, remaining_pct)
        protein_bar = self._create_progress_bar(protein_pct, None)

        # Determine overall status
        if remaining_pct < 20:
            status = "critical"  # Very low calories remaining
            status_emoji = "🔴"
        elif remaining_pct < 40:
            status = "warning"
            status_emoji = "🟡"
        else:
            status = "good"
            status_emoji = "🟢"

        # Generate recommendations based on budget
        recommendations = []
        if status == "critical":
            recommendations.append("⚠️ Very low calorie budget! Consider light activities only.")
        elif status == "warning":
            recommendations.append("⚡ Moderate intensity recommended - you budget is getting tight.")
        else:
            recommendations.append("✅ Good budget for moderate exercise.")

        if protein_pct < 50:
            recommendations.append("🥩 Protein intake is low - consider high-protein recovery meal.")

        return {
            "tdee": round(tdee),
            "calories_in": round(calories_in),
            "calories_out": round(calories_out),
            "remaining": round(remaining),
            "remaining_pct": round(remaining_pct, 1),
            "calorie_bar": calorie_bar,
            "protein_bar": protein_bar,
            "status": status,
            "status_emoji": status_emoji,
            "recommendations": recommendations,
        }

    def _create_progress_bar(
        self,
        percentage: float,
        remaining_pct: Optional[float] = None
    ) -> str:
        """
        Create a visual progress bar string.

        Args:
            percentage: Current percentage (0-100)
            remaining_pct: Remaining percentage (optional, for dual-color display)

        Returns:
            Progress bar string like "🟢 [▰▰▰▰▰▱▱▱▱▱] 50%"
        """
        filled = int(percentage / 10)
        empty = 10 - filled

        bar = "▰" * filled + "▱" * empty

        # Color coding based on percentage
        if percentage >= 100:
            color = "🔴"  # Over budget
        elif percentage >= 80:
            color = "🟡"  # Warning zone
        else:
            color = "🟢"  # Good

        # Remaining indicator (for calories)
        if remaining_pct is not None:
            if remaining_pct < 20:
                remaining_color = "🔴"
            elif remaining_pct < 40:
                remaining_color = "🟡"
            else:
                remaining_color = "🟢"

            return f"{color} [{bar}] {percentage:.0f}% {remaining_color}"

        return f"{color} [{bar}] {percentage:.0f}%"

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

        v6.1 Upgrade: Now loads real user profile from Supabase.
        """
        logger.info("[FitnessAgent] Executing async task: %s", task[:100] + "...")

        # 1. Extract discord_user_id and load real profile from Supabase
        discord_user_id = self._extract_discord_id(context, task)
        user_profile = self._load_user_context(discord_user_id)
        health_conditions = user_profile.get("health_conditions", [])

        # 2. Extract visual warnings
        visual_warnings = self._extract_visual_warnings_from_task(task)

        # 3. Get today's real-time stats from Supabase
        today_stats = self._get_today_stats(discord_user_id)
        daily_agg = self._get_daily_aggregation(discord_user_id)

        # 4. Extract nutrition info from context (for HealthMemo handoff)
        nutrition_info = ""
        if context:
            for msg in context:
                if msg.get("from") == "nutrition" or msg.get("type") == "nutrition_summary":
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

        # 5.5. Generate budget progress visualization
        budget_progress = self._generate_budget_progress(daily_agg, user_profile)
        budget_context = f"""
BUDGET PROGRESS (v6.2):
{budget_progress['calorie_bar']}
- Remaining: {budget_progress['remaining']} kcal ({budget_progress['remaining_pct']:.1f}%)
- Status: {budget_progress['status_emoji']} {budget_progress['status'].upper()}
- Recommendation: {budget_progress['recommendations'][0] if budget_progress['recommendations'] else 'N/A'}
"""

        # 6. Build Prompt
        health_memo_section = ""
        if visual_warnings:
            health_memo_section = f"\nHEALTH MEMO ALERT: Warnings detected {visual_warnings}. Reduce intensity. Include BR-001 disclaimer.\n"

        dynamic_context = f"""
{health_memo_section}
USER PROFILE: BMI {bmi}, Calorie Maintenance {round(bmr)} kcal, Conditions: {health_conditions}.
CALORIE STATUS: {calorie_status}.
{budget_context}
RAG SAFE EXERCISES: {safe_ex_list}.
"""
        full_task = f"{task}\n\nCONTEXT:\n{dynamic_context}\n\nReturn EXACTLY a JSON object."
        
        # Call base agent's execute (which is synchronous but we can run it in a thread or just call it)
        # BaseAgent.execute usually calls the LLM.
        import asyncio
        result_str = await asyncio.to_thread(super().execute, full_task, context)
        
        # 7. Post-process and inject images into JSON recommendations if missing
        if not result_str:
            logger.warning("[FitnessAgent] LLM returned empty response. Using fallback.")
            result_str = "{}"

        try:
            clean_str = result_str.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[-1].split("```")[0].strip()

            if not clean_str:
                raise ValueError("Empty response after cleaning")

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

            # Inject budget progress into response (v6.2)
            result_json["budget_progress"] = budget_progress

            return json.dumps(result_json)
            
        except Exception as e:
            logger.error(f"[FitnessAgent] Async post-process failed: {e}")
            # Try to return something usable even if not perfect JSON
            if result_str and len(result_str) > 10:
                return result_str
            return json.dumps({"summary": "Error processing fitness advice.", "recommendations": []})

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute fitness advice task and return structured JSON.

        Module 3: Now includes dynamic risk filtering based on Health Memo.
        v6.1 Upgrade: Now loads real user profile from Supabase.
        """
        logger.info("[FitnessAgent] Analyzing task: %s", task[:100] + "...")

        # 1. Extract discord_user_id and load real profile from Supabase
        discord_user_id = self._extract_discord_id(context, task)
        user_profile = self._load_user_context(discord_user_id)
        health_conditions = user_profile.get("health_conditions", [])

        # 2. Extract visual warnings from task (Health Memo)
        visual_warnings = self._extract_visual_warnings_from_task(task)
        if visual_warnings:
            logger.info(f"[FitnessAgent] Health Memo warnings detected: {visual_warnings}")

        # 3. Get today's stats and daily aggregation
        today_stats = self._get_today_stats(discord_user_id)
        daily_agg = self._get_daily_aggregation(discord_user_id)

        # 4. Extract nutrition info from context
        nutrition_info = ""
        if context:
            for msg in context:
                if msg.get("from") == "nutrition" or msg.get("type") == "nutrition_summary":
                    nutrition_info = msg.get("content", "")

        # 5. Get Safe Recommendations from RAG with dynamic risks
        # Note: empathy_strategy will be built later with budget_progress, so pass None for now
        rag_data = self.rag.get_safe_recommendations(
            task,
            health_conditions,
            dynamic_risks=visual_warnings
        )
        safe_ex_list = [f"{e['name']} (Reason: {e.get('description', '')})" for e in rag_data['safe_exercises']]
        warnings = rag_data.get('safety_warnings', [])
        dynamic_adjustments = rag_data.get('dynamic_adjustments')

        # 6. Dynamic Calculation
        bmr = self._calculate_bmr(user_profile)
        calorie_status = self._determine_calorie_status(bmr, nutrition_info)
        bmi = self._calculate_bmi(user_profile)
        nutrition_snippet = nutrition_info or ""
        if len(nutrition_snippet) > 1500:
            nutrition_snippet = nutrition_snippet[:1500] + "...(truncated)"

        # 6.5. Generate budget progress visualization (v6.2)
        budget_progress = self._generate_budget_progress(daily_agg, user_profile)

        # 6.6. Extract user habits for preference learning (v6.3)
        user_habits = self._get_user_habits(discord_user_id, days=14)

        # 6.7. Build empathy strategy for conflict resolution (v6.3)
        empathy_strategy = self._build_empathy_strategy(
            user_habits,
            budget_progress,
            visual_warnings
        )

        # 7. Build Dynamic Prompt Supplement with real-time data
        health_memo_section = ""
        if visual_warnings:
            health_memo_section = f"""
HEALTH MEMO ALERT:
- Visual warnings detected: {visual_warnings}
- User recently consumed food with health concerns
- MUST reduce exercise intensity accordingly
- MUST include BR-001 disclaimer in response
"""

        # Build preference context (v6.3)
        preference_context = ""
        if user_habits.get("top_activities"):
            top_acts = ", ".join(user_habits["top_activities"][:3])
            intensity = user_habits.get("avg_intensity", "unknown")
            trend = user_habits.get("recent_trend", "stable")
            total_workouts = user_habits.get("total_workouts", 0)

            preference_context = f"""
USER PREFERENCE CONTEXT (v6.3):
- Favorite Activities: {top_acts}
- Preferred Intensity: {intensity}
- Recent Trend: {trend} activity frequency
- Total Workouts (14d): {total_workouts}
- Instruction: Prioritize favorite activities if they pass safety/budget checks. If user prefers high-intensity but budget is critical, suggest alternatives with empathy.
"""

        # Build empathy context section (v6.3)
        empathy_context = ""
        if empathy_strategy.get("conflict_type"):
            empathy_msg = empathy_strategy.get("empathy_message", "")
            suggested_pivot = empathy_strategy.get("suggested_pivot", "")
            conflict = empathy_strategy.get("conflict_type", "")

            empathy_context = f"""
EMPATHY STRATEGY (v6.3):
- Conflict Detected: {conflict}
- Intensity Modifier: {empathy_strategy.get('intensity_modifier', 'maintain').upper()}
- Empathy Message: {empathy_msg}
- Suggested Pivot: {suggested_pivot}
- IMPORTANT: If there's a conflict, acknowledge the user's preference first, then explain the pivot with empathy. Be warm, not robotic.
"""

        # Include real-time daily stats + budget progress
        today_context = f"""
TODAY'S REAL-TIME DATA (from Supabase):
- Calories consumed today: {today_stats.get('total_calories', 0)} kcal
- Protein today: {today_stats.get('total_protein', 0)}g
- Daily net calories: {daily_agg.get('net_calories', 0)} kcal
- Active minutes today: {daily_agg.get('active_minutes', 0)} min

BUDGET PROGRESS (v6.2):
{budget_progress['calorie_bar']}
- Remaining: {budget_progress['remaining']} kcal ({budget_progress['remaining_pct']:.1f}%)
- Status: {budget_progress['status_emoji']} {budget_progress['status'].upper()}
- Tip: {budget_progress['recommendations'][0] if budget_progress['recommendations'] else 'N/A'}
"""

        dynamic_context = f"""
{health_memo_section}
{today_context}
{preference_context}
{empathy_context}
USER PROFILE: BMI {bmi}, Calorie Maintenance {round(bmr)} kcal, Conditions: {health_conditions}.
CALORIE STATUS: {calorie_status}.
RELEVANT NUTRITION DATA: {nutrition_snippet}
RAG SAFE EXERCISES: {safe_ex_list}.
RAG SAFETY WARNINGS: {warnings}.
DYNAMIC ADJUSTMENTS: {dynamic_adjustments}.
"""

        full_task = f"{task}\n\nCONTEXT:\n{dynamic_context}\n\nBased on this, return EXACTLY a JSON object with keys: summary, recommendations, safety_warnings, avoid, dynamic_adjustments."

        result_str = super().execute(full_task, context)

        # 8. Validation/Cleanup
        try:
            clean_str = result_str.strip()
            if "```json" in clean_str:
                clean_str = clean_str.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_str:
                clean_str = clean_str.split("```")[-1].split("```")[0].strip()

            # Verify valid JSON
            result_json = json.loads(clean_str)

            # 8.5. Inject budget progress into response (v6.2)
            result_json["budget_progress"] = budget_progress

            # 8.6. Inject empathy strategy and user habits into response (v6.3)
            result_json["empathy_strategy"] = empathy_strategy
            result_json["user_habits"] = user_habits

            # 9. Double-validation: Check recommendations against visual warnings
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
                "budget_progress": budget_progress,  # v6.2: Include even in fallback
            }
            if visual_warnings:
                fallback["safety_warnings"].append(BR001_DISCLAIMER)
                fallback["dynamic_adjustments"] = BR001_DISCLAIMER
            return json.dumps(fallback)
