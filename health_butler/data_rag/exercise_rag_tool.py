"""
Exercise RAG Tool for semantic search over exercise database.

Provides semantic search for exercises based on user constraints (MET values, 
contraindications, equipment, intensity) using ChromaDB vector database.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ExerciseRagTool:
    """
    RAG tool for exercise data using ChromaDB for semantic search.
    Provides MET values for calorie calculations and filters by user constraints.
    """
    
    def __init__(
        self, 
        db_path: str = "health_butler/data/chroma_db",
        collection_name: str = "exercise_data"
    ):
        """
        Initialize Exercise RAG Tool.
        
        Args:
            db_path: Path to ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection for exercises
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize embedding function (same as nutrition RAG for consistency)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            path_obj = Path(self.db_path)
            path_obj.mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.ef
            )
            logger.info(f"Connected to ChromaDB at {self.db_path}, collection: {self.collection_name}")
            logger.info(f"Exercise collection count: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB for exercises: {e}")
            raise e
    
    def query_exercises(
        self,
        query_text: str,
        top_k: int = 5,
        category: Optional[str] = None,
        intensity: Optional[Literal["light", "moderate", "vigorous"]] = None,
        equipment: Optional[List[str]] = None,
        exclude_contraindications: Optional[List[str]] = None,
        min_met: Optional[float] = None,
        max_met: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant exercises using semantic search with optional filtering.
        
        Args:
            query_text: Natural language query (e.g., "low impact cardio")
            top_k: Number of results to return
            category: Filter by category (cardio, strength, flexibility, sports, daily)
            intensity: Filter by intensity level
            equipment: List of available equipment (filters to matching exercises)
            exclude_contraindications: Health limitations to avoid (e.g., ["knee_injury"])
            min_met: Minimum MET value
            max_met: Maximum MET value
            
        Returns:
            List of exercise dictionaries with text, metadata, and MET values
        """
        logger.info(f"Exercise RAG Query: {query_text}")
        
        # Build where clause for metadata filtering
        where_conditions = {}
        
        if category:
            where_conditions["category"] = category
        
        if intensity:
            where_conditions["intensity"] = intensity
        
        # Note: ChromaDB doesn't support complex queries like "contraindication NOT IN list"
        # We'll filter these post-query
        
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k * 2,  # Get more to allow post-filtering
                where=where_conditions if where_conditions else None
            )
            
            # Format and post-filter results
            formatted_results = []
            if results['documents']:
                for i in range(len(results['documents'][0])):
                    exercise = {
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "id": results['ids'][0][i],
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    }
                    
                    # Apply post-query filters
                    if not self._passes_filters(
                        exercise,
                        equipment=equipment,
                        exclude_contraindications=exclude_contraindications,
                        min_met=min_met,
                        max_met=max_met
                    ):
                        continue
                    
                    formatted_results.append(exercise)
                    
                    # Stop when we have enough results
                    if len(formatted_results) >= top_k:
                        break
            
            logger.info(f"Returned {len(formatted_results)} exercises after filtering")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Exercise query failed: {e}")
            return []
    
    def _passes_filters(
        self,
        exercise: Dict[str, Any],
        equipment: Optional[List[str]],
        exclude_contraindications: Optional[List[str]],
        min_met: Optional[float],
        max_met: Optional[float]
    ) -> bool:
        """
        Check if exercise passes all filter criteria.
        
        Args:
            exercise: Exercise dictionary with metadata
            equipment: Required equipment list
            exclude_contraindications: Health limitations to avoid
            min_met: Minimum MET value
            max_met: Maximum MET value
            
        Returns:
            True if exercise passes all filters
        """
        metadata = exercise.get("metadata", {})
        
        # Equipment filter: exercise equipment must be in user's available equipment
        if equipment:
            exercise_equipment = metadata.get("equipment", "none")
            if exercise_equipment not in equipment and exercise_equipment != "none":
                return False
        
        # Contraindication filter: reject if exercise has user's limitations
        if exclude_contraindications:
            exercise_contraindications = metadata.get("contraindications", [])
            if isinstance(exercise_contraindications, str):
                exercise_contraindications = [exercise_contraindications]
            
            # Check if any user limitation is in exercise contraindications
            for limitation in exclude_contraindications:
                if limitation in exercise_contraindications:
                    logger.debug(f"Filtered out {metadata.get('activity')} due to {limitation}")
                    return False
        
        # MET value range filter
        met_value = metadata.get("met_value", 0.0)
        if isinstance(met_value, (int, float)):
            if min_met and met_value < min_met:
                return False
            if max_met and met_value > max_met:
                return False
        
        return True
    
    def get_exercise_by_id(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific exercise by its ID.
        
        Args:
            exercise_id: Unique exercise identifier
            
        Returns:
            Exercise dictionary or None if not found
        """
        try:
            result = self.collection.get(ids=[exercise_id])
            if result['documents']:
                return {
                    "text": result['documents'][0],
                    "metadata": result['metadatas'][0] if result['metadatas'] else {},
                    "id": result['ids'][0]
                }
        except Exception as e:
            logger.error(f"Failed to get exercise by ID {exercise_id}: {e}")
        
        return None
    
    def calculate_calorie_burn(
        self,
        met_value: float,
        weight_kg: float,
        duration_minutes: int
    ) -> float:
        """
        Calculate calories burned for an exercise.
        
        Formula: Calories = MET × weight(kg) × duration(hours)
        
        Args:
            met_value: Metabolic Equivalent of Task value
            weight_kg: User's weight in kilograms
            duration_minutes: Exercise duration in minutes
            
        Returns:
            Estimated calories burned
        """
        duration_hours = duration_minutes / 60.0
        calories = met_value * weight_kg * duration_hours
        return round(calories, 1)
    
    def suggest_duration_for_calories(
        self,
        met_value: float,
        weight_kg: float,
        target_calories: float
    ) -> int:
        """
        Suggest exercise duration to burn target calories.
        
        Args:
            met_value: Metabolic Equivalent of Task value
            weight_kg: User's weight in kilograms
            target_calories: Target calories to burn
            
        Returns:
            Suggested duration in minutes
        """
        if met_value == 0 or weight_kg == 0:
            return 0
        
        duration_hours = target_calories / (met_value * weight_kg)
        duration_minutes = int(duration_hours * 60)
        
        # Round to nearest 5 minutes for practicality
        duration_minutes = max(5, round(duration_minutes / 5) * 5)
        
        return duration_minutes
    
    def add_exercises(self, exercises: List[Dict[str, Any]]) -> None:
        """
        Add exercise documents to the vector database.
        
        Expected format:
        [{
            "text": "Running at 6 mph burns 9.8 METs...",
            "metadata": {
                "activity": "running_6mph",
                "met_value": 9.8,
                "category": "cardio",
                ...
            },
            "id": "exercise_001"
        }]
        
        Args:
            exercises: List of exercise dictionaries to add
        """
        if not exercises:
            return
        
        texts = [ex['text'] for ex in exercises]
        metadatas = [ex.get('metadata', {}) for ex in exercises]
        ids = [ex.get('id', str(hash(ex['text']))) for ex in exercises]
        
        try:
            self.collection.upsert(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Upserted {len(exercises)} exercises to ChromaDB")
        except Exception as e:
            logger.error(f"Failed to add exercises: {e}")
            raise


# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    tool = ExerciseRagTool()
    
    # Test adding sample exercise if collection is empty
    if tool.collection.count() == 0:
        sample_exercises = [
            {
                "text": "Brisk walking at 3.5 mph burns 4.3 METs. Low-impact cardiovascular exercise suitable for beginners and people with joint issues.",
                "metadata": {
                    "activity": "walking_brisk_3.5mph",
                    "met_value": 4.3,
                    "category": "cardio",
                    "intensity": "moderate",
                    "contraindications": [],
                    "equipment": "none",
                    "muscle_groups": ["legs", "core"]
                },
                "id": "walking_brisk"
            },
            {
                "text": "Running at 6 mph burns 9.8 METs. High-intensity cardiovascular exercise. Not recommended for people with knee or joint problems.",
                "metadata": {
                    "activity": "running_6mph",
                    "met_value": 9.8,
                    "category": "cardio",
                    "intensity": "vigorous",
                    "contraindications": ["knee_injury", "ankle_injury", "severe_obesity"],
                    "equipment": "none",
                    "muscle_groups": ["legs", "core", "cardiovascular"]
                },
                "id": "running_6mph"
            },
            {
                "text": "Swimming laps (moderate effort) burns 5.8 METs. Full-body low-impact exercise excellent for people with joint issues.",
                "metadata": {
                    "activity": "swimming_moderate",
                    "met_value": 5.8,
                    "category": "cardio",
                    "intensity": "moderate",
                    "contraindications": [],
                    "equipment": "pool",
                    "muscle_groups": ["full_body", "cardiovascular"]
                },
                "id": "swimming_moderate"
            }
        ]
        
        tool.add_exercises(sample_exercises)
        print(f"Added {len(sample_exercises)} sample exercises")
    
    # Test query without filters
    print("\n--- Test 1: Basic cardio query ---")
    results = tool.query_exercises("cardio exercises", top_k=3)
    for r in results:
        print(f"- {r['metadata'].get('activity')}: {r['metadata'].get('met_value')} METs")
    
    # Test query with contraindication filter
    print("\n--- Test 2: Cardio for user with knee injury ---")
    results = tool.query_exercises(
        "cardio exercises",
        top_k=3,
        exclude_contraindications=["knee_injury"]
    )
    for r in results:
        print(f"- {r['metadata'].get('activity')}: {r['metadata'].get('met_value')} METs")
    
    # Test calorie calculation
    print("\n--- Test 3: Calorie burn calculation ---")
    calories = tool.calculate_calorie_burn(met_value=4.3, weight_kg=75, duration_minutes=30)
    print(f"Brisk walking (4.3 METs) for 30 min at 75kg: {calories} calories")
    
    # Test duration suggestion
    print("\n--- Test 4: Duration to burn 300 calories ---")
    duration = tool.suggest_duration_for_calories(met_value=4.3, weight_kg=75, target_calories=300)
    print(f"Duration needed: {duration} minutes")
