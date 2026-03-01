"""
Personal Health Butler Discord Bot

Main entry point for Discord Bot deployment on Google Cloud Run.
Integrates HealthSwarm for message processing with persistent Gateway connection.
"""

import asyncio
import logging
import os
import json
from json import JSONDecoder
import re
import uuid
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

import discord
from discord import Intents, Client, Embed
from discord.ext import commands, tasks

from src.swarm import HealthSwarm
from src.discord_bot.embed_builder import HealthButlerEmbed
from src.discord_bot.modals import RegistrationModal
from src.discord_bot.views import RegistrationViewA, RegistrationViewB, LogWorkoutView, SettingsView
from src.discord_bot.roulette_view import RouletteView, MealInspirationView
from src.agents.engagement.engagement_agent import EngagementAgent
from src.agents.analytics.analytics_agent import AnalyticsAgent
from src.discord_bot.profile_db import get_profile_db, ProfileDB
from aiohttp import web

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_ACTIVITY = os.getenv("DISCORD_ACTIVITY", "Helping with nutrition & fitness")

# Vaughan, Ontario → America/Toronto
LOCAL_TZ = ZoneInfo("America/Toronto")

# Demo Mode State (Global) - Pure in-memory, no persistence
demo_mode = False
demo_user_id = None
demo_guild_id = None

# Temporary demo user profile (in-memory only, cleared on exit)
_demo_user_profile: Dict[str, Any] = {}  # user_id -> temporary profile JSON

# Supabase Profile Database
profile_db: Optional[ProfileDB] = None

# In-memory cache for user profiles (synced with Supabase)
_user_profiles_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> profile


def _parse_int_set(value: Optional[str]) -> set[int]:
    items: set[int] = set()
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            items.add(int(part))
        except Exception:
            continue
    return items


def _is_profile_query(text_lower: str) -> bool:
    """Return True when the user is asking about their own profile/identity."""
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    patterns = [
        r"\bwho\s*am\s*i\b",
        r"\bwhoami\b",
        r"\bmy\s+profile\b",
        r"\bshow\s+(me\s+)?(my\s+)?profile\b",
        r"\b(profile|stats|metrics)\b\s*\??$",
        r"\bwhat('?s| is)\s+my\s+(name|age|height|weight|goal|goals|diet|conditions|activity|preferences)\b",
        r"\bmy\s+(name|age|height|weight|goal|goals|diet|conditions|activity|preferences)\b\s*\??$",
        r"\b(daily\s+)?calorie\s+target\b",
        r"\btarget\s+calories\b",
        r"\bdaily\s+target\b",
    ]
    return any(re.search(p, text_lower) for p in patterns)


def _is_daily_summary_query(text_lower: str) -> bool:
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    if re.search(r"\b(summary|stats)\b\s*\??$", text_lower):
        return True
    if re.search(r"\b(today|todays|today's)\b.*\b(summary|stats|log|intake)\b", text_lower):
        return True
    if "today" in text_lower and any(
        k in text_lower for k in ("calorie", "calories", "kcal", "protein", "carb", "fat", "meals")
    ):
        return True
    return False


def _is_help_query(text_lower: str) -> bool:
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    return any(
        phrase in text_lower
        for phrase in (
            "help",
            "commands",
            "what can you do",
            "how do i",
            "how to",
            "usage",
        )
    )


