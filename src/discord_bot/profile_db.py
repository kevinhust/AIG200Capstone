"""Supabase Profile Database Module for Health Butler.

Provides persistent storage for:
- User Profiles (profiles table)
- Daily Logs (daily_logs table)
- Chat Messages (chat_messages table)
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Any as _Any
from datetime import date, datetime, timedelta
try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore
    Client = _Any  # type: ignore
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


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

    def delete_profile(self, discord_user_id: str) -> bool:
        """Delete user profile from database.
        
        Args:
            discord_user_id: Discord user ID
            
        Returns:
            True if successful
        """
        try:
            response = self.client.table("profiles").delete().eq("id", discord_user_id).execute()
            return True
        except Exception as exc:
            print(f"DEBUG: Failed to delete profile for {discord_user_id}: {exc}")
            return False

    # ============================================
    # Multiplayer: Weekly Split + Privacy
    # ============================================

    def update_weekly_split(
        self,
        discord_user_id: str,
        weekly_split: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update `profiles.weekly_split` for matchmaking."""
        response = (
            self.client.table("profiles")
            .update({"weekly_split": weekly_split})
            .eq("id", discord_user_id)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_matchmaking_candidates(
        self,
        *,
        muscle_groups: List[str],
        day: str,
        exclude_user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return candidate profiles whose split overlaps `muscle_groups` on `day`.

        This is implemented as a simple Python-side filter for compatibility with
        multiple Supabase/PostgREST versions. You can later replace this with a
        server-side SQL function for efficient JSONB overlap queries.
        """
        day_key = (day or "").strip().lower()
        wanted = {str(m or "").strip().lower() for m in (muscle_groups or []) if str(m or "").strip()}

        response = self.client.table("profiles").select("id,full_name,weekly_split,privacy_level").execute()
        rows = response.data or []

        matches: list[dict[str, Any]] = []
        for row in rows:
            if str(row.get("id")) == str(exclude_user_id):
                continue

            privacy = str(row.get("privacy_level") or "friends").lower()
            if privacy == "private":
                continue

            split = row.get("weekly_split") or {}
            day_values = split.get(day_key) if isinstance(split, dict) else None
            if not isinstance(day_values, list):
                continue

            theirs = {str(x or "").strip().lower() for x in day_values if str(x or "").strip()}
            if wanted and theirs.intersection(wanted):
                matches.append(row)
                if len(matches) >= limit:
                    break

        return matches

    def update_privacy_level(self, discord_user_id: str, privacy_level: str) -> Optional[Dict[str, Any]]:
        """Update `profiles.privacy_level` ('public'|'friends'|'private')."""
        response = (
            self.client.table("profiles")
            .update({"privacy_level": privacy_level})
            .eq("id", discord_user_id)
            .execute()
        )
        return response.data[0] if response.data else None

    # ============================================
    # Multiplayer: Friend Connections
    # ============================================

    def send_friend_request(self, requester_id: str, addressee_id: str) -> Optional[Dict[str, Any]]:
        """Create a pending friend request from `requester_id` to `addressee_id`."""
        if str(requester_id) == str(addressee_id):
            raise ValueError("Cannot friend-request yourself")

        payload = {
            "requester_id": str(requester_id),
            "addressee_id": str(addressee_id),
            "status": "pending",
            "updated_at": datetime.utcnow().isoformat(),
        }
        response = self.client.table("friend_connections").insert(payload).execute()
        return response.data[0] if response.data else None

    def respond_to_friend_request(self, connection_id: str, *, accept: bool) -> Optional[Dict[str, Any]]:
        """Accept a friend request (or delete it if declined)."""
        if accept:
            response = (
                self.client.table("friend_connections")
                .update({"status": "accepted", "updated_at": datetime.utcnow().isoformat()})
                .eq("id", connection_id)
                .execute()
            )
            return response.data[0] if response.data else None

        # Decline: delete the pending request (non-blocking).
        self.client.table("friend_connections").delete().eq("id", connection_id).execute()
        return None

    def get_friends(self, discord_user_id: str) -> List[Dict[str, Any]]:
        """Return accepted friend connections for the user (both directions)."""
        uid = str(discord_user_id)
        a = (
            self.client.table("friend_connections")
            .select("*")
            .eq("requester_id", uid)
            .eq("status", "accepted")
            .execute()
        )
        b = (
            self.client.table("friend_connections")
            .select("*")
            .eq("addressee_id", uid)
            .eq("status", "accepted")
            .execute()
        )
        return (a.data or []) + (b.data or [])

    def get_pending_requests(self, discord_user_id: str) -> List[Dict[str, Any]]:
        """Return pending incoming friend requests for the user."""
        uid = str(discord_user_id)
        response = (
            self.client.table("friend_connections")
            .select("*")
            .eq("addressee_id", uid)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def can_view_profile(self, viewer_id: str, target_id: str) -> bool:
        """Enforce `profiles.privacy_level` using the friend graph."""
        if str(viewer_id) == str(target_id):
            return True

        target = self.get_profile(str(target_id)) or {}
        privacy = str(target.get("privacy_level") or "friends").lower()
        if privacy == "public":
            return True
        if privacy == "private":
            return False

        # friends-only: accepted connection in either direction
        uid = str(viewer_id)
        tid = str(target_id)
        a = (
            self.client.table("friend_connections")
            .select("id")
            .eq("requester_id", uid)
            .eq("addressee_id", tid)
            .eq("status", "accepted")
            .limit(1)
            .execute()
        )
        if a.data:
            return True
        b = (
            self.client.table("friend_connections")
            .select("id")
            .eq("requester_id", tid)
            .eq("addressee_id", uid)
            .eq("status", "accepted")
            .limit(1)
            .execute()
        )
        return bool(b.data)

    # ============================================
    # Multiplayer: Guild Settings
    # ============================================

    def get_guild_settings(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Fetch settings for a Discord guild/server."""
        response = (
            self.client.table("guild_settings")
            .select("*")
            .eq("guild_id", str(guild_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def upsert_guild_settings(self, guild_id: str, **settings: Any) -> Optional[Dict[str, Any]]:
        """Create or update guild settings (upsert on `guild_id`)."""
        payload: Dict[str, Any] = {"guild_id": str(guild_id), **settings, "updated_at": datetime.utcnow().isoformat()}
        response = self.client.table("guild_settings").upsert(payload, on_conflict="guild_id").execute()
        return response.data[0] if response.data else None

    # ============================================
    # Multiplayer: BYOK (Bring Your Own Key)
    # ============================================

    def _get_byok_passphrase(self) -> str:
        """Read the server-side encryption passphrase from env."""
        passphrase = os.getenv("BYOK_ENCRYPTION_KEY", "").strip()
        if not passphrase:
            raise RuntimeError("BYOK_ENCRYPTION_KEY is missing (required to encrypt/decrypt BYOK API keys)")
        return passphrase

    def save_llm_config(
        self,
        *,
        owner_id: str,
        owner_type: str,
        provider: str,
        api_key: str,
        base_url: str = "",
        model_name: str = "",
        is_active: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Upsert an encrypted LLM config via the `upsert_user_llm_config` RPC."""
        params = {
            "p_owner_id": str(owner_id),
            "p_owner_type": str(owner_type),
            "p_provider": str(provider),
            "p_base_url": base_url or "",
            "p_model_name": model_name or "",
            "p_plain_api_key": api_key or "",
            "p_passphrase": self._get_byok_passphrase(),
            "p_is_active": bool(is_active),
        }
        try:
            response = self.client.rpc("upsert_user_llm_config", params).execute()
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as exc:
            logger.warning("[ProfileDB] save_llm_config failed: %s", exc)
            raise

    def get_llm_config(
        self,
        *,
        owner_id: str,
        owner_type: str = "user",
        provider: str = "openai",
    ) -> Optional[Dict[str, Any]]:
        """Fetch a decrypted LLM config via the `get_user_llm_config` RPC."""
        params = {
            "p_owner_id": str(owner_id),
            "p_owner_type": str(owner_type),
            "p_provider": str(provider),
            "p_passphrase": self._get_byok_passphrase(),
        }
        response = self.client.rpc("get_user_llm_config", params).execute()
        if not response.data:
            return None
        return response.data[0] if isinstance(response.data, list) else response.data

    def delete_llm_config(self, *, owner_id: str, owner_type: str, provider: str) -> bool:
        """Delete an LLM config for an owner/provider."""
        response = (
            self.client.table("user_llm_configs")
            .delete()
            .eq("owner_id", str(owner_id))
            .eq("owner_type", str(owner_type))
            .eq("provider", str(provider))
            .execute()
        )
        return response is not None

    def resolve_llm_config(
        self,
        *,
        discord_user_id: str,
        guild_id: str,
        provider: str = "openai",
    ) -> Optional[Dict[str, Any]]:
        """Prefer user-level config; fall back to guild-level config."""
        user_cfg = self.get_llm_config(owner_id=str(discord_user_id), owner_type="user", provider=provider)
        if user_cfg:
            return user_cfg
        return self.get_llm_config(owner_id=str(guild_id), owner_type="guild", provider=provider)

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
            "calories_intake": int(float(calories_intake)) if calories_intake else 0,
            "protein_g": int(float(protein_g)) if protein_g else 0,
            "steps_count": int(steps_count) if steps_count else 0,
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
            "calories": int(float(calories)) if calories else 0,
            "protein_g": int(float(protein_g)) if protein_g else 0,
            "carbs_g": int(float(carbs_g)) if carbs_g else 0,
            "fat_g": int(float(fat_g)) if fat_g else 0,
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
    # Workout Logs (v6.3 Preference Learning)
    # ============================================

    def get_workout_logs(
        self,
        discord_user_id: str,
        days: int = 14,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw workout logs for preference learning analysis.

        Args:
            discord_user_id: Discord user ID
            days: Number of days to look back (default: 14)
            status: Optional filter by status ("recommended", "completed", etc.)

        Returns:
            List of workout log entries with exercise_name, status, duration_min,
            kcal_estimate, created_at
        """
        start_ts = datetime.now().timestamp() - (days * 24 * 60 * 60)
        start_date = datetime.fromtimestamp(start_ts).isoformat()

        try:
            query = self.client.table("workout_logs")\
                .select("exercise_name, status, duration_min, kcal_estimate, created_at, metadata")\
                .eq("user_id", discord_user_id)\
                .gte("created_at", start_date)\
                .order("created_at", desc=True)

            if status:
                query = query.eq("status", status)

            response = query.execute()
            return response.data or []

        except Exception as e:
            logger.warning(f"[ProfileDB] Failed to fetch workout logs: {e}")
            # Fallback: try chat_messages
            return self._get_workout_logs_from_chat(discord_user_id, days, status)

    def _get_workout_logs_from_chat(
        self,
        discord_user_id: str,
        days: int = 14,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback: Extract workout logs from chat_messages table."""
        start_ts = datetime.now().timestamp() - (days * 24 * 60 * 60)
        logs = []

        try:
            history = self.get_chat_history(discord_user_id, limit=500)
            for msg in history:
                if msg.get("role") != "workout_log":
                    continue

                created_at = msg.get("created_at")
                if created_at:
                    try:
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                        if ts < start_ts:
                            continue
                    except Exception:
                        pass

                try:
                    payload = json.loads(msg.get("content", "{}"))
                except Exception:
                    continue

                if status and payload.get("status") != status:
                    continue

                logs.append({
                    "exercise_name": payload.get("exercise_name"),
                    "status": payload.get("status"),
                    "duration_min": payload.get("duration_min"),
                    "kcal_estimate": payload.get("kcal_estimate"),
                    "created_at": created_at,
                    "metadata": payload.get("metadata", {})
                })

            return logs

        except Exception as e:
            logger.warning(f"[ProfileDB] Fallback workout logs failed: {e}")
            return []

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

    def get_daily_aggregation(self, discord_user_id: str, log_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Aggregate total health data for a specific day.
        Includes Calories In (from meals) and Calories Out (from workout_logs).
        """
        target_date = log_date or date.today()
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()

        # 1. Total Calories In (Meals)
        meal_res = self.client.table("meals")\
            .select("calories, protein_g")\
            .eq("user_id", discord_user_id)\
            .gte("created_at", start)\
            .lte("created_at", end)\
            .execute()
        
        meals = meal_res.data or []
        total_in = sum(float(m.get("calories", 0) or 0) for m in meals)
        total_prot = sum(float(m.get("protein_g", 0) or 0) for m in meals)

        # 2. Total Calories Out (Workout Logs)
        # Note: We filter for 'completed' workouts to be accurate
        workout_res = self.client.table("workout_logs")\
            .select("kcal_estimate, duration_min")\
            .eq("user_id", discord_user_id)\
            .eq("status", "completed")\
            .gte("created_at", start)\
            .lte("created_at", end)\
            .execute()
        
        workouts = workout_res.data or []
        total_out = sum(float(w.get("kcal_estimate", 0) or 0) for w in workouts)
        total_minutes = sum(int(w.get("duration_min", 0) or 0) for w in workouts)

        return {
            "date": target_date.isoformat(),
            "calories_in": total_in,
            "calories_out": total_out,
            "net_calories": total_in - total_out,
            "protein_g": total_prot,
            "active_minutes": total_minutes,
            "meal_count": len(meals),
            "workout_count": len(workouts)
        }

    def get_historical_trends(self, discord_user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Retrieve daily aggregated health data for the last N days.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        start_ts = datetime.combine(start_date, datetime.min.time()).isoformat()
        end_ts = datetime.combine(end_date, datetime.max.time()).isoformat()

        # 1. Fetch all meals in range
        meal_res = self.client.table("meals")\
            .select("calories, protein_g, created_at")\
            .eq("user_id", discord_user_id)\
            .gte("created_at", start_ts)\
            .lte("created_at", end_ts)\
            .execute()
        meals = meal_res.data or []

        # 2. Fetch all completed workouts in range
        workout_res = self.client.table("workout_logs")\
            .select("kcal_estimate, duration_min, created_at")\
            .eq("user_id", discord_user_id)\
            .eq("status", "completed")\
            .gte("created_at", start_ts)\
            .lte("created_at", end_ts)\
            .execute()
        workouts = workout_res.data or []

        # 3. Aggregate by date
        daily_stats = {}
        for i in range(days):
            d = start_date + timedelta(days=i)
            d_str = d.isoformat()
            daily_stats[d_str] = {
                "date": d_str,
                "calories_in": 0.0,
                "calories_out": 0.0,
                "protein_g": 0.0,
                "active_minutes": 0,
                "meal_count": 0,
                "workout_count": 0
            }

        for m in meals:
            m_date = datetime.fromisoformat(m["created_at"].split("T")[0]).date().isoformat()
            if m_date in daily_stats:
                daily_stats[m_date]["calories_in"] += float(m.get("calories", 0) or 0)
                daily_stats[m_date]["protein_g"] += float(m.get("protein_g", 0) or 0)
                daily_stats[m_date]["meal_count"] += 1

        for w in workouts:
            w_date = datetime.fromisoformat(w["created_at"].split("T")[0]).date().isoformat()
            if w_date in daily_stats:
                daily_stats[w_date]["calories_out"] += float(w.get("kcal_estimate", 0) or 0)
                daily_stats[w_date]["active_minutes"] += int(w.get("duration_min", 0) or 0)
                daily_stats[w_date]["workout_count"] += 1

        # Return sorted list
        return sorted(daily_stats.values(), key=lambda x: x["date"])

    def get_monthly_trends_raw(self, discord_user_id: str) -> List[Dict[str, Any]]:
        """
        Query the v_monthly_trends view for high-level monthly stats.
        Returns aggregated data for the last 30 days.
        """
        try:
            response = self.client.table("v_monthly_trends")\
                .select("*")\
                .eq("user_id", discord_user_id)\
                .execute()
            return response.data or []
        except Exception as e:
            # Fallback to manual aggregation if view is missing or inaccessible
            print(f"DEBUG: Falling back from v_monthly_trends due to: {e}")
            return self.get_historical_trends(discord_user_id, days=30)


# Singleton instance for app-wide use
_db_instance: Optional[ProfileDB] = None


def get_profile_db() -> ProfileDB:
    """Get or create singleton ProfileDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProfileDB()
    return _db_instance
