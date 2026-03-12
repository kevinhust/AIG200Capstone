"""
MET (Metabolic Equivalent of Task) Mapping Module.

Provides scientific calorie calculation based on the Compendium of Physical Activities.
MET represents the energy cost of an activity as a multiple of resting metabolic rate.

Formula: Calories = MET × Weight(kg) × Duration(hours)

Reference: Ainsworth et al. (2011) Compendium of Physical Activities
https://sites.google.com/site/compendiumofphysicalactivities/
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExerciseProfile:
    """Scientific profile for an exercise."""
    met_value: float
    intensity: str  # "low", "moderate", "high"
    equipment_type: str  # "bodyweight", "dumbbell", "barbell", "machine", "cable", "other"
    primary_muscles: List[str]
    category: str


# ============================================================================
# MET REFERENCE TABLE
# Based on Compendium of Physical Activities (Ainsworth et al., 2011)
# ============================================================================

# Format: "keyword_pattern": (MET, intensity_category)
# Intensity categories: low (<3.0), moderate (3.0-6.0), high (>6.0)

MET_REFERENCE: Dict[str, Tuple[float, str]] = {
    # === STRETCHING & YOGA (Low Intensity) ===
    "yoga": (2.5, "low"),
    "hatha yoga": (2.5, "low"),
    "stretch": (2.3, "low"),
    "stretching": (2.3, "low"),
    "flexibility": (2.3, "low"),
    "pilates": (3.0, "moderate"),
    "tai chi": (3.0, "moderate"),

    # === WALKING (Low to Moderate) ===
    "walking": (3.5, "moderate"),
    "walk": (3.5, "moderate"),
    "brisk walk": (4.3, "moderate"),
    "power walk": (5.0, "moderate"),
    "incline walk": (5.3, "moderate"),
    "treadmill walk": (3.5, "moderate"),

    # === RUNNING & JOGGING (High Intensity) ===
    "running": (9.8, "high"),
    "run": (9.8, "high"),
    "jogging": (7.0, "high"),
    "jog": (7.0, "high"),
    "sprint": (15.0, "high"),
    "treadmill run": (9.8, "high"),

    # === CYCLING (Moderate to High) ===
    "cycling": (5.8, "moderate"),
    "bike": (5.8, "moderate"),
    "stationary bike": (5.5, "moderate"),
    "spinning": (8.5, "high"),
    "bicycle": (5.8, "moderate"),

    # === SWIMMING (Moderate to High) ===
    "swimming": (6.0, "high"),
    "swim": (6.0, "high"),
    "freestyle": (7.0, "high"),
    "breaststroke": (7.0, "high"),
    "backstroke": (6.0, "high"),
    "water aerobics": (4.0, "moderate"),

    # === STRENGTH TRAINING - BODYWEIGHT ===
    "push up": (8.0, "high"),
    "push-up": (8.0, "high"),
    "pushup": (8.0, "high"),
    "pull up": (8.0, "high"),
    "pull-up": (8.0, "high"),
    "chin up": (8.0, "high"),
    "dip": (8.0, "high"),
    "tricep dip": (8.0, "high"),
    "squat": (5.0, "moderate"),
    "bodyweight squat": (5.0, "moderate"),
    "lunge": (4.0, "moderate"),
    "split squat": (5.0, "moderate"),
    "plank": (3.0, "moderate"),
    "crunch": (3.0, "moderate"),
    "sit up": (3.8, "moderate"),
    "sit-up": (3.8, "moderate"),
    "burpee": (10.0, "high"),
    "mountain climber": (8.0, "high"),
    "jump squat": (10.0, "high"),
    "box jump": (9.0, "high"),
    "jumping jack": (8.0, "high"),
    "bear walk": (5.0, "moderate"),
    "bear crawl": (5.0, "moderate"),

    # === STRENGTH TRAINING - WEIGHTED ===
    "bench press": (6.0, "moderate"),
    "deadlift": (6.0, "moderate"),
    "squat (weighted)": (6.0, "moderate"),
    "barbell squat": (6.0, "moderate"),
    "shoulder press": (5.0, "moderate"),
    "overhead press": (5.0, "moderate"),
    "bicep curl": (3.5, "moderate"),
    "curl": (3.5, "moderate"),
    "tricep extension": (3.5, "moderate"),
    "lateral raise": (3.0, "moderate"),
    "row": (4.5, "moderate"),
    "lat pulldown": (4.5, "moderate"),
    "chest fly": (4.0, "moderate"),
    "leg press": (5.0, "moderate"),
    "leg curl": (4.0, "moderate"),
    "leg extension": (4.0, "moderate"),
    "calf raise": (3.5, "moderate"),

    # === HIIT & CARDIO ===
    "hiit": (10.0, "high"),
    "tabata": (11.0, "high"),
    "crossfit": (9.0, "high"),
    "circuit training": (8.0, "high"),
    "interval training": (9.0, "high"),
    "boot camp": (8.0, "high"),
    "kettlebell": (8.0, "high"),
    "battle rope": (9.0, "high"),

    # === CORE & ABS ===
    "ab": (3.5, "moderate"),
    "abs": (3.5, "moderate"),
    "core": (3.5, "moderate"),
    "leg raise": (3.5, "moderate"),
    "russian twist": (3.5, "moderate"),
    "v-up": (4.0, "moderate"),

    # === ATHLETIC & SPORTS ===
    "boxing": (9.0, "high"),
    "kickboxing": (10.0, "high"),
    "mma": (10.0, "high"),
    "martial art": (8.0, "high"),
    "jump rope": (11.0, "high"),
    "skipping": (11.0, "high"),
    "basketball": (6.5, "high"),
    "soccer": (7.0, "high"),
    "tennis": (7.3, "high"),
    "badminton": (5.5, "moderate"),
    "volleyball": (4.0, "moderate"),
    "golf": (4.3, "moderate"),

    # === RECOVERY & COOL DOWN ===
    "foam roll": (2.0, "low"),
    "massage": (1.5, "low"),
    "meditation": (1.0, "low"),
    "breathing": (1.0, "low"),
    "cool down": (2.5, "low"),
    "warm up": (3.5, "moderate"),

    # === FUNCTIONAL TRAINING ===
    "farmer walk": (5.0, "moderate"),
    "farmer's walk": (5.0, "moderate"),
    "turkish get up": (4.0, "moderate"),
    "clean": (6.0, "moderate"),
    "snatch": (6.0, "moderate"),
    "thruster": (7.0, "high"),
    "wall ball": (8.0, "high"),
}

# Equipment type mapping based on keywords
EQUIPMENT_KEYWORDS: Dict[str, str] = {
    "bodyweight": "bodyweight",
    "body weight": "bodyweight",
    "none": "bodyweight",
    "no equipment": "bodyweight",
    "dumbbell": "dumbbell",
    "dumbell": "dumbbell",
    "barbell": "barbell",
    "bar": "barbell",
    "kettlebell": "kettlebell",
    "cable": "cable",
    "machine": "machine",
    "smith": "machine",
    "resistance band": "band",
    "band": "band",
    "medicine ball": "ball",
    "stability ball": "ball",
    "swiss ball": "ball",
    "bosu": "ball",
    "pull up bar": "bar",
    "pull-up bar": "bar",
    "dip station": "bar",
    "bench": "bench",
    "rack": "rack",
}

# Muscle group mapping
MUSCLE_GROUPS: Dict[str, str] = {
    # Chest
    "pectoralis": "chest",
    "chest": "chest",
    "pec": "chest",

    # Back
    "latissimus": "back",
    "trapezius": "back",
    "rhomboid": "back",
    "back": "back",

    # Shoulders
    "deltoid": "shoulders",
    "shoulder": "shoulders",

    # Arms
    "bicep": "arms",
    "tricep": "arms",
    "brachialis": "arms",
    "forearm": "arms",

    # Core
    "abdominis": "core",
    "oblique": "core",
    "core": "core",
    "abs": "core",

    # Legs
    "quadricep": "legs",
    "quad": "legs",
    "hamstring": "legs",
    "glute": "legs",
    "gluteus": "legs",
    "calf": "legs",
    "gastrocnemius": "legs",
    "soleus": "legs",
    "leg": "legs",
    "thigh": "legs",

    # Full body
    "full body": "full_body",
    "total body": "full_body",
}


def get_met_for_exercise(name: str, category: str = "", tags: List[str] = None) -> Tuple[float, str]:
    """
    Get MET value and intensity for an exercise using keyword matching.

    Args:
        name: Exercise name
        category: Exercise category (e.g., "Chest", "Back")
        tags: List of tags/muscles associated with the exercise

    Returns:
        Tuple of (met_value, intensity)
    """
    if tags is None:
        tags = []

    name_lower = name.lower()
    category_lower = category.lower()
    all_text = f"{name_lower} {category_lower} {' '.join(str(t).lower() for t in tags)}"

    # 1. Exact name match (highest priority)
    for key, (met, intensity) in MET_REFERENCE.items():
        if key == name_lower:
            return met, intensity

    # 2. Partial name match
    best_match: Optional[Tuple[float, str, int]] = None  # (met, intensity, match_length)

    for key, (met, intensity) in MET_REFERENCE.items():
        if key in name_lower:
            match_length = len(key)
            if best_match is None or match_length > best_match[2]:
                best_match = (met, intensity, match_length)

    if best_match:
        return best_match[0], best_match[1]

    # 3. Category-based inference
    category_met = {
        "cardio": (6.0, "high"),
        "hiit": (10.0, "high"),
        "legs": (5.0, "moderate"),
        "chest": (5.0, "moderate"),
        "back": (5.0, "moderate"),
        "shoulders": (4.5, "moderate"),
        "arms": (4.0, "moderate"),
        "core": (3.5, "moderate"),
        "abs": (3.5, "moderate"),
        "stretching": (2.3, "low"),
        "yoga": (2.5, "low"),
    }

    for cat_key, (met, intensity) in category_met.items():
        if cat_key in category_lower:
            return met, intensity

    # 4. Tag-based inference
    for tag in tags:
        tag_lower = str(tag).lower()
        for key, (met, intensity) in MET_REFERENCE.items():
            if key in tag_lower:
                return met, intensity

    # 5. Default to moderate intensity
    logger.debug(f"No MET match found for '{name}', defaulting to 3.5 (moderate)")
    return 3.5, "moderate"


def get_equipment_type(tags: List[str], name: str = "") -> str:
    """
    Determine equipment type from tags and name.

    Args:
        tags: List of equipment/muscle tags
        name: Exercise name

    Returns:
        Equipment type string
    """
    all_text = f"{name.lower()} {' '.join(str(t).lower() for t in tags)}"

    # Check for bodyweight first
    bodyweight_indicators = ["bodyweight", "body weight", "none (bodyweight", "no equipment"]
    for indicator in bodyweight_indicators:
        if indicator in all_text:
            return "bodyweight"

    # Check for specific equipment
    for keyword, equipment in EQUIPMENT_KEYWORDS.items():
        if keyword in all_text:
            return equipment

    return "other"


def get_primary_muscles(tags: List[str], category: str = "") -> List[str]:
    """
    Extract primary muscle groups from tags and category.

    Args:
        tags: List of muscle/equipment tags
        category: Exercise category

    Returns:
        List of primary muscle groups
    """
    muscles = []
    all_text = f"{category.lower()} {' '.join(str(t).lower() for t in tags)}"

    for keyword, muscle in MUSCLE_GROUPS.items():
        if keyword in all_text and muscle not in muscles:
            muscles.append(muscle)

    # Category fallback
    if not muscles and category:
        cat_lower = category.lower()
        if cat_lower in ["chest", "back", "shoulders", "arms", "legs", "core", "abs"]:
            muscles.append(cat_lower)

    return muscles if muscles else ["general"]


def calculate_calories(met: float, weight_kg: float, duration_min: float) -> float:
    """
    Calculate calories burned using the MET formula.

    Formula: Calories = MET × Weight(kg) × Duration(hours)

    Args:
        met: MET value of the exercise
        weight_kg: User's weight in kilograms
        duration_min: Duration in minutes

    Returns:
        Estimated calories burned
    """
    if met <= 0 or weight_kg <= 0 or duration_min <= 0:
        return 0.0

    duration_hours = duration_min / 60.0
    calories = met * weight_kg * duration_hours

    return round(calories, 1)


def get_exercise_profile(name: str, category: str = "", tags: List[str] = None) -> ExerciseProfile:
    """
    Get complete scientific profile for an exercise.

    Args:
        name: Exercise name
        category: Exercise category
        tags: List of tags

    Returns:
        ExerciseProfile with MET, intensity, equipment, and muscles
    """
    if tags is None:
        tags = []

    met_value, intensity = get_met_for_exercise(name, category, tags)
    equipment_type = get_equipment_type(tags, name)
    primary_muscles = get_primary_muscles(tags, category)

    return ExerciseProfile(
        met_value=met_value,
        intensity=intensity,
        equipment_type=equipment_type,
        primary_muscles=primary_muscles,
        category=category,
    )


def enrich_exercise_data(exercise: Dict) -> Dict:
    """
    Enrich an exercise dictionary with scientific attributes.

    Args:
        exercise: Exercise dict with 'name', 'category', 'tags'

    Returns:
        Enriched exercise dict with met_value, intensity, equipment_type, primary_muscles
    """
    name = exercise.get("name", "")
    category = exercise.get("category", "")
    tags = exercise.get("tags", [])

    profile = get_exercise_profile(name, category, tags)

    enriched = exercise.copy()
    enriched["met_value"] = profile.met_value
    enriched["intensity"] = profile.intensity
    enriched["equipment_type"] = profile.equipment_type
    enriched["primary_muscles"] = profile.primary_muscles

    return enriched


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def batch_enrich_exercises(exercises: List[Dict], verbose: bool = True) -> List[Dict]:
    """
    Enrich a list of exercises with scientific attributes.

    Args:
        exercises: List of exercise dictionaries
        verbose: Whether to log progress

    Returns:
        List of enriched exercise dictionaries
    """
    enriched = []

    # Statistics tracking
    intensity_counts = {"low": 0, "moderate": 0, "high": 0}
    equipment_counts: Dict[str, int] = {}

    for ex in exercises:
        enriched_ex = enrich_exercise_data(ex)
        enriched.append(enriched_ex)

        # Update stats
        intensity_counts[enriched_ex["intensity"]] += 1
        eq = enriched_ex["equipment_type"]
        equipment_counts[eq] = equipment_counts.get(eq, 0) + 1

    if verbose:
        logger.info(f"✅ Enriched {len(enriched)} exercises")
        logger.info(f"   Intensity: {intensity_counts}")
        logger.info(f"   Equipment: {equipment_counts}")

    return enriched