def _looks_health_related(text_lower: str) -> bool:
    """Quick filter to prevent routing random chat to specialist agents."""
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    nutrition_keywords = (
        "food",
        "eat",
        "ate",
        "meal",
        "calorie",
        "calories",
        "macro",
        "macros",
        "protein",
        "carb",
        "fat",
        "diet",
        "nutrition",
        "ingredients",
        "recipe",
    )
    fitness_keywords = (
        "workout",
        "exercise",
        "fitness",
        "gym",
        "run",
        "walk",
        "steps",
        "train",
        "cardio",
        "strength",
        "stretch",
        "yoga",
        "bmi",
        "weight loss",
        "gain muscle",
        "health",
        "healthy",
        "injury",
        "pain",
        "sleep",
        "stress",
        "blood pressure",
        "hypertension",
        "diabetes",
        "cholesterol",
    )
    return any(k in text_lower for k in nutrition_keywords) or any(
        k in text_lower for k in fitness_keywords
    )


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from cache or load from Supabase."""
    global _user_profiles_cache, profile_db

    if user_id in _user_profiles_cache:
        return _user_profiles_cache[user_id]

    # Try to load from Supabase
    if profile_db:
        profile = profile_db.get_profile(user_id)
        if profile:
            # Convert Supabase format back to internal format
            _user_profiles_cache[user_id] = {
                "name": profile.get("full_name", ""),
                "age": profile.get("age", 25),
                "gender": profile.get("gender", "Not specified"),
                "height": profile.get("height_cm", 170),
                "weight": profile.get("weight_kg", 70),
                "goal": profile.get("goal", "General Health"),
                "conditions": profile.get("restrictions", "").split(", ") if profile.get("restrictions") else [],
                "activity": profile.get("activity", "Moderately Active"),
                "diet": profile.get("diet", []).split(", ") if profile.get("diet") else [],
                "preferences": profile.get("preferences_json") or {},
                "meals": []
            }
            return _user_profiles_cache[user_id]

    # Return empty default if not found
    return {"meals": []}


def save_user_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """Save user profile to Supabase."""
    global profile_db, _user_profiles_cache

    if not profile_db:
        logger.warning("ProfileDB not initialized, skipping save")
        return False

    try:
        # Check if profile exists
        existing = profile_db.get_profile(user_id)

        raw_conditions = profile.get("conditions", [])
        conditions = raw_conditions if isinstance(raw_conditions, list) else [str(raw_conditions)]
        raw_diet = profile.get("diet", [])
        diet_list = raw_diet if isinstance(raw_diet, list) else [str(raw_diet)]

        restrictions_str = ", ".join(conditions) if conditions and "None" not in conditions else None
        diet_str = ", ".join(diet_list) if diet_list and "None" not in diet_list else None
        normalized_profile = {
            "name": str(profile.get("name", "")),
            "age": int(profile.get("age", 25)),
            "gender": str(profile.get("gender", "Not specified")),
            "height": float(profile.get("height", profile.get("height_cm", 170))),
            "weight": float(profile.get("weight", profile.get("weight_kg", 70))),
            "goal": str(profile.get("goal", "General Health")),
            "conditions": conditions,
            "activity": str(profile.get("activity", "Moderately Active")),
            "diet": diet_list,
            "preferences": profile.get("preferences") if isinstance(profile.get("preferences"), dict) else {},
            "meals": profile.get("meals", []),
        }

        profile_data = {
            "full_name": normalized_profile["name"],
            "age": normalized_profile["age"],
            "gender": normalized_profile["gender"],
            "weight_kg": normalized_profile["weight"],
            "height_cm": normalized_profile["height"],
            "goal": normalized_profile["goal"],
            "restrictions": restrictions_str,
            "activity": normalized_profile["activity"],
            "diet": diet_str,
            "preferences_json": normalized_profile["preferences"],
        }

        try:
            if existing:
                profile_db.update_profile(user_id, **profile_data)
            else:
                profile_db.create_profile(
                    discord_user_id=user_id,
                    full_name=normalized_profile["name"],
                    age=normalized_profile["age"],
                    gender=normalized_profile["gender"],
                    height_cm=normalized_profile["height"],
                    weight_kg=normalized_profile["weight"],
                    goal=normalized_profile["goal"],
                    conditions=conditions,
                    activity=normalized_profile["activity"],
                    diet=diet_list,
                    preferences=normalized_profile["preferences"],
                )
        except Exception as exc:
            # Backwards-compatible retry when an older Supabase schema is missing `preferences_json`.
            if "preferences_json" in str(exc).lower():
                logger.warning("Retrying profile save without preferences_json column...")
                if existing:
                    fallback_data = dict(profile_data)
                    fallback_data.pop("preferences_json", None)
                    profile_db.update_profile(user_id, **fallback_data)
                else:
                    profile_db.create_profile(
                        discord_user_id=user_id,
                        full_name=normalized_profile["name"],
                        age=normalized_profile["age"],
                        gender=normalized_profile["gender"],
                        height_cm=normalized_profile["height"],
                        weight_kg=normalized_profile["weight"],
                        goal=normalized_profile["goal"],
                        conditions=conditions,
                        activity=normalized_profile["activity"],
                        diet=diet_list,
                        preferences=None,
                    )
            else:
                raise

        # Update cache
        _user_profiles_cache[user_id] = normalized_profile
        logger.info(f"✅ Profile saved for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to save profile: {e}")
        return False


def calculate_daily_target(profile: Dict[str, Any]) -> int:
    """Calculate TDEE based on Mifflin-St Jeor Equation."""
    try:
        weight = float(profile.get('weight_kg', 70))
        height = float(profile.get('height_cm', 170))
        age = int(profile.get('age', 30))
        gender = profile.get('gender', 'Male').lower()
        
        # BMR
        bmr = (10 * weight) + (6.25 * height) - (5 * age)
        if 'female' in gender:
            bmr -= 161
        else:
            bmr += 5
        
        # Activity Factor
        activity_map = {
            "sedentary": 1.2,
            "lightly active": 1.375,
            "moderately active": 1.55,
            "very active": 1.725,
            "extra active": 1.9
        }
        factor = activity_map.get(profile.get('activity', '').lower(), 1.2)
        tdee = bmr * factor
        
        # Goal adjustment
        goal = profile.get('goal', '').lower()
        if 'lose' in goal:
            tdee -= 500
        elif 'gain' in goal:
            tdee += 300
            
        return int(tdee)
    except Exception as e:
        logger.warning(f"Failed to calculate TDEE: {e}")
        return 2000


def save_demo_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """Save demo user profile to Supabase (wrapper for save_user_profile).
    
    Added by Research Agent on 2026-02-12 to fix undefined function error.
    """
    return save_user_profile(user_id, profile)


def _normalize_gender(gender_raw: str) -> str:
    """Normalize free-text gender input into a small stable set."""
    value = (gender_raw or "").strip().lower()
    if value in {"male", "man", "m"}:
        return "Male"
    if value in {"female", "woman", "f"}:
        return "Female"
    return "Other"


# LogWorkoutView moved to src.discord_bot.views.py


def _apply_serving_multiplier(nutrition_payload: Dict[str, Any], multiplier: float, dish_override: Optional[str] = None) -> Dict[str, Any]:
    """Scale a nutrition payload in-place (and return it) by a serving multiplier.

    Bullet-proof behavior:
    - Supports repeated updates (e.g. 1 → 2 → 1) without compounding.
    - Uses `serving_multiplier` already stored on the payload to compute a ratio.
    """
    try:
        m = float(multiplier or 1.0)
    except Exception:
        m = 1.0
    if m <= 0:
        m = 1.0

    try:
        prev = float(nutrition_payload.get("serving_multiplier", 1.0) or 1.0)
    except Exception:
        prev = 1.0
    if prev <= 0:
        prev = 1.0

    ratio = m / prev

    if dish_override:
        nutrition_payload["dish_name"] = str(dish_override).strip() or nutrition_payload.get("dish_name")

    macros = nutrition_payload.get("total_macros", {}) or {}
    if isinstance(macros, dict):
        for key in ("calories", "protein", "carbs", "fat"):
            try:
                macros[key] = round(float(macros.get(key, 0) or 0) * ratio, 1)
            except Exception:
                continue
        nutrition_payload["total_macros"] = macros

    # Keep the per-item breakdown internally consistent by scaling each/total.
    rows = nutrition_payload.get("calorie_breakdown", []) or []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for k in ("calories_each", "calories_total"):
                try:
                    row[k] = round(float(row.get(k, 0) or 0) * ratio, 1)
                except Exception:
                    continue

    nutrition_payload["serving_multiplier"] = round(m, 3)
    return nutrition_payload


class MealServingAdjustModal(discord.ui.Modal, title="Adjust Serving"):
    """Modal to adjust the serving multiplier for a scanned meal."""

    multiplier = discord.ui.TextInput(
        label="Serving multiplier (e.g., 0.5, 1, 2)",
        placeholder="1",
        min_length=1,
        max_length=8,
    )
    dish_name = discord.ui.TextInput(
        label="Dish name override (optional)",
        placeholder="leave blank",
        required=False,
        min_length=0,
        max_length=80,
    )

    def __init__(self, view: "MealLogView"):
        # In unit tests, there may be no running event loop; skip discord.py init.
        self._view = view
        try:
            super().__init__()
        except RuntimeError:
            # Stubs/tests: inputs may be replaced manually.
            pass

    async def on_submit(self, interaction: discord.Interaction):
        # Owner-only
        if str(interaction.user.id) != str(self._view.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        raw = str(getattr(self.multiplier, "value", "") or "").strip()
        try:
            m = float(raw)
        except Exception:
            return await interaction.response.send_message("Please enter a valid number (e.g., 0.5, 1, 2).", ephemeral=True)

        if m <= 0 or m > 10:
            return await interaction.response.send_message("Multiplier must be between 0 and 10.", ephemeral=True)

        dish_override = str(getattr(self.dish_name, "value", "") or "").strip()
        await self._view.apply_multiplier(interaction, m, dish_override=dish_override or None)


class MealLogView(discord.ui.View):
    """Interactive controls to add/remove/adjust a scanned meal in daily totals."""

    def __init__(
        self,
        bot: "HealthButlerDiscordBot",
        *,
        user_id: str,
        nutrition_payload: Dict[str, Any],
        logged_meal: Optional[Dict[str, Any]] = None,
    ):
        self.bot = bot
        self.user_id = str(user_id)
        self.nutrition_payload = nutrition_payload
        self.logged_meal = logged_meal or None

        try:
            super().__init__(timeout=3600)
        except RuntimeError:
            # Unit tests / stubs: allow construction without a running loop.
            pass

        self._sync_button_states()

    def _sync_button_states(self) -> None:
        """Enable/disable buttons based on logged state (best-effort)."""
        try:
            logged = self._is_logged()
            for item in getattr(self, "children", []) or []:
                if getattr(item, "label", None) == "Add to Today":
                    item.disabled = bool(logged)
                elif getattr(item, "label", None) == "Remove from Today":
                    item.disabled = not bool(logged)
        except Exception:
            pass

    def _is_logged(self) -> bool:
        return bool(self.logged_meal and self.logged_meal.get("meal_id"))

    async def _refresh_message_embed(self, interaction: discord.Interaction) -> None:
        """Rebuild and edit the nutrition embed to reflect current payload."""
        embed = self.bot._build_nutrition_embed(self.nutrition_payload)
        # Add a small status marker
        if self._is_logged():
            embed.title = "✅ " + (embed.title or "Nutrition Analysis")
        else:
            embed.title = "📝 " + (embed.title or "Nutrition Analysis")
            embed.set_footer(text=(embed.footer.text + " • Not logged yet") if embed.footer and embed.footer.text else "Not logged yet")
        self._sync_button_states()
        await interaction.message.edit(embed=embed, view=self)

    async def apply_multiplier(self, interaction: discord.Interaction, multiplier: float, *, dish_override: Optional[str] = None) -> None:
        """Apply serving multiplier to payload and persist update if logged."""
        # Update local payload
        _apply_serving_multiplier(self.nutrition_payload, multiplier, dish_override=dish_override)

        meal_id = str((self.logged_meal or {}).get("meal_id") or "")

        # If already logged, update the correct storage backend.
        if self._is_logged():
            global demo_mode, _demo_user_profile, demo_user_id

            # Demo-mode meals are in-memory only (never touch Supabase with demo-* IDs).
            if demo_mode and str(self.user_id) == str(demo_user_id) and meal_id.startswith("demo-"):
                try:
                    macros = dict(self.nutrition_payload.get("total_macros", {}) or {})
                    # Update the canonical meal record stored in demo profile
                    meals = _demo_user_profile.get(self.user_id, {}).get("meals", []) or []
                    for m in meals:
                        if str(m.get("meal_id")) == meal_id:
                            m["dish"] = self.nutrition_payload.get("dish_name", m.get("dish"))
                            m["macros"] = macros
                            break
                    # Keep view state consistent
                    if isinstance(self.logged_meal, dict):
                        self.logged_meal["dish"] = self.nutrition_payload.get("dish_name", self.logged_meal.get("dish"))
                        self.logged_meal["macros"] = macros
                except Exception:
                    pass

            # Persisted meal: update Supabase and recompute daily totals.
            elif profile_db and meal_id and not meal_id.startswith("demo-"):
                try:
                    macros = self.nutrition_payload.get("total_macros", {}) or {}
                    profile_db.update_meal(
                        meal_id,
                        dish_name=self.nutrition_payload.get("dish_name"),
                        calories=float(macros.get("calories", 0) or 0),
                        protein_g=float(macros.get("protein", 0) or 0),
                        carbs_g=float(macros.get("carbs", 0) or 0),
                        fat_g=float(macros.get("fat", 0) or 0),
                    )
                    try:
                        from datetime import date

                        profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
                    except Exception:
                        pass
                except Exception as exc:
                    return await interaction.response.send_message(f"Failed to update meal: {exc}", ephemeral=True)

        await interaction.response.send_message("✅ Updated serving size.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)

    def _build_meal_record(self) -> Dict[str, Any]:
        macros = self.nutrition_payload.get("total_macros", {}) or {}
        return {
            "time": datetime.now(LOCAL_TZ).strftime("%H:%M"),
            "dish": self.nutrition_payload.get("dish_name", "Meal"),
            "macros": {
                "calories": float(macros.get("calories", 0) or 0),
                "protein": float(macros.get("protein", 0) or 0),
                "carbs": float(macros.get("carbs", 0) or 0),
                "fat": float(macros.get("fat", 0) or 0),
            },
        }

    def _cache_add(self, record: Dict[str, Any]) -> None:
        try:
            if self.user_id in _user_profiles_cache:
                _user_profiles_cache[self.user_id].setdefault("meals", []).append(
                    {
                        "meal_id": record.get("meal_id"),
                        "time": record.get("time"),
                        "dish": record.get("dish"),
                        "macros": record.get("macros"),
                    }
                )
        except Exception:
            pass

    def _cache_remove(self, meal_id: str) -> None:
        try:
            if self.user_id in _user_profiles_cache:
                meals = _user_profiles_cache[self.user_id].get("meals", []) or []
                _user_profiles_cache[self.user_id]["meals"] = [m for m in meals if str(m.get("meal_id")) != str(meal_id)]
        except Exception:
            pass

    @discord.ui.button(label="Add to Today", style=discord.ButtonStyle.green, emoji="✅")
    async def add_to_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        if self._is_logged():
            return await interaction.response.send_message("Already logged.", ephemeral=True)

        record = self._build_meal_record()

        global demo_mode, _demo_user_profile, demo_user_id
        if demo_mode and str(self.user_id) == str(demo_user_id):
            # In-memory log
            record["meal_id"] = f"demo-{uuid.uuid4().hex[:10]}"
            _demo_user_profile.setdefault(self.user_id, {"meals": []}).setdefault("meals", []).append(record)
            self.logged_meal = record
        elif profile_db:
            try:
                created = profile_db.create_meal(
                    discord_user_id=self.user_id,
                    dish_name=record["dish"],
                    calories=record["macros"]["calories"],
                    protein_g=record["macros"]["protein"],
                    carbs_g=record["macros"]["carbs"],
                    fat_g=record["macros"]["fat"],
                    confidence_score=float(self.nutrition_payload.get("confidence_score", 0.0) or 0.0),
                )
                meal_id = (created or {}).get("id")
                record["meal_id"] = meal_id or f"db-unknown-{uuid.uuid4().hex[:10]}"
                self.logged_meal = record
                try:
                    from datetime import date

                    profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
                except Exception:
                    pass
            except Exception as exc:
                return await interaction.response.send_message(f"Failed to log meal: {exc}", ephemeral=True)
        else:
            return await interaction.response.send_message("Database not connected; cannot log meals right now.", ephemeral=True)

        self._cache_add(record)
        await interaction.response.send_message("✅ Added to your daily total.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)

    @discord.ui.button(label="Adjust Serving", style=discord.ButtonStyle.gray, emoji="✏️")
    async def adjust_serving(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)
        await interaction.response.send_modal(MealServingAdjustModal(self))

    @discord.ui.button(label="Remove from Today", style=discord.ButtonStyle.red, emoji="🗑️")
    async def remove_from_today(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.user_id):
            return await interaction.response.send_message("This meal is for someone else.", ephemeral=True)

        if not self._is_logged():
            return await interaction.response.send_message("This scan isn't logged yet.", ephemeral=True)

        meal_id = str(self.logged_meal.get("meal_id"))
        global demo_mode, _demo_user_profile, demo_user_id

        if demo_mode and str(self.user_id) == str(demo_user_id):
            meals = _demo_user_profile.get(self.user_id, {}).get("meals", []) or []
            _demo_user_profile[self.user_id]["meals"] = [m for m in meals if str(m.get("meal_id")) != meal_id]
        elif profile_db:
            try:
                profile_db.delete_meal(meal_id)
                try:
                    from datetime import date

                    profile_db.recompute_daily_log_from_meals(self.user_id, date.today())
                except Exception:
                    pass
            except Exception as exc:
                return await interaction.response.send_message(f"Failed to remove meal: {exc}", ephemeral=True)
        else:
            return await interaction.response.send_message("Database not connected; cannot remove meals right now.", ephemeral=True)

        self._cache_remove(meal_id)
        self.logged_meal = None
        await interaction.response.send_message("🗑️ Removed from your daily total.", ephemeral=True)
        await self._refresh_message_embed(interaction)
        await self.bot._send_daily_summary_embed(interaction.channel, self.user_id)





async def _on_registration_modal_submit(interaction: discord.Interaction, data: Dict[str, Any]):
    """Callback for v4.1 simplified RegistrationModal (Step 1/3)"""
    user_id = str(interaction.user.id)
    global _demo_user_profile
    
    # Initialize/Update profile buffer with metrics
    _demo_user_profile[user_id] = {
        "name": data["name"],
        "age": data["age"],
        "height_cm": data["height_cm"],
        "weight_kg": data["weight_kg"],
        "meals": []
    }
    
    # Send Progress Embed (Step 2/3 🟢🟢⚪) and RegistrationViewA
    embed = HealthButlerEmbed.build_progress_embed(
        step=2,
        total_steps=3,
        title="Biological Profile",
        description=(
            f"Thanks **{data['name']}**! We've noted your metrics.\n"
            "Now, please select your **Biological Sex**, **Health Goal**, and **Activity Level** to calibrate your plan."
        )
    )
    
    # Instantiate the new modular view
    view = RegistrationViewA(user_id, _demo_user_profile[user_id], HealthButlerEmbed)
    
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )


class StartSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Start Setup', style=discord.ButtonStyle.green, emoji='🚀')
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationModal(on_submit_callback=_on_registration_modal_submit))





class HealthButlerDiscordBot(Client):
    def __init__(self):
        global profile_db

        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        super().__init__(intents=intents, heartbeat_timeout=120)

        # Initialize Supabase ProfileDB
        try:
            profile_db = get_profile_db()
            logger.info("✅ Supabase ProfileDB initialized")
        except Exception as e:
            logger.warning(f"⚠️ ProfileDB init failed (continuing without persistence): {e}")
            profile_db = None

        self.swarm = HealthSwarm(verbose=True)
        self.start_time = datetime.now()
        # Optional demo safety allowlists (comma-separated IDs). Empty => allow all.
        self.allowed_user_ids = _parse_int_set(os.getenv("DISCORD_ALLOWED_USER_IDS"))
        self.allowed_channel_ids = _parse_int_set(os.getenv("DISCORD_ALLOWED_CHANNEL_IDS"))
        self.engagement_agent = EngagementAgent()
        self.analytics_agent = AnalyticsAgent()
        logger.info("Health Butler Discord Bot initialized with Engagement and Analytics Agents")

    async def setup_hook(self):
        logger.info("Bot setup_hook: starting proactive loops")
        # Start loops
        if not self.morning_checkin.is_running():
            self.morning_checkin.start()
        if not self.nightly_summary.is_running():
            self.nightly_summary.start()
        
        # Start health check server within the loop
        asyncio.create_task(self._start_health_server())

    async def _send_proactive_message(self, user_id: str, embed: discord.Embed, view: Optional[discord.ui.View] = None):
        """Helper to send proactive DM to user if allowed."""
        try:
            profile = get_user_profile(user_id)
            # Check privacy toggle
            prefs = profile.get("preferences", {})
            if not prefs.get("allow_proactive_notifications", True):
                return

            user = await self.fetch_user(int(user_id))
            if user:
                await user.send(embed=embed, view=view)
                logger.info(f"📬 Sent proactive message to {user.display_name}")
        except Exception as e:
            logger.error(f"Failed to send proactive message to {user_id}: {e}")

    async def _start_health_server(self):
        """Minimal HTTP server for Cloud Run health checks."""
        app = web.Application()
        app.router.add_get('/health', lambda r: web.Response(text="OK"))
        port = int(os.getenv("PORT", 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"❤️ Health check server started on port {port}")

    async def on_ready(self):
        logger.info(f"✅ Bot logged in as {self.user} (ID: {self.user.id})")
        # Start proactive tasks (Phase 4 & 6)
        if not self.morning_checkin.is_running():
            self.morning_checkin.start()
        if not self.nightly_summary.is_running():
            self.nightly_summary.start()
        if not self.pre_meal_reminder.is_running():
            self.pre_meal_reminder.start()

    @tasks.loop(time=time(8, 0, tzinfo=LOCAL_TZ))
    async def morning_checkin(self):
        """Proactive morning check-in (Phase 4)."""
        logger.info("🌤️ Running scheduled morning health check-ins...")
        
        # In a real production bot, we would iterate over all active users in Supabase.
        # For this implementation, we'll process the cached users who have opted in.
        for user_id in list(_user_profiles_cache.keys()):
            profile = _user_profiles_cache[user_id]
            
            # Generate personalized greeting
            result = await self.engagement_agent.generate_morning_greeting(profile)
            
            embed = discord.Embed(
                title=f"☀️ Good Morning, {profile.get('name', 'there')}!",
                description=result.get("greeting", "Ready for a healthy day?"),
                color=discord.Color.gold()
            )
            embed.add_field(name="🎯 Today's Focus", value=result.get("focus_goal", profile.get("goal")), inline=False)
            embed.add_field(name="💡 Butler Tip", value=result.get("tip", "Remember to stay hydrated!"), inline=False)
            embed.set_footer(text="Settings: Use /settings to manage notifications")
            
            await self._send_proactive_message(user_id, embed)

    @tasks.loop(time=time(21, 30, tzinfo=LOCAL_TZ))
    async def nightly_summary(self):
        """Proactive nightly summary (Phase 4)."""
        logger.info("🌙 Running scheduled nightly health summaries...")
        
        for user_id in list(_user_profiles_cache.keys()):
            # 1. Aggregate today's data (Meals + Workouts)
            if profile_db:
                aggregation = profile_db.get_daily_aggregation(user_id)
                profile = get_user_profile(user_id)
                
                # 2. Generate AI Insight
                report = await self.engagement_agent.generate_daily_report(aggregation, profile)
                
                embed = discord.Embed(
                    title="📊 Daily Health Report",
                    description=report.get("summary_text", "Here is your summary for today."),
                    color=discord.Color.purple() if report.get("status") == "on_track" else discord.Color.orange()
                )
                
                embed.add_field(name="🍽️ Intake", value=f"{aggregation['calories_in']:.0f} kcal", inline=True)
                embed.add_field(name="🏋️ Burned", value=f"{aggregation['calories_out']:.0f} kcal", inline=True)
                embed.add_field(name="⚖️ Net", value=f"{aggregation['net_calories']:.0f} kcal", inline=True)
                embed.add_field(name="🚀 Tomorrow", value=report.get("tomorrow_tip", "Keep up the momentum!"), inline=False)
                
                await self._send_proactive_message(user_id, embed)

    @tasks.loop(time=[time(11, 30, tzinfo=LOCAL_TZ), time(17, 30, tzinfo=LOCAL_TZ)])
    async def pre_meal_reminder(self):
        """Active inspiration for upcoming meals (Phase 6)."""
        logger.info("🎰 Running scheduled pre-meal inspiration checks...")
        for user_id in list(_user_profiles_cache.keys()):
            try:
                profile = get_user_profile(user_id)
                stats = profile_db.get_today_stats(user_id) if profile_db else {"total_calories": 0}
                target = calculate_daily_target(profile)
                remaining = {"calories": max(0, target - stats["total_calories"])}
                
                embed = discord.Embed(
                    title="🥗 Time for a boost?",
                    description=(
                        f"Hi **{profile.get('name', 'there')}**! It's almost meal time.\n"
                        f"You have **{int(remaining['calories'])} kcal** remaining in your daily budget.\n\n"
                        "Need some healthy inspiration? Try the **Food Roulette** below!"
                    ),
                    color=discord.Color.green()
                )
                view = MealInspirationView(user_id, remaining)
                await self._send_proactive_message(user_id, embed, view=view)
            except Exception as e:
                logger.error(f"Error in pre_meal_reminder for {user_id}: {e}")

    @morning_checkin.before_loop
    @nightly_summary.before_loop
    @pre_meal_reminder.before_loop
    async def before_loops(self):
        await self.wait_until_ready()

    def _persist_chat_message(self, user_id: str, role: str, content: str) -> None:
        """Persist chat message to Supabase with safe type normalization."""
        global profile_db
        if not profile_db:
            return

        try:
            normalized_role = str(role or "user")
            normalized_content = str(content or "")
            profile_db.save_message(
                discord_user_id=str(user_id),
                role=normalized_role,
                content=normalized_content,
            )
        except Exception as exc:
            logger.warning(f"Failed to persist chat message: {exc}")

    async def on_message(self, message: discord.Message):
        global demo_mode, demo_user_id
        if message.author.bot or not message.guild: return

        # Optional allowlists for demo safety (empty allowlist => allow all)
        if self.allowed_user_ids and message.author.id not in self.allowed_user_ids:
            return
        if self.allowed_channel_ids and message.channel.id not in self.allowed_channel_ids:
            return

        self._persist_chat_message(str(message.author.id), "user", message.content)

        # Helper for user_id in later scopes
        author_id = str(message.author.id)

        if message.content.strip().lower().startswith("/demo"):
            await self._handle_demo_command(message)
            return

        if message.content.strip().lower() == "/settings":
            profile = get_user_profile(author_id)
            embed = discord.Embed(
                title="⚙️ Health Butler Settings",
                description="Manage your notification and privacy preferences.",
                color=discord.Color.blue()
            )
            allow_proactive = profile.get("preferences", {}).get("allow_proactive_notifications", True)
            status_text = "✅ Enabled" if allow_proactive else "❌ Disabled"
            embed.add_field(name="Proactive Notifications", value=f"Current status: {status_text}", inline=False)
            
            await message.channel.send(embed=embed, view=SettingsView(author_id, profile))
            return

        if message.content.strip().lower() == "/trends":
            profile = get_user_profile(author_id)
            if not profile or not profile.get("name"):
                await message.channel.send("⚠️ You need to complete your profile first! Use `/setup` or type anything health-related.")
                return

            await message.channel.send("🔍 Analyzing your health trends... this may take a moment.")
            
            # 1. Fetch 30-day data
            if profile_db:
                historical_data = profile_db.get_historical_trends(author_id, days=30)
                
                # 2. Process with AnalyticsAgent
                analysis = await self.analytics_agent.analyze_trends(historical_data, profile)
                
                # 3. Build & Send Embed
                embed = HealthButlerEmbed.build_trends_embed(
                    user_name=profile.get("name", "User"),
                    trend_data=analysis,
                    historical_raw=historical_data
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("⚠️ Database not available for trend analysis.")
            return

        if message.content.strip().lower().startswith("!settings"):
            await self._handle_settings_command(message)
            return

        if message.content.strip().lower() in ("/exit", "/quit"):
            if demo_mode: await self._handle_exit_command(message)
            else: await message.channel.send("⚠️ Use `/demo` first.")
            return

        if demo_mode and str(message.author.id) != demo_user_id: return

        # Load profile (prefer in-memory demo profile, fallback to persisted profile)
        global _demo_user_profile
        persisted_profile = get_user_profile(author_id)
        user_profile = _demo_user_profile.get(author_id) or persisted_profile or {"meals": []}
        if "meals" not in user_profile:
            user_profile["meals"] = []

        # Quick intent shortcuts to avoid misrouting random/meta queries to Nutrition.
        content_lower = (message.content or "").strip().lower()
        if not message.attachments:
            if _is_profile_query(content_lower):
                await self._send_user_profile_embed(message.channel, author_id, user_profile)
                await self._send_daily_summary_embed(message.channel, author_id)
                return

            if _is_daily_summary_query(content_lower):
                await self._send_daily_summary_embed(message.channel, author_id)
                return

            if _is_help_query(content_lower) or not _looks_health_related(content_lower):
                await message.channel.send(
                    "I can help with **nutrition** (meal photos, calories, macros) and **fitness** (workouts, goals).\n"
                    "- Upload a food photo to get a nutrition analysis.\n"
                    "- Ask: \"Give me a 20-minute beginner workout at home\".\n"
                    "- Ask: \"Who am I?\" to view your saved profile.\n"
                    "If you haven't onboarded yet, run `/demo` to register."
                )
                return

        try:
            image_attachment = next((a for a in message.attachments if a.content_type and a.content_type.startswith('image/')), None)
            user_context = {
                "user_id": str(message.author.id),
                "username": message.author.display_name,
                "name": user_profile.get("name", message.author.display_name),
                "age": user_profile.get("age", 30),
                "gender": user_profile.get("gender", "Not specified"),
                "height": user_profile.get("height", user_profile.get("height_cm", 170)),
                "weight": user_profile.get("weight", user_profile.get("weight_kg", 70)),
                "conditions": user_profile.get("conditions", []),
                "goal": user_profile.get("goal", "General Health"),
                "activity": user_profile.get("activity", "Moderately Active"),
                "diet": user_profile.get("diet", []),
                "preferences": user_profile.get("preferences", {}),
                "daily_intake": user_profile.get("meals", [])
            }

            async with message.channel.typing():
                if image_attachment:
                    image_path = f"/tmp/{image_attachment.filename}"
                    await image_attachment.save(image_path)
                    
                    # Iterative status message for streaming feedback
                    status_msg = await message.channel.send("📸 *Image received, analyzing components...*")
                    
                    async def progress_update(state: str, status_text: str):
                        try:
                            await status_msg.edit(content=status_text)
                        except Exception:
                            pass

                    try:
                        result = await self.swarm.execute_async(
                            user_input="Analyze this meal", 
                            image_path=image_path, 
                            user_context=user_context,
                            progress_callback=progress_update
                        )
                    finally:
                        if os.path.exists(image_path):
                            os.remove(image_path)
                        try:
                            await status_msg.delete()
                        except Exception:
                            pass
                else:
                    result = await self.swarm.execute_async(
                        user_input=message.content, 
                        user_context=user_context
                    )

                # Persist scanned meals only (image uploads). Text-only nutrition queries should NOT
                # auto-affect consumed totals.
                latest_meal = None
                if image_attachment:
                    try:
                        parsed = self._extract_json_payload(result.get("response") or "")
                        macros = (parsed or {}).get("total_macros", {}) if isinstance(parsed, dict) else {}
                        calories = self._to_float(macros.get("calories", 0), 0.0)
                        confidence = self._to_float(
                            (parsed or {}).get("confidence_score", (parsed or {}).get("total_confidence", 0.0)),
                            0.0,
                        )
                        # Avoid logging "no food detected" / 0-kcal scans automatically.
                        if calories > 0 and confidence >= 0.10:
                            latest_meal = await self._persist_meal_data(result["response"], str(message.author.id))
                    except Exception:
                        latest_meal = None

                await self._send_swarmed_response(
                    message.channel,
                    result["response"],
                    str(message.author.id),
                    latest_meal=latest_meal,
                    scan_mode=bool(image_attachment),
                )

        except Exception as e:
            logger.error(f"Error: {e}")
            await message.channel.send(f"⚠️ Error: {str(e)}")

    async def _send_swarmed_response(
        self,
        channel,
        response: str,
        interaction_user_id: str,
        latest_meal: Optional[Dict[str, Any]] = None,
        *,
        scan_mode: bool = False,
    ):
        try:
            clean_str = response.strip()
            self._persist_chat_message(str(interaction_user_id), "assistant", clean_str)
            data = self._extract_json_payload(clean_str)

            # If we have structured data, use the Unified Embed Design
            if isinstance(data, dict):
                # Check if it's a Nutrition analysis
                if "dish_name" in data and "total_macros" in data:
                    embed = self._build_nutrition_embed(data)
                    view = None
                    if scan_mode:
                        view = MealLogView(
                            self,
                            user_id=str(interaction_user_id),
                            nutrition_payload=data,
                            logged_meal=latest_meal,
                        )
                        # Add a visible status marker at send-time (so user doesn't need to click).
                        if latest_meal and latest_meal.get("meal_id"):
                            embed.title = "✅ " + (embed.title or "Nutrition Analysis")
                        else:
                            embed.title = "📝 " + (embed.title or "Nutrition Analysis")
                            if embed.footer and embed.footer.text:
                                embed.set_footer(text=embed.footer.text + " • Not logged yet")
                            else:
                                embed.set_footer(text="Not logged yet")

                    if view:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                elif "summary" in data and ("recommendations" in data or "exercises" in data):
                    user_profile = get_user_profile(str(interaction_user_id))
                    display_name = user_profile.get("name") or "User"
                    embed = self._build_fitness_embed(data, user_name=display_name)
                    await self._persist_fitness_plan(data, interaction_user_id)
                    await channel.send(embed=embed, view=LogWorkoutView(self, data, interaction_user_id))
                else:
                    # Fallback for other specialist agents or generic JSON
                    embed = Embed(title="💎 Health Butler Analysis", color=discord.Color.blue())
                    for k, v in data.items():
                        if isinstance(v, (str, int, float)) and len(str(v)) < 1000:
                            embed.add_field(name=k.replace("_", " ").title(), value=str(v), inline=False)
                    await channel.send(embed=embed)
                
                # Show Today's Summary with direct injection to bypass DB latency
                await self._send_daily_summary_embed(channel, str(interaction_user_id), latest_meal=latest_meal)
                return

            # Fallback for text-only responses
            MAX_LEN = 1900
            if len(clean_str) > MAX_LEN:
                for i in range(0, len(clean_str), MAX_LEN):
                    await channel.send(clean_str[i:i+MAX_LEN])
            else:
                await channel.send(clean_str)

        except Exception as e:
            logger.error(f"Response handling error: {e}")
            await channel.send(f"⚠️ Error processing response: {str(e)[:100]}")

    async def _send_user_profile_embed(self, channel, user_id: str, profile: Dict[str, Any]) -> None:
        """Send a profile summary embed (no agent routing)."""
        # Basic existence check
        has_any = any(
            profile.get(k)
            for k in (
                "name",
                "age",
                "gender",
                "height",
                "height_cm",
                "weight",
                "weight_kg",
                "goal",
                "activity",
                "diet",
                "conditions",
                "preferences",
            )
        )
        if not has_any or profile == {"meals": []}:
            await channel.send("⚠️ I don't have a saved profile for you yet. Run `/demo` to register.")
            return

        name = profile.get("name") or "Not provided"
        age = profile.get("age", "N/A")
        gender = profile.get("gender", "N/A")
        height = profile.get("height", profile.get("height_cm", "N/A"))
        weight = profile.get("weight", profile.get("weight_kg", "N/A"))
        goal = profile.get("goal", "General Health")
        activity = profile.get("activity", "Moderately Active")
        diet = profile.get("diet", [])
        conditions = profile.get("conditions", [])
        prefs = profile.get("preferences", {}) if isinstance(profile.get("preferences"), dict) else {}

        # Determine persistence status
        saved = False
        try:
            global profile_db
            if profile_db and profile_db.get_profile(str(user_id)):
                saved = True
        except Exception:
            saved = False

        embed = Embed(title="👤 Your Profile", color=discord.Color.blurple())
        embed.add_field(name="Name", value=str(name), inline=True)
        embed.add_field(name="Age / Gender", value=f"{age} / {gender}", inline=True)
        embed.add_field(name="Metrics", value=f"{height} cm / {weight} kg", inline=False)
        embed.add_field(name="Goal", value=str(goal), inline=True)
        embed.add_field(name="Activity", value=str(activity), inline=True)
        embed.add_field(
            name="Conditions",
            value=", ".join(conditions) if conditions else "None",
            inline=False,
        )
        embed.add_field(
            name="Diet",
            value=", ".join(diet) if isinstance(diet, list) and diet else "None",
            inline=False,
        )
        if prefs:
            pref_lines = []
            if "sleep_hours" in prefs:
                pref_lines.append(f"Sleep: {prefs.get('sleep_hours')}h")
            if "stress_level" in prefs:
                pref_lines.append(f"Stress: {prefs.get('stress_level')}/10")
            if "workout_days_per_week" in prefs:
                pref_lines.append(f"Workout days: {prefs.get('workout_days_per_week')}/wk")
            if "session_minutes" in prefs:
                pref_lines.append(f"Session: {prefs.get('session_minutes')} min")
            if "motivation_style" in prefs:
                pref_lines.append(f"Motivation: {prefs.get('motivation_style')}")
            if pref_lines:
                embed.add_field(name="Personalization", value=" | ".join(pref_lines), inline=False)

        embed.set_footer(
            text="✅ Saved to database" if saved else "⚠️ In-session only (Supabase not configured)"
        )
        await channel.send(embed=embed)

    def _extract_json_payload(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the most relevant JSON object from model output text.

        Priority:
        1) Whole-string JSON object
        2) Any embedded JSON object containing nutrition payload keys
        3) First embedded JSON object
        """
        if not text:
            return None

        clean = text.strip()

        if "```json" in clean:
            clean = clean.split("```json")[-1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[-1].split("```")[0].strip()

        try:
            payload = json.loads(clean)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        decoder = JSONDecoder()
        candidates: List[Dict[str, Any]] = []
        for idx, ch in enumerate(clean):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(clean, idx)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except Exception:
                continue

        if not candidates:
            return None

        preferred = next(
            (
                obj
                for obj in candidates
                if "dish_name" in obj and "total_macros" in obj
            ),
            None,
        )
        if preferred:
            return preferred

        return candidates[0]

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _macros_from_items(self, data: Dict[str, Any]) -> Dict[str, float]:
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for item in data.get("items_detected", []) or []:
            if not isinstance(item, dict):
                continue
            macros = item.get("macros", {})
            for key in totals:
                totals[key] += self._to_float(macros.get(key, 0), 0.0)
        return totals

    def _calorie_breakdown_rows(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return normalized calorie breakdown rows for embed display."""
        normalized_rows: List[Dict[str, Any]] = []

        def aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            grouped: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                item_name = str(row.get("item") or "Unknown").strip()
                qty = max(1, int(self._to_float(row.get("quantity"), 1)))
                c_total = self._to_float(row.get("calories_total"), 0.0)
                if c_total <= 0:
                    continue

                if item_name not in grouped:
                    grouped[item_name] = {
                        "item": item_name,
                        "quantity": 0,
                        "calories_total": 0.0,
                    }
                grouped[item_name]["quantity"] += qty
                grouped[item_name]["calories_total"] += c_total

            output: List[Dict[str, Any]] = []
            for row in grouped.values():
                quantity = row["quantity"]
                calories_total = round(row["calories_total"], 1)
                output.append(
                    {
                        "item": row["item"],
                        "quantity": quantity,
                        "calories_each": round(calories_total / quantity, 1),
                        "calories_total": calories_total,
                    }
                )

            return output

        source_rows = data.get("calorie_breakdown", []) or []
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("item") or "Unknown").strip()
            quantity = max(1, int(self._to_float(row.get("quantity"), 1)))
            c_each = round(self._to_float(row.get("calories_each"), 0.0), 1)
            c_total = round(self._to_float(row.get("calories_total"), 0.0), 1)
            if c_total <= 0:
                continue
            normalized_rows.append(
                {
                    "item": name,
                    "quantity": quantity,
                    "calories_each": c_each if c_each > 0 else round(c_total / quantity, 1),
                    "calories_total": c_total,
                }
            )

        if normalized_rows:
            return aggregate_rows(normalized_rows)

        for item in data.get("items_detected", []) or []:
            if not isinstance(item, dict):
                continue
            macros = item.get("macros", {}) or {}
            item_total = round(self._to_float(macros.get("calories"), 0.0), 1)
            if item_total <= 0:
                continue
            normalized_rows.append(
                {
                    "item": str(item.get("name") or "Unknown"),
                    "quantity": 1,
                    "calories_each": item_total,
                    "calories_total": item_total,
                }
            )

        return aggregate_rows(normalized_rows)

    def _build_nutrition_embed(self, data: Dict[str, Any]) -> Embed:
        """
        Build a premium, standardized nutrition embed based on user-provided design.
        """
        dish = data.get("dish_name", "Unknown Meal")
        macros = data.get("total_macros", {})
        dt = data.get("detailed_nutrients", {})
        confidence = data.get("confidence_score", 0.9)
        
        stars = "★" * min(5, max(0, int(confidence * 5))) + "☆" * (5 - min(5, max(0, int(confidence * 5))))
        title = f"Nutrition Analysis: {dish} • {int(confidence*100)}% Confidence"
        embed = Embed(title=title, color=discord.Color.green())

        cals = self._to_float(macros.get("calories", 0), 0.0)
        p = self._to_float(macros.get("protein", 0), 0.0)
        c = self._to_float(macros.get("carbs", 0), 0.0)
        f = self._to_float(macros.get("fat", 0), 0.0)

        if cals <= 0 and p <= 0 and c <= 0 and f <= 0:
            recovered = self._macros_from_items(data)
            if recovered["calories"] > 0:
                cals, p, c, f = recovered["calories"], recovered["protein"], recovered["carbs"], recovered["fat"]
                data["total_macros"] = {"calories": round(cals, 1), "protein": round(p, 1), "carbs": round(c, 1), "fat": round(f, 1)}

        breakdown_rows = self._calorie_breakdown_rows(data)
        if breakdown_rows and cals <= 0:
            cals = round(sum(row.get("calories_total", 0.0) for row in breakdown_rows), 1)
            data.setdefault("total_macros", {})["calories"] = cals
        
        embed.description = f"🔥 **{cals}** kcal | 🍖 **{p}g** P | 🍞 **{c}g** C | 🥑 **{f}g** F"

        total_g = p + c + f
        if total_g > 0:
            def get_bar(val):
                pct = int((val / total_g) * 20)
                return "█" * pct + "░" * (20 - pct)

            def color_bar(val, marker: str):
                pct = int((val / total_g) * 12)
                return marker * pct + "⬛" * (12 - pct)
            
            p_pct = (p / total_g) * 100
            c_pct = (c / total_g) * 100
            f_pct = (f / total_g) * 100
            
            breakdown = (
                f"🍖 **Protein** {p_pct:2.0f}% • {round(p, 1)}g\n"
                f"{color_bar(p, '🟦')}\n"
                f"🍞 **Carbs** {c_pct:2.0f}% • {round(c, 1)}g\n"
                f"{color_bar(c, '🟨')}\n"
                f"🥑 **Fat** {f_pct:2.0f}% • {round(f, 1)}g\n"
                f"{color_bar(f, '🟩')}"
            )
            embed.add_field(name="📊 Macros Breakdown", value=breakdown, inline=False)

        # Phase 6: Daily Impact & Remaining Budget
        dv = data.get("daily_value_percentage", {})
        budget = data.get("remaining_budget", {})
        if dv or budget:
            def render_impact_line(label, current_pct, remaining_val, unit="", marker="🟧"):
                filled = int(min(100, current_pct) / 10)
                bar = marker * filled + "⬜" * (10 - filled)
                return f"**{label}**: `{bar}` **{current_pct:.1f}%**\n➡️ *Remaining: {remaining_val} {unit}*"

            impact_text = (
                render_impact_line("Calories", dv.get("calories", 0), budget.get("calories", 0), "kcal", "🟧") + "\n" +
                render_impact_line("Protein", dv.get("protein", 0), budget.get("protein", 0), "g", "🟦") + "\n" +
                render_impact_line("Carbs", dv.get("carbs", 0), budget.get("carbs", 0), "g", "🟨") + "\n" +
                render_impact_line("Fat", dv.get("fat", 0), budget.get("fat", 0), "g", "🟩")
            )
            embed.add_field(name="📈 Daily Impact & Remaining Budget", value=impact_text, inline=False)

        if breakdown_rows:
            detail_lines = []
            for row in breakdown_rows[:6]:
                qty = row.get("quantity", 1)
                line = (
                    f"• {row.get('item', 'Item')}: {row.get('calories_each', 0):.1f} kcal"
                    f" × {qty} = **{row.get('calories_total', 0):.1f} kcal**"
                )
                detail_lines.append(line)

            listed_total = sum(self._to_float(row.get("calories_total"), 0.0) for row in breakdown_rows)
            detail_lines.append(f"**Overall Total: {listed_total:.1f} kcal**")
            embed.add_field(name="🍽️ Calories by Item", value="\n".join(detail_lines), inline=False)

        ingredients = data.get("ingredients_with_portions", [])
        if not ingredients:
            raw_items = data.get("items_detected", [])
            normalized = []
            for item in raw_items[:6]:
                if isinstance(item, dict):
                    name = item.get("name", "Unknown")
                    portion = item.get("estimated_weight_grams")
                    if portion:
                        normalized.append(f"{name} (~{portion}g)")
                    else:
                        normalized.append(name)
                else:
                    normalized.append(str(item))
            ingredients = normalized

        ing_list = "\n".join([f"• {i}" for i in ingredients[:6]]) if ingredients else "Not specified"
        embed.add_field(name="🥗 Key Ingredients", value=ing_list, inline=False)

        insight = self._compose_health_insight(data, cals)
        embed.add_field(name="💡 Health Insight", value=insight, inline=False)

        embed.set_footer(text=f"Confidence: {stars} ({int(confidence*100)}%) • Anchored to USDA data + visual estimation")
        return embed

    def _compose_health_insight(self, data: Dict[str, Any], calories: float) -> str:
        """Generate a concise 1-3 sentence overview (food + workout + status)."""
        base_tip = data.get("health_tip") or data.get("composition_analysis") or "Meal analyzed successfully."

        if calories >= 700:
            workout_sentence = "Workout suggestion: add 35-45 minutes of moderate cardio or a brisk walk."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and is on the higher side, so keep your next meal lighter and protein-focused."
        elif calories >= 350:
            workout_sentence = "Workout suggestion: 20-30 minutes of activity helps keep daily balance."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and fits a moderate intake range for most goals."
        else:
            workout_sentence = "Workout suggestion: a short 10-20 minute walk is enough for digestion and consistency."
            status_sentence = f"Food and current status: this meal is about {int(calories)} kcal and is relatively light, leaving flexibility for later meals."

        concise_base = base_tip.split(".")[0].strip()
        tip_line = f"• {concise_base}." if concise_base else "• Meal analyzed successfully."
        status_line = f"• {status_sentence}"
        workout_line = f"• {workout_sentence}"
        return "\n".join([tip_line, status_line, workout_line])

    def _build_fitness_embed(self, data: Dict[str, Any], user_name: str = "User") -> Embed:
        """Build fitness-specific embed for structured FitnessAgent output using HealthButlerEmbed factory."""
        return HealthButlerEmbed.build_fitness_card(data, user_name=user_name)

    async def _persist_fitness_plan(self, data: Dict[str, Any], user_id: str) -> None:
        """Persist recommended workouts so plans are tracked in Supabase."""
        if not profile_db:
            return
        try:
            for rec in (data.get("recommendations", []) or [])[:5]:
                profile_db.log_workout_event(
                    discord_user_id=user_id,
                    exercise_name=str(rec.get("name", "Exercise")),
                    duration_min=int(self._to_float(rec.get("duration_min", 20), 20)),
                    kcal_estimate=self._to_float(rec.get("kcal_estimate", 80), 80),
                    status="recommended",
                    source="fitness_agent",
                    raw_payload=rec,
                )
        except Exception as e:
            logger.warning(f"Failed to persist fitness plan: {e}")

    async def _send_daily_summary_embed(self, channel, user_id: str, latest_meal: Optional[Dict[str, Any]] = None):
        """Send a 'Today's Summary' embed as requested by user."""
        if not user_id:
            return

        # Demo mode: compute totals from in-memory meal log (no DB dependency).
        global demo_mode, demo_user_id, _demo_user_profile
        if demo_mode and demo_user_id and str(user_id) == str(demo_user_id):
            try:
                profile = _demo_user_profile.get(str(user_id)) or get_user_profile(str(user_id)) or {"meals": []}
                meals = profile.get("meals", []) or []
                consumed = sum(float((m.get("macros") or {}).get("calories", 0) or 0) for m in meals)
                meals_count = len(meals)
                target = calculate_daily_target(profile)

                percent = (consumed / target * 100) if target > 0 else 0
                remaining = target - consumed

                embed = Embed(title="🟢 Today's Summary", color=discord.Color.green())
                embed.add_field(
                    name="📊 Calories",
                    value=f"**{consumed}** / {target} kcal ({percent:.1f}%)",
                    inline=False,
                )
                embed.add_field(name="🍽️ Meals", value=f"**{meals_count}**", inline=True)
                if remaining > 0:
                    embed.add_field(name="💡 Status", value=f"You can have about **{remaining}** more kcal", inline=False)
                else:
                    embed.add_field(name="⚠️ Status", value=f"Over target by **{abs(remaining)}** kcal", inline=False)
                await channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send daily summary (demo): {e}")
            return

        if not profile_db:
            return
        
        try:
            profile = get_user_profile(user_id)
            stats = profile_db.get_today_stats(user_id)
            target = calculate_daily_target(profile)
            
            consumed = stats["total_calories"]
            meals_count = stats["meal_count"]
            
            # Direct Injection Logic: If summary doesn't yet include the latest meal, add it.
            # This happens due to eventual consistency or write propagation delay.
            if latest_meal and latest_meal.get("macros", {}).get("calories"):
                # Check if this meal is already accounted for in stats (simple heuristic: if stats is 0 but we have a meal, it's definitely missing)
                if consumed < latest_meal["macros"]["calories"]:
                    consumed += latest_meal["macros"]["calories"]
                    meals_count += 1
                    logger.info("💉 Injected latest meal into summary to bypass DB latency")

            percent = (consumed / target * 100) if target > 0 else 0
            remaining = target - consumed
            
            embed = Embed(title="🟢 Today's Summary", color=discord.Color.green())
            embed.add_field(
                name="📊 Calories", 
                value=f"**{consumed}** / {target} kcal ({percent:.1f}%)", 
                inline=False
            )
            embed.add_field(name="🍽️ Meals", value=f"**{meals_count}**", inline=True)
            
            if remaining > 0:
                embed.add_field(name="💡 Status", value=f"You can have about **{remaining}** more kcal", inline=False)
            else:
                embed.add_field(name="⚠️ Status", value=f"Over target by **{abs(remaining)}** kcal", inline=False)
                
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")

    async def _persist_meal_data(self, response: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Extract and persist meal data - in-memory for demo, Supabase for real users."""
        try:
            data = self._extract_json_payload(response)
            if not data:
                return None

            if "dish_name" in data and "total_macros" in data:
                m = data["total_macros"]
                meal_record = {
                    "meal_id": None,
                    "time": datetime.now(LOCAL_TZ).strftime("%H:%M"),
                    "dish": data["dish_name"],
                    "macros": data["total_macros"]
                }

                global demo_mode, _demo_user_profile, profile_db

                # Demo mode: in-memory only
                if demo_mode and user_id == demo_user_id:
                    if user_id not in _demo_user_profile:
                        _demo_user_profile[user_id] = {"meals": []}
                    meal_record["meal_id"] = f"demo-{uuid.uuid4().hex[:10]}"
                    _demo_user_profile[user_id].setdefault("meals", []).append(meal_record)
                    logger.info(f"📝 Demo meal saved: {data['dish_name']}")

                # Real user: persist to Supabase
                elif profile_db:
                    from datetime import date
                    today = date.today()
                    calories = float(m.get('calories', 0) or 0)
                    protein = float(m.get('protein', 0) or 0)
                    carbs = float(m.get('carbs', 0) or 0)
                    fat = float(m.get('fat', 0) or 0)

                    # Keep legacy daily_logs write for backwards compatibility (tests + older schema).
                    try:
                        profile_db.create_daily_log(
                            discord_user_id=user_id,
                            log_date=today,
                            calories_intake=calories,
                            protein_g=protein,
                        )
                    except Exception:
                        pass

                    # 1. Create detailed meal record (source of truth for totals)
                    created = profile_db.create_meal(
                        discord_user_id=user_id,
                        dish_name=data["dish_name"],
                        calories=calories,
                        protein_g=protein,
                        carbs_g=carbs,
                        fat_g=fat,
                        confidence_score=data.get("confidence_score") or data.get("total_confidence", 0.0)
                    )
                    meal_record["meal_id"] = (created or {}).get("id")
                    logger.info(f"💾 Detailed meal persisted to DB: {data['dish_name']} ({calories} kcal)")

                    # 2. Recompute daily log totals from meals (keeps daily_logs consistent)
                    try:
                        profile_db.recompute_daily_log_from_meals(user_id, today)
                    except Exception:
                        pass

                    # Also update local cache
                    if user_id in _user_profiles_cache:
                        _user_profiles_cache[user_id].setdefault("meals", []).append(meal_record)

                return meal_record

        except Exception as e:
            logger.debug(f"Meal persist error: {e}")

        return None

    async def _handle_demo_command(self, message):
        global demo_mode, demo_user_id, demo_user_profile
        if not demo_mode:
            # Check if user already has a profile
            user_id = str(message.author.id)
            existing_profile = get_user_profile(user_id)

            if existing_profile and existing_profile.get("name"):
                # User exists, activate demo mode directly
                demo_mode = True
                demo_user_id = user_id
                _demo_user_profile[user_id] = existing_profile

                await message.channel.send(
                    f"👋 Welcome back, **{existing_profile.get('name', 'User')}**!\n"
                    f"Your profile has been loaded from database.\n"
                    f"Goal: {existing_profile.get('goal', 'General Health')}\n"
                    "You can now ask health questions or upload food photos!"
                )
            else:
                # Always start fresh registration flow
                await message.channel.send(
                    "Hi! I'm **Health Butler**. Let's set up your profile for safety-first health advice.",
                    view=StartSetupView()
                )

    async def _handle_exit_command(self, message):
        global demo_mode, demo_user_id, _demo_user_profile
        user_id = str(message.author.id)

        demo_mode = False
        demo_user_id = None

        # Clear this user's temporary demo profile
        if user_id in _demo_user_profile:
            del _demo_user_profile[user_id]
            logger.info(f"🗑️ Cleared demo profile for user {user_id}")
    async def _handle_settings_command(self, message: discord.Message):
        """Manages personalized engagement settings (Phase 4)."""
        author_id = str(message.author.id)
        content = message.content.replace("!settings", "").strip().lower()
        
        # Fetch profile
        profile = _user_profiles_cache.get(author_id) or get_user_profile(author_id) or {}
        prefs = profile.get("preferences_json", {})
        
        if not content:
            status_ico = "✅ Enabled" if prefs.get("morning_checkin_enabled", True) else "❌ Disabled"
            await message.reply(
                f"⚙️ **Your Health Assistant Settings**\n"
                f"• Morning Check-in: **{status_ico}**\n\n"
                f"To toggle, use `!settings morning on` or `!settings morning off`."
            )
            return

        if "morning" in content:
            new_val = "off" not in content
            prefs["morning_checkin_enabled"] = new_val
            if profile_db:
                profile_db.update_profile(author_id, preferences_json=prefs)
            
            # Update cache
            if author_id in _user_profiles_cache:
                _user_profiles_cache[author_id]["preferences_json"] = prefs
            
            status_text = "enabled" if new_val else "disabled"
            await message.reply(f"✅ Morning Check-in successfully **{status_text}**.")

def main():
    bot = HealthButlerDiscordBot()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        logger.error("No DISCORD_TOKEN found.")

if __name__ == "__main__":
    main()
