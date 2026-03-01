import logging
import re
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo
from src.discord_bot.profile_db import ProfileDB

logger = logging.getLogger(__name__)

# Vaughan, Ontario → America/Toronto
LOCAL_TZ = ZoneInfo("America/Toronto")

# State (Moved from bot.py for decoupling)
demo_mode = False
demo_user_id = None
demo_guild_id = None

# Temporary demo user profile (in-memory only, cleared on exit)
_demo_user_profile: Dict[str, Any] = {}  # user_id -> temporary profile JSON

# Supabase Profile Database
profile_db: Optional[ProfileDB] = None

# In-memory cache for user profiles (synced with Supabase)
_user_profiles_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> profile

def set_profile_db(db: ProfileDB):
    global profile_db
    profile_db = db

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

def _normalize_gender(gender_raw: str) -> str:
    """Normalize free-text gender input into a small stable set."""
    value = (gender_raw or "").strip().lower()
    if value in {"male", "man", "m"}:
        return "Male"
    if value in {"female", "woman", "f"}:
        return "Female"
    return "Other"

def _parse_int_set(env_val: Optional[str]) -> set[int]:
    """Parses a comma-separated string of IDs into a set of ints."""
    if not env_val:
        return set()
    try:
        return {int(x.strip()) for x in env_val.split(",") if x.strip()}
    except Exception:
        return set()

def save_demo_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    return save_user_profile(user_id, profile)
