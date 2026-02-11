"""
User Profile Management System for Health Butler AI.

Manages user health profiles with local JSON persistence for privacy-first approach.
Stores age, weight, fitness level, health limitations, goals, and exercise preferences.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Default storage location in user's home directory
DEFAULT_PROFILE_DIR = Path.home() / ".health_butler"
DEFAULT_PROFILE_PATH = DEFAULT_PROFILE_DIR / "user_profile.json"


class FitnessGoal(BaseModel):
    """Represents a SMART fitness goal with tracking capabilities."""
    
    goal_id: str = Field(description="Unique identifier for the goal")
    goal_type: Literal["weight_loss", "muscle_gain", "endurance", "consistency", "custom"] = Field(
        description="Type of fitness goal"
    )
    description: str = Field(description="Human-readable goal description")
    target_value: float = Field(description="Numeric target (e.g., 5 for 5kg loss)")
    current_value: float = Field(default=0.0, description="Current progress value")
    unit: str = Field(description="Unit of measurement (kg, km, days, etc.)")
    deadline: datetime = Field(description="Goal completion deadline")
    created_at: datetime = Field(default_factory=datetime.now)
    completed: bool = Field(default=False)
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.target_value == 0:
            return 0.0
        return min((self.current_value / self.target_value) * 100, 100.0)
    
    @property
    def days_remaining(self) -> int:
        """Calculate days remaining until deadline."""
        return max((self.deadline - datetime.now()).days, 0)
    
    @property
    def is_on_track(self) -> bool:
        """Determine if goal is on track based on time passed vs progress made."""
        total_days = (self.deadline - self.created_at).days
        days_passed = (datetime.now() - self.created_at).days
        
        if total_days == 0:
            return self.completed
        
        expected_progress = (days_passed / total_days) * 100
        return self.progress_percent >= expected_progress * 0.9  # 90% threshold
    
    def update_progress(self, new_value: float) -> None:
        """Update current progress value."""
        self.current_value = new_value
        if self.current_value >= self.target_value:
            self.completed = True


class UserProfile(BaseModel):
    """
    User health profile with personal attributes, fitness goals, and exercise preferences.
    Stored locally on user's device for privacy.
    """
    
    user_id: str = Field(default="default_user", description="User identifier")
    
    # Basic health information
    age: int = Field(ge=1, le=120, description="User age in years")
    weight_kg: float = Field(gt=0, le=500, description="User weight in kilograms")
    height_cm: Optional[float] = Field(default=None, gt=0, le=300, description="User height in cm")
    sex: Optional[Literal["male", "female", "other"]] = Field(default=None)
    
    # Fitness level
    fitness_level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Self-assessed fitness level"
    )
    
    # Health limitations and constraints
    health_limitations: List[str] = Field(
        default_factory=list,
        description="List of health limitations (e.g., 'knee_injury', 'high_blood_pressure')"
    )
    
    # Available equipment and context
    available_equipment: List[str] = Field(
        default_factory=lambda: ["none"],
        description="Available exercise equipment (e.g., 'home', 'gym', 'outdoor')"
    )
    
    # Fitness goals
    fitness_goals: List[FitnessGoal] = Field(
        default_factory=list,
        description="Active and completed fitness goals"
    )
    
    # Exercise preference tracking (activity_name -> completion_count)
    exercise_preferences: Dict[str, int] = Field(
        default_factory=dict,
        description="Exercise completion frequency for preference learning"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @field_validator("health_limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, v):
        """Normalize health limitations to lowercase with underscores."""
        if isinstance(v, list):
            return [lim.lower().replace(" ", "_") for lim in v]
        return v
    
    @property
    def active_goals(self) -> List[FitnessGoal]:
        """Get list of active (not completed) goals."""
        return [goal for goal in self.fitness_goals if not goal.completed]
    
    @property
    def bmi(self) -> Optional[float]:
        """Calculate BMI if height is available."""
        if self.height_cm:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None
    
    def add_goal(self, goal: FitnessGoal) -> None:
        """Add a new fitness goal."""
        self.fitness_goals.append(goal)
        self.last_updated = datetime.now()
    
    def increment_exercise_preference(self, exercise_name: str) -> None:
        """Increment completion count for an exercise."""
        exercise_key = exercise_name.lower().replace(" ", "_")
        self.exercise_preferences[exercise_key] = self.exercise_preferences.get(exercise_key, 0) + 1
        self.last_updated = datetime.now()
    
    def get_top_preferences(self, limit: int = 5) -> List[tuple[str, int]]:
        """Get top N preferred exercises by completion count."""
        sorted_prefs = sorted(
            self.exercise_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_prefs[:limit]
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary for JSON serialization."""
        return self.model_dump(mode="json")
    
    @classmethod
    def from_dict(cls, data: dict) -> UserProfile:
        """Create profile from dictionary."""
        return cls.model_validate(data)
    
    def save_to_disk(self, path: Optional[Path] = None) -> None:
        """
        Save profile to JSON file on local disk.
        
        Args:
            path: Optional custom path. Defaults to ~/.health_butler/user_profile.json
        """
        save_path = path or DEFAULT_PROFILE_PATH
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Update timestamp
        self.last_updated = datetime.now()
        
        # Save to JSON
        try:
            with open(save_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
            logger.info(f"User profile saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            raise
    
    @classmethod
    def load_from_disk(cls, path: Optional[Path] = None) -> UserProfile:
        """
        Load profile from JSON file on local disk.
        
        Args:
            path: Optional custom path. Defaults to ~/.health_butler/user_profile.json
            
        Returns:
            UserProfile instance or new default profile if file doesn't exist
        """
        load_path = path or DEFAULT_PROFILE_PATH
        
        if not load_path.exists():
            logger.info("No existing profile found, creating default profile")
            return cls.create_default()
        
        try:
            with open(load_path, 'r') as f:
                data = json.load(f)
            profile = cls.from_dict(data)
            logger.info(f"User profile loaded from {load_path}")
            return profile
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}. Creating default profile.")
            return cls.create_default()
    
    @classmethod
    def create_default(cls) -> UserProfile:
        """Create a default user profile for first-time users."""
        return cls(
            age=30,
            weight_kg=70.0,
            fitness_level="beginner",
            health_limitations=[],
            available_equipment=["home"]
        )
    
    def export_json(self, export_path: Path) -> None:
        """
        Export profile to a custom location for backup.
        
        Args:
            export_path: Path where to export the profile
        """
        self.save_to_disk(export_path)
        logger.info(f"Profile exported to {export_path}")
    
    @classmethod
    def import_json(cls, import_path: Path) -> UserProfile:
        """
        Import profile from a backup file.
        
        Args:
            import_path: Path to the profile backup
            
        Returns:
            Imported UserProfile instance
        """
        return cls.load_from_disk(import_path)


# Convenience functions for common operations

def get_user_profile(path: Optional[Path] = None) -> UserProfile:
    """
    Get the user profile, loading from disk if available.
    
    Args:
        path: Optional custom profile path
        
    Returns:
        UserProfile instance
    """
    return UserProfile.load_from_disk(path)


def save_user_profile(profile: UserProfile, path: Optional[Path] = None) -> None:
    """
    Save the user profile to disk.
    
    Args:
        profile: UserProfile instance to save
        path: Optional custom save path
    """
    profile.save_to_disk(path)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    # Create a sample profile
    profile = UserProfile(
        user_id="test_user",
        age=28,
        weight_kg=75.0,
        height_cm=175,
        fitness_level="intermediate",
        health_limitations=["knee injury"],
        available_equipment=["home", "outdoor"]
    )
    
    # Add a goal
    goal = FitnessGoal(
        goal_id="goal_1",
        goal_type="weight_loss",
        description="Lose 5kg in 2 months",
        target_value=5.0,
        unit="kg",
        deadline=datetime(2026, 4, 5)
    )
    profile.add_goal(goal)
    
    # Track exercise preferences
    profile.increment_exercise_preference("walking")
    profile.increment_exercise_preference("walking")
    profile.increment_exercise_preference("yoga")
    
    # Save to disk
    profile.save_to_disk()
    
    # Load back
    loaded_profile = UserProfile.load_from_disk()
    print(f"Loaded profile for user: {loaded_profile.user_id}")
    print(f"Active goals: {len(loaded_profile.active_goals)}")
    print(f"Top preferences: {loaded_profile.get_top_preferences()}")
    print(f"BMI: {loaded_profile.bmi}")
