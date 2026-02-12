from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set


def _parse_int_set(value: str) -> Set[int]:
    items = set()
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        items.add(int(part))
    return items


@dataclass(frozen=True)
class DiscordBotConfig:
    token: str
    allowed_channel_ids: Set[int]
    allowed_user_ids: Set[int]
    # Optional: limit command sync to a single guild for fast dev iteration
    guild_id: Optional[int]
    # Where to store per-user profiles inside the container
    profile_dir: Path

    @staticmethod
    def from_env() -> "DiscordBotConfig":
        token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN is required")

        allowed_channel_ids = _parse_int_set(
            os.environ.get("DISCORD_ALLOWED_CHANNEL_IDS", "")
        )
        allowed_user_ids = _parse_int_set(os.environ.get("DISCORD_ALLOWED_USER_IDS", ""))

        guild_id_raw = os.environ.get("DISCORD_GUILD_ID", "").strip()
        guild_id = int(guild_id_raw) if guild_id_raw else None

        profile_dir = Path(os.environ.get("HEALTH_BUTLER_PROFILE_DIR", "/data/profiles"))

        return DiscordBotConfig(
            token=token,
            allowed_channel_ids=allowed_channel_ids,
            allowed_user_ids=allowed_user_ids,
            guild_id=guild_id,
            profile_dir=profile_dir,
        )

    def is_channel_allowed(self, channel_id: int) -> bool:
        # If allowlist is empty, allow all (dev-friendly default)
        return (not self.allowed_channel_ids) or (channel_id in self.allowed_channel_ids)

    def is_user_allowed(self, user_id: int) -> bool:
        # If allowlist is empty, allow all (dev-friendly default)
        return (not self.allowed_user_ids) or (user_id in self.allowed_user_ids)

