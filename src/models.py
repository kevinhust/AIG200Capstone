"""Pydantic DTOs for Supabase-persisted multiplayer features.

These models are intentionally thin and map closely to the database schema used by
`src/discord_bot/profile_db.py`.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

PrivacyLevel = Literal["public", "friends", "private"]
FriendStatus = Literal["pending", "accepted", "blocked"]
OwnerType = Literal["user", "guild"]
LLMProvider = Literal["openai", "anthropic", "google", "local", "custom"]


_DAY_FIELDS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

_CANONICAL_SPLIT_TAGS: dict[str, str] = {
    # Core lifts / muscle groups
    "chest": "chest",
    "pec": "chest",
    "pecs": "chest",
    "back": "back",
    "lats": "back",
    "shoulder": "shoulders",
    "shoulders": "shoulders",
    "delts": "shoulders",
    "bicep": "biceps",
    "biceps": "biceps",
    "tricep": "triceps",
    "triceps": "triceps",
    "arm": "arms",
    "arms": "arms",
    "leg": "legs",
    "legs": "legs",
    "lower": "lower",
    "upper": "upper",
    "full": "full_body",
    "full_body": "full_body",
    "core": "abs",
    "abs": "abs",
    "glute": "glutes",
    "glutes": "glutes",
    "quad": "quads",
    "quads": "quads",
    "hamstring": "hamstrings",
    "hamstrings": "hamstrings",
    "calf": "calves",
    "calves": "calves",
    # Patterns
    "push": "push",
    "pull": "pull",
    # Meta
    "cardio": "cardio",
    "rest": "rest",
}


def _tokenize_split_value(raw: str) -> list[str]:
    value = (raw or "").strip().lower()
    if not value:
        return []

    value = value.replace("&", " and ").replace("/", " and ")
    value = re.sub(r"[^a-z0-9_\s]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return []

    parts: list[str] = []
    for chunk in value.split(" and "):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts.extend([p.strip() for p in chunk.split(",") if p.strip()])
    return parts


def _normalize_split_tags(values: List[str]) -> List[str]:
    out: list[str] = []
    seen: set[str] = set()

    for v in values or []:
        for token in _tokenize_split_value(str(v)):
            token = token.replace(" ", "_")
            token = re.sub(r"_+", "_", token).strip("_")
            if not token:
                continue

            canonical = _CANONICAL_SPLIT_TAGS.get(token)
            if not canonical:
                # Unknown values are allowed but normalized for matching (snake_case).
                canonical = token

            if canonical not in seen:
                out.append(canonical)
                seen.add(canonical)

    if not out:
        return ["rest"]

    # "rest" is exclusive if any other tags exist.
    if "rest" in seen and len(out) > 1:
        out = [t for t in out if t != "rest"]

    return out[:8]


class WeeklySplit(BaseModel):
    """Weekly training split, stored as JSONB on `profiles.weekly_split`."""

    model_config = ConfigDict(extra="forbid")

    monday: List[str] = Field(default_factory=lambda: ["rest"])
    tuesday: List[str] = Field(default_factory=lambda: ["rest"])
    wednesday: List[str] = Field(default_factory=lambda: ["rest"])
    thursday: List[str] = Field(default_factory=lambda: ["rest"])
    friday: List[str] = Field(default_factory=lambda: ["rest"])
    saturday: List[str] = Field(default_factory=lambda: ["rest"])
    sunday: List[str] = Field(default_factory=lambda: ["rest"])

    @field_validator(*_DAY_FIELDS, mode="before")
    @classmethod
    def _normalize_day(cls, v: Any) -> List[str]:
        if v is None:
            return ["rest"]
        if isinstance(v, str):
            return _normalize_split_tags([v])
        if isinstance(v, list):
            return _normalize_split_tags([str(x) for x in v])
        return _normalize_split_tags([str(v)])


class UserProfileRead(BaseModel):
    """Read model for rows from the `profiles` table."""

    model_config = ConfigDict(extra="ignore")

    id: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    restrictions: Optional[str] = None
    activity: Optional[str] = None
    diet: Optional[str] = None
    preferences_json: Dict[str, Any] = Field(default_factory=dict)

    weekly_split: Optional[WeeklySplit] = None
    privacy_level: PrivacyLevel = "friends"

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserProfileUpdate(BaseModel):
    """Partial update model for `profiles`."""

    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    restrictions: Optional[str] = None
    activity: Optional[str] = None
    diet: Optional[str] = None
    preferences_json: Optional[Dict[str, Any]] = None

    weekly_split: Optional[WeeklySplit] = None
    privacy_level: Optional[PrivacyLevel] = None


class FriendConnection(BaseModel):
    """Represents a row in `friend_connections`."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    requester_id: str
    addressee_id: str
    status: FriendStatus = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GuildSettings(BaseModel):
    """Represents a row in `guild_settings`."""

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    guild_id: str
    default_privacy: PrivacyLevel = "friends"
    features_enabled: Dict[str, bool] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LLMProviderConfig(BaseModel):
    """Decrypted BYOK config for initializing OpenAI-compatible clients."""

    model_config = ConfigDict(extra="ignore")

    owner_id: str
    owner_type: OwnerType = "user"
    provider: LLMProvider = "openai"
    base_url: Optional[str] = None
    api_key: Optional[SecretStr] = None
    model_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_api_config(self) -> Dict[str, str]:
        """Return an `api_config` dict compatible with `BaseAgent(api_config=...)`."""
        return {
            "base_url": (self.base_url or "").rstrip("/"),
            "api_key": self.api_key.get_secret_value() if self.api_key else "",
            "model": self.model_name or "",
        }

