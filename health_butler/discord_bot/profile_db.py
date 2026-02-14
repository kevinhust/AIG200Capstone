"""Supabase Profile Database Module for Health Butler.

Provides persistent storage for:
- User Profiles (profiles table)
- Daily Logs (daily_logs table)
- Chat Messages (chat_messages table)
"""

import os
import json
from typing import Dict, Any, Optional, List, Any as _Any
from datetime import date, datetime
try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore
    Client = _Any  # type: ignore
from dotenv import load_dotenv

load_dotenv()


class ProfileDB:
    """Supabase database client for user profile persistence."""

    def __init__(self):
        """Initialize Supabase client from environment variables."""
        if create_client is None:
            raise RuntimeError("supabase package is not installed")
        self.url: str = os.getenv("SUPABASE_URL", "")
        self.key: str = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            or os.getenv("SUPABASE_KEY", "")
        )

        if not self.url or not self.key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set in environment variables"
            )

        self.client: Client = create_client(self.url, self.key)

    def _is_missing_column_error(self, error: Exception, column_name: str) -> bool:
        """Return True when exception indicates a missing DB column."""
        return column_name.lower() in str(error).lower()

    # ============================================
    # Profile Operations
    # ============================================

    def get_profile(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by Discord user ID.

        Discord users are stored with their Discord ID as the profile UUID.
        For demo mode, we use Discord ID directly as the UUID.
        """
        # Note: In production, you'd have a discord_user_id column
        # For now, we'll query profiles directly (assuming auth.users.id = discord_user_id)
        response = self.client.table("profiles").select("*").eq("id", discord_user_id).execute()

        if response.data:
            return response.data[0]
        return None

    def create_profile(
        self,
        discord_user_id: str,
        full_name: str,
        age: int,
        gender: str,
        height_cm: float,
        weight_kg: float,
        goal: str,
        conditions: List[str],
        activity: str,
        diet: List[str],
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new user profile.

        Args:
            discord_user_id: Discord user ID (used as UUID)
            full_name: User's full name
            age: User's age
            gender: User's gender
            height_cm: Height in centimeters
            weight_kg: Weight in kilograms
            goal: Health goal (Lose Weight, Maintain, Gain Muscle)
            conditions: List of health conditions
            activity: Activity level
            diet: List of dietary preferences
            preferences: Additional personalization signals

        Returns:
            Created profile data
        """
        restrictions_str = ", ".join(conditions) if conditions and "None" not in conditions else None

        profile_data = {
            "id": discord_user_id,  # Using Discord ID as UUID for demo
            "full_name": full_name,
            "age": age,
            "gender": gender,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "goal": goal,
            "restrictions": restrictions_str,
            "activity": activity,
            "diet": ", ".join(diet) if diet else None,
            "preferences_json": preferences or {},
        }

        try:
            response = self.client.table("profiles").insert(profile_data).execute()
            return response.data[0] if response.data else None
        except Exception as exc:
            if "preferences_json" in profile_data and self._is_missing_column_error(exc, "preferences_json"):
                fallback_data = dict(profile_data)
                fallback_data.pop("preferences_json", None)
                response = self.client.table("profiles").insert(fallback_data).execute()
                return response.data[0] if response.data else None
            raise

    def update_profile(
        self,
        discord_user_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update user profile fields.

        Args:
            discord_user_id: Discord user ID
            **updates: Fields to update (full_name, age, weight_kg, etc.)

        Returns:
            Updated profile data
        """
        try:
            response = self.client.table("profiles").update(updates).eq("id", discord_user_id).execute()
            return response.data[0] if response.data else None
        except Exception as exc:
            if "preferences_json" in updates and self._is_missing_column_error(exc, "preferences_json"):
                fallback_updates = dict(updates)
                fallback_updates.pop("preferences_json", None)
                response = self.client.table("profiles").update(fallback_updates).eq("id", discord_user_id).execute()
                return response.data[0] if response.data else None
            raise

    # ============================================
    # Daily Logs Operations
    # ============================================

    def create_daily_log(
        self,
        discord_user_id: str,
        log_date: date,
        calories_intake: int = 0,
        protein_g: int = 0,
        steps_count: int = 0
    ) -> Dict[str, Any]:
        """Create or update a daily log entry."""
        log_data = {
            "user_id": discord_user_id,
            "date": log_date.isoformat(),
            "calories_intake": float(calories_intake),
            "protein_g": float(protein_g),
            "steps_count": int(steps_count),
        }

        response = self.client.table("daily_logs").upsert(log_data, on_conflict="user_id,date").execute()
        return response.data[0] if response.data else None

    def get_daily_logs(self, discord_user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent daily logs for a user."""
        response = self.client.table("daily_logs").select("*").eq("user_id", discord_user_id).order("date", desc=True).limit(days).execute()
        return response.data

    # ============================================
    # Chat Messages Operations
    # ============================================

    def save_message(self, discord_user_id: str, role: str, content: str) -> Dict[str, Any]:
        """Save a chat message."""
        message_data = {
            "user_id": discord_user_id,
            "role": role,
            "content": content
        }

        response = self.client.table("chat_messages").insert(message_data).execute()
        return response.data[0] if response.data else None

    # ============================================
    # Meal Operations
    # ============================================

    def create_meal(
        self,
        discord_user_id: str,
        dish_name: str,
        calories: int = 0,
        protein_g: int = 0,
        carbs_g: int = 0,
        fat_g: int = 0,
        confidence_score: float = 0.0
    ) -> Dict[str, Any]:
        """Create a meal record."""
        meal_data = {
            "user_id": discord_user_id,
            "dish_name": dish_name,
            "calories": float(calories),
            "protein_g": float(protein_g),
            "carbs_g": float(carbs_g),
            "fat_g": float(fat_g),
            "confidence_score": float(confidence_score),
        }
        
        response = self.client.table("meals").insert(meal_data).execute()
        return response.data[0] if response.data else None

    def get_meals(self, discord_user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent meals for a user."""
        response = self.client.table("meals").select("*").eq("user_id", discord_user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data

    def get_today_stats(self, discord_user_id: str) -> Dict[str, Any]:
        """Aggregate calories and meal count for the current day."""
        # Get UTC today start
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        response = self.client.table("meals").select("calories", "protein_g", "carbs_g", "fat_g")\
            .eq("user_id", discord_user_id)\
            .gte("created_at", today_start)\
            .execute()
        
        meals = response.data
        stats = {
            "meal_count": len(meals),
            "total_calories": sum(m.get("calories", 0) for m in meals if m.get("calories")),
            "total_protein": sum(m.get("protein_g", 0) for m in meals if m.get("protein_g")),
            "total_carbs": sum(m.get("carbs_g", 0) for m in meals if m.get("carbs_g")),
            "total_fat": sum(m.get("fat_g", 0) for m in meals if m.get("fat_g"))
        }
        return stats

    def update_meal(self, meal_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a meal record by primary key `id`.

        Note: Schema is expected to include `meals.id`. If not present, this will fail.
        """
        response = self.client.table("meals").update(updates).eq("id", meal_id).execute()
        return response.data[0] if response.data else None

    def delete_meal(self, meal_id: str) -> bool:
        """Delete a meal record by primary key `id`."""
        response = self.client.table("meals").delete().eq("id", meal_id).execute()
        # Supabase returns deleted rows in `data` for delete. Treat any successful execute as True.
        return response is not None

    def recompute_daily_log_from_meals(self, discord_user_id: str, log_date: date) -> Optional[Dict[str, Any]]:
        """Recompute a day's totals from `meals` and upsert into `daily_logs`.

        This keeps `daily_logs` consistent when meals are added/edited/deleted.
        """
        start = datetime.combine(log_date, datetime.min.time()).isoformat()
        end = datetime.combine(log_date, datetime.max.time()).isoformat()

        response = (
            self.client.table("meals")
            .select("calories,protein_g,carbs_g,fat_g,created_at")
            .eq("user_id", discord_user_id)
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        )
        meals = response.data or []
        total_calories = sum(float(m.get("calories", 0) or 0) for m in meals)
        total_protein = sum(float(m.get("protein_g", 0) or 0) for m in meals)

        return self.create_daily_log(
            discord_user_id=discord_user_id,
            log_date=log_date,
            calories_intake=total_calories,
            protein_g=total_protein,
        )

    def get_chat_history(self, discord_user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chat messages for a user."""
        response = self.client.table("chat_messages").select("*").eq("user_id", discord_user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data

    # ============================================
    # Workout Tracking Operations
    # ============================================

    def log_workout_event(
        self,
        discord_user_id: str,
        exercise_name: str,
        duration_min: int,
        kcal_estimate: float,
        status: str = "recommended",
        source: str = "fitness_agent",
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Persist workout recommendation/completion.

        Tries `workout_logs` table first; falls back to `chat_messages` JSON log
        so tracking still works even if the optional table is not provisioned yet.
        """
        event = {
            "user_id": discord_user_id,
            "exercise_name": exercise_name,
            "duration_min": int(duration_min),
            "kcal_estimate": float(kcal_estimate),
            "status": status,
            "source": source,
            "metadata": raw_payload or {},
        }

        try:
            response = self.client.table("workout_logs").insert(event).execute()
            return response.data[0] if response.data else None
        except Exception:
            # Graceful fallback without breaking bot UX
            payload = json.dumps(event)
            return self.save_message(discord_user_id, role="workout_log", content=payload)

    def add_routine_exercise(
        self,
        discord_user_id: str,
        exercise_name: str,
        target_per_week: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Add an exercise to the user's routine.

        Tries `workout_routines` table first; falls back to `chat_messages`.
        If an active routine entry already exists for this exercise, updates it
        instead of creating duplicates.
        """
        normalized_exercise_name = str(exercise_name or "Exercise").strip()
        routine_item = {
            "user_id": discord_user_id,
            "exercise_name": normalized_exercise_name,
            "target_per_week": int(target_per_week),
            "status": "active",
            "metadata": metadata or {},
        }

        try:
            existing = self.client.table("workout_routines")\
                .select("id")\
                .eq("user_id", discord_user_id)\
                .eq("exercise_name", normalized_exercise_name)\
                .eq("status", "active")\
                .limit(1)\
                .execute()

            existing_rows = existing.data or []
            if existing_rows:
                response = self.client.table("workout_routines")\
                    .update({
                        "target_per_week": int(target_per_week),
                        "metadata": metadata or {},
                        "updated_at": datetime.now().isoformat(),
                    })\
                    .eq("id", existing_rows[0]["id"])\
                    .execute()
                return response.data[0] if response.data else None

            response = self.client.table("workout_routines").insert(routine_item).execute()
            return response.data[0] if response.data else None
        except Exception:
            payload = json.dumps(routine_item)
            return self.save_message(discord_user_id, role="routine_log", content=payload)

    def get_workout_progress(self, discord_user_id: str, days: int = 7) -> Dict[str, Any]:
        """Return recent workout progress summary for UI display."""
        start_ts = datetime.now().timestamp() - (days * 24 * 60 * 60)

        completed_count = 0
        recommended_count = 0
        total_minutes = 0
        total_kcal = 0.0
        routine_count = 0
        recent_recommendations: List[str] = []
        routine_exercises: List[str] = []

        try:
            response = self.client.table("workout_logs")\
                .select("status, duration_min, kcal_estimate, exercise_name, created_at")\
                .eq("user_id", discord_user_id)\
                .gte("created_at", datetime.fromtimestamp(start_ts).isoformat())\
                .order("created_at", desc=True)\
                .execute()

            logs = response.data or []
            for row in logs:
                if row.get("status") == "recommended":
                    recommended_count += 1
                    exercise_name = str(row.get("exercise_name") or "").strip()
                    if exercise_name and exercise_name not in recent_recommendations and len(recent_recommendations) < 3:
                        recent_recommendations.append(exercise_name)

                if row.get("status") == "completed":
                    completed_count += 1
                    total_minutes += int(row.get("duration_min") or 0)
                    total_kcal += float(row.get("kcal_estimate") or 0)

            routine_response = self.client.table("workout_routines")\
                .select("id, exercise_name")\
                .eq("user_id", discord_user_id)\
                .eq("status", "active")\
                .order("created_at", desc=True)\
                .execute()
            routine_rows = routine_response.data or []
            routine_count = len(routine_rows)
            for row in routine_rows:
                exercise_name = str(row.get("exercise_name") or "").strip()
                if exercise_name and len(routine_exercises) < 5:
                    routine_exercises.append(exercise_name)

            return {
                "completed_count": completed_count,
                "recommended_count": recommended_count,
                "total_minutes": total_minutes,
                "total_kcal": total_kcal,
                "routine_count": routine_count,
                "recent_recommendations": recent_recommendations,
                "routine_exercises": routine_exercises,
            }
        except Exception:
            # Fallback using chat_messages log payloads
            history = self.get_chat_history(discord_user_id, limit=200)
            for msg in history:
                role = msg.get("role", "")
                try:
                    payload = json.loads(msg.get("content", "{}"))
                except Exception:
                    continue

                created_at = msg.get("created_at")
                if created_at:
                    try:
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                        if ts < start_ts:
                            continue
                    except Exception:
                        pass

                if role == "workout_log":
                    if payload.get("status") == "recommended":
                        recommended_count += 1
                        exercise_name = str(payload.get("exercise_name") or "").strip()
                        if exercise_name and exercise_name not in recent_recommendations and len(recent_recommendations) < 3:
                            recent_recommendations.append(exercise_name)
                    if payload.get("status") == "completed":
                        completed_count += 1
                        total_minutes += int(payload.get("duration_min") or 0)
                        total_kcal += float(payload.get("kcal_estimate") or 0)
                if role == "routine_log" and payload.get("status") == "active":
                    routine_count += 1
                    exercise_name = str(payload.get("exercise_name") or "").strip()
                    if exercise_name and exercise_name not in routine_exercises and len(routine_exercises) < 5:
                        routine_exercises.append(exercise_name)

            return {
                "completed_count": completed_count,
                "recommended_count": recommended_count,
                "total_minutes": total_minutes,
                "total_kcal": total_kcal,
                "routine_count": routine_count,
                "recent_recommendations": recent_recommendations,
                "routine_exercises": routine_exercises,
            }


# Singleton instance for app-wide use
_db_instance: Optional[ProfileDB] = None


def get_profile_db() -> ProfileDB:
    """Get or create singleton ProfileDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProfileDB()
    return _db_instance
