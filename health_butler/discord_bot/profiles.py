from __future__ import annotations

from pathlib import Path

from health_butler.data.user_profiles import UserProfile


def profile_path_for_user(profile_dir: Path, discord_user_id: int) -> Path:
    """
    Map a Discord user to a profile path.

    We store one JSON per Discord user for demo privacy/isolation.
    """
    return profile_dir / f"{discord_user_id}.json"


def load_profile(profile_dir: Path, discord_user_id: int) -> UserProfile:
    path = profile_path_for_user(profile_dir, discord_user_id)
    return UserProfile.load_from_disk(path)


def save_profile(profile_dir: Path, profile: UserProfile, discord_user_id: int) -> None:
    path = profile_path_for_user(profile_dir, discord_user_id)
    profile.user_id = str(discord_user_id)
    profile.save_to_disk(path)

