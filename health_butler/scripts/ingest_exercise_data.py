"""
Script to ingest Compendium of Physical Activities data into ChromaDB.

Downloads or loads the Compendium CSV, processes it with metadata enrichment,
and loads it into the exercise_data ChromaDB collection for RAG queries.
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from health_butler.data_rag.exercise_rag_tool import ExerciseRagTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
COMPENDIUM_CSV = DATA_DIR / "compendium_activities.csv"


# Contraindication mappings based on common health conditions
CONTRAINDICATION_MAPPING = {
    # Knee/Joint Issues
    "running": ["knee_injury", "ankle_injury", "severe_arthritis"] ,
    "jogging": ["knee_injury", "ankle_injury", "severe_arthritis"],
    "jump": ["knee_injury", "ankle_injury", "osteoporosis"],
    "basketball": ["knee_injury", "ankle_injury"],
    "soccer": ["knee_injury", "ankle_injury"],
    "tennis": ["knee_injury", "ankle_injury"],
    
    # Cardiovascular Concerns
    "vigorous": ["heart_disease", "uncontrolled_hypertension"],
    "sprinting": ["heart_disease", "uncontrolled_hypertension"],
    
    # Back/Spine Issues
    "heavy lifting": ["back_injury", "herniated_disc"],
    "deadlift": ["back_injury", "herniated_disc"],
    "rowing": ["back_injury"],
    
    # General high-impact
    "high impact": ["osteoporosis", "severe_obesity"],
}


def infer_contraindications(activity_name: str, met_value: float) -> List[str]:
    """
    Infer contraindications based on activity name and MET value.
    
    Args:
        activity_name: Name of the activity
        met_value: MET value of the activity
        
    Returns:
        List of contraindication tags
    """
    contraindications = []
    activity_lower = activity_name.lower()
    
    # Check keyword-based contraindications
    for keyword, limitations in CONTRAINDICATION_MAPPING.items():
        if keyword in activity_lower:
            contraindications.extend(limitations)
    
    # MET-based contraindications (very high intensity)
    if met_value >= 10.0:
        if "heart_disease" not in contraindications:
            contraindications.append("severe_heart_disease")
    
    # Remove duplicates
    return list(set(contraindications))


def categorize_activity(activity_name: str, code: str) -> str:
    """
    Categorize activity into main types.
    
    Args:
        activity_name: Name of the activity
        code: Compendium activity code
        
    Returns:
        Category string (cardio, strength, flexibility, sports, daily)
    """
    activity_lower = activity_name.lower()
    
    # Cardio keywords
    if any(kw in activity_lower for kw in ["walk", "run", "jog", "swim", "cycle", "bike", "cardio", "aerobic"]):
        return "cardio"
    
    # Strength keywords
    if any(kw in activity_lower for kw in ["weight", "lift", "strength", "resistance", "push-up", "pull-up"]):
        return "strength"
    
    # Flexibility keywords
    if any(kw in activity_lower for kw in ["yoga", "stretch", "pilates", "tai chi"]):
        return "flexibility"
    
    # Sports keywords
    if any(kw in activity_lower for kw in ["basketball", "football", "tennis", "soccer", "baseball", "golf", "hockey"]):
        return "sports"
    
    # Daily activities
    if any(kw in activity_lower for kw in ["house", "clean", "garden", "stairs", "shopping", "cook"]):
        return "daily"
    
    # Default to cardio if unclear
    return "cardio"


def determine_intensity(met_value: float) -> str:
    """
    Determine intensity level based on MET value.
    
    MET Ranges (CDC guidelines):
    - Light: < 3.0 METs
    - Moderate: 3.0 - 6.0 METs
    - Vigorous: > 6.0 METs
    
    Args:
        met_value: Metabolic Equivalent value
        
    Returns:
        Intensity level string
    """
    if met_value < 3.0:
        return "light"
    elif met_value <= 6.0:
        return "moderate"
    else:
        return "vigorous"


def determine_equipment(activity_name: str) -> str:
    """
    Determine required equipment based on activity name.
    
    Args:
        activity_name: Name of the activity
        
    Returns:
        Equipment category
    """
    activity_lower = activity_name.lower()
    
    if any(kw in activity_lower for kw in ["gym", "weight", "machine", "treadmill", "elliptical"]):
        return "gym"
    
    if any(kw in activity_lower for kw in ["pool", "swim"]):
        return "pool"
    
    if any(kw in activity_lower for kw in ["bike", "cycle"]) and "stationary" not in activity_lower:
        return "outdoor"
    
    if any(kw in activity_lower for kw in ["outdoor", "trail", "field"]):
        return "outdoor"
    
    # Default to none (bodyweight/home)
    return "none"


def create_sample_dataset() -> List[Dict[str, Any]]:
    """
    Create a sample exercise dataset for testing when Compendium CSV is not available.
    
    Returns:
        List of exercise documents
    """
    logger.info("Creating sample exercise dataset (Compendium CSV not found)")
    
    sample_data = [
        ("Walking, 2.0 mph, slow pace", 2.0, "01010"),
        ("Walking, 3.0 mph, moderate pace", 3.5, "01030"),
        ("Walking, 3.5 mph, brisk pace", 4.3, "01040"),
        ("Walking, 4.0 mph, very brisk pace", 5.0, "01050"),
        ("Jogging, general", 7.0, "12020"),
        ("Running, 5 mph (12 min/mile)", 8.3, "12030"),
        ("Running, 6 mph (10 min/mile)", 9.8, "12040"),
        ("Running, 7 mph (8.5 min/mile)", 11.0, "12050"),
        ("Running, 8 mph (7.5 min/mile)", 11.8, "12060"),
        ("Bicycling, leisure, 5.5 mph", 3.5, "01015"),
        ("Bicycling, 10-11.9 mph, leisure", 6.8, "01020"),
        ("Bicycling, 12-13.9 mph, moderate effort", 8.0, "01030"),
        ("Swimming, leisurely, not lap swimming", 6.0, "18200"),
        ("Swimming, crawl, fast, vigorous effort", 10.0, "18310"),
        ("Swimming, backstroke, general", 7.0, "18320"),
        ("Swimming, breaststroke, general", 10.3, "18330"),
        ("Yoga, Hatha", 2.5, "02100"),
        ("Yoga, Power", 4.0, "02101"),
        ("Pilates, general", 3.0, "02120"),
        ("Stretching, mild", 2.3, "02200"),
        ("Weight lifting, light or moderate effort", 3.0, "02050"),
        ("Weight lifting, vigorous effort", 6.0, "02052"),
        ("Push-ups, vigorous effort", 8.0, "02064"),
        ("Sit-ups, vigorous effort", 8.0, "02070"),
        ("Jumping jacks, vigorous", 8.0, "02090"),
        ("Elliptical trainer, moderate effort", 5.0, "02048"),
        ("Stair climbing, general", 8.8, "02065"),
        ("Basketball, game", 8.0, "15010"),
        ("Basketball, shooting baskets", 4.5, "15020"),
        ("Tennis, singles", 8.0, "15675"),
        ("Tennis, doubles", 6.0, "15680"),
        ("Soccer, general", 7.0, "15600"),
        ("Golf, walking and carrying clubs", 4.3, "15240"),
        ("Golf, using power cart", 3.5, "15250"),
        ("Dancing, aerobic, ballet or modern", 6.1, "03015"),
        ("Dancing, ballroom, fast (disco, folk, square)", 5.5, "03022"),
        ("Dancing, ballroom, slow (waltz, foxtrot, tango)", 3.0, "03025"),
        ("Gardening, general", 4.0, "08050"),
        ("Mowing lawn, walk power mower", 5.5, "08090"),
        ("Raking lawn", 4.3, "08100"),
        ("Housecleaning, general", 3.3, "05040"),
        ("Cooking or food preparation", 2.5, "05020"),
        ("Shopping, non-grocery", 2.3, "17170"),
        ("Vacuuming", 3.3, "05060"),
        ("Sitting quietly", 1.0, "07010"),
    ]
    
    exercises =[]
    for idx, (activity, met, code) in enumerate(sample_data):
        category = categorize_activity(activity, code)
        intensity = determine_intensity(met)
        equipment = determine_equipment(activity)
        contraindications = infer_contraindications(activity, met)
        
        text = f"{activity} burns {met} METs. {intensity.capitalize()} intensity {category} exercise."
        
        exercise = {
            "text": text,
            "metadata": {
                "activity": activity.lower().replace(", ", "_").replace(" ", "_"),
                "met_value": met,
                "category": category,
                "intensity": intensity,
                "contraindications": contraindications,
                "equipment": equipment,
                "code": code
            },
            "id": f"exercise_{idx:04d}"
        }
        exercises.append(exercise)
    
    return exercises


def load_compendium_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """
    Load and process Compendium of Physical Activities CSV.
    
    Expected CSV columns:
    - CODE: Activity code
    - METS: MET value
    - SPECIFIC MOTION: Activity description
    
    Args:
        csv_path: Path to Compendium CSV file
        
    Returns:
        List of processed exercise documents
    """
    logger.info(f"Loading Compendium CSV from {csv_path}")
    
    exercises = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for idx, row in enumerate(reader):
                # Extract fields (adjust column names based on actual CSV)
                code = row.get('CODE', row.get('code', str(idx)))
                met_value = float(row.get('METS', row.get('mets', row.get('MET', 3.0))))
                activity = row.get('SPECIFIC MOTION', row.get('specific_motion', row.get('ACTIVITY', f'Activity {idx}')))
                
                # Enrich with metadata
                category = categorize_activity(activity, code)
                intensity = determine_intensity(met_value)
                equipment = determine_equipment(activity)
                contraindications = infer_contraindications(activity, met_value)
                
                # Generate descriptive text
                text = f"{activity} burns {met_value} METs. {intensity.capitalize()} intensity {category} exercise."
                if contraindications:
                    text += f" Contraindications: {', '.join(contraindications)}."
                
                exercise = {
                    "text": text,
                    "metadata": {
                        "activity": activity.lower().replace(", ", "_").replace(" ", "_"),
                        "met_value": met_value,
                        "category": category,
                        "intensity": intensity,
                        "contraindications": contraindications,
                        "equipment": equipment,
                        "code": code
                    },
                    "id": f"compendium_{code}_{idx}"
                }
                exercises.append(exercise)
        
        logger.info(f"Loaded {len(exercises)} exercises from Compendium CSV")
        return exercises
    
    except Exception as e:
        logger.error(f"Failed to load Compendium CSV: {e}")
        return []


def main():
    """Main ingestion script."""
    logger.info("Starting exercise data ingestion...")
    
    # Try to load Compendium CSV, fall back to sample data
    if COMPENDIUM_CSV.exists():
        exercises = load_compendium_csv(COMPENDIUM_CSV)
    else:
        logger.warning(f"Compendium CSV not found at {COMPENDIUM_CSV}")
        logger.info("Using sample dataset instead")
        exercises = create_sample_dataset()
    
    if not exercises:
        logger.error("No exercises to ingest!")
        return
    
    # Initialize RAG tool and add exercises
    logger.info("Initializing Exercise RAG Tool...")
    rag_tool = ExerciseRagTool()
    
    logger.info(f"Adding {len(exercises)} exercises to ChromaDB...")
    rag_tool.add_exercises(exercises)
    
    # Verify ingestion
    final_count = rag_tool.collection.count()
    logger.info(f"✓ Ingestion complete! Collection now has {final_count} exercises.")
    
    # Test query
    logger.info("\n--- Testing RAG query ---")
    results = rag_tool.query_exercises("low impact cardio", top_k=3)
    for i, result in enumerate(results, 1):
        logger.info(f"{i}. {result['metadata'].get('activity')}: {result['metadata'].get('met_value')} METs")


if __name__ == "__main__":
    main()
