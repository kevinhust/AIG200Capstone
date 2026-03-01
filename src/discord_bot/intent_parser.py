import re
from typing import Optional

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
    
    # Exclude if it looks like an actionable request (e.g. "help me work it off")
    action_keywords = {"work", "burn", "exercise", "workout", "plan", "train", "recommend", "suggest", "help"}
    if any(k in text_lower for k in action_keywords):
        return False

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


def _is_sensitive_query(text_lower: str) -> bool:
    """Check if the user is asking for data that should be private (Summary, Trends, Profile)."""
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    
    # 1. Check for specific commands or natural language summary requests
    is_summary = _is_daily_summary_query(text_lower)
    is_profile = _is_profile_query(text_lower)
    
    # 2. Check for "trends" explicitly
    is_trends = "/trends" in text_lower or re.search(r"\b(trends?|analytics|monthly\s+report)\b", text_lower)
    
    return is_summary or is_profile or is_trends


def _looks_health_related(text_lower: str) -> bool:
    """Quick filter to prevent routing random chat to specialist agents."""
    text_lower = (text_lower or "").strip().lower()
    if not text_lower:
        return False
    nutrition_keywords = (
        "food", "eat", "ate", "meal", "calorie", "calories", "macro", "macros",
        "protein", "carb", "fat", "diet", "nutrition", "ingredients", "recipe",
    )
    fitness_keywords = (
        "workout", "exercise", "fitness", "gym", "run", "walk", "steps", "train",
        "cardio", "strength", "stretch", "yoga", "bmi", "weight loss", "gain muscle",
        "health", "healthy", "injury", "pain", "sleep", "stress", "blood pressure",
        "hypertension", "diabetes", "cholesterol",
    )
    return any(k in text_lower for k in nutrition_keywords) or any(
        k in text_lower for k in fitness_keywords
    )
