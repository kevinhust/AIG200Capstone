"""
Unit tests for MET (Metabolic Equivalent of Task) calculation.

Tests:
1. MET value mapping for various exercises
2. Intensity classification
3. Equipment type detection
4. Calorie calculation formula
5. Exercise enrichment
"""

import pytest
from unittest.mock import Mock, patch


class TestMETMapping:
    """Test suite for MET mapping functions."""

    def test_get_met_for_exercise_yoga(self):
        """Test MET mapping for yoga (low intensity)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("Yoga", "Stretching")
        assert met == 2.5
        assert intensity == "low"

    def test_get_met_for_exercise_running(self):
        """Test MET mapping for running (high intensity)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("Running", "Cardio")
        assert met == 9.8
        assert intensity == "high"

    def test_get_met_for_exercise_walking(self):
        """Test MET mapping for walking (moderate intensity)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("Brisk Walking", "Cardio")
        assert met == 4.3
        assert intensity == "moderate"

    def test_get_met_for_exercise_hiit(self):
        """Test MET mapping for HIIT (high intensity)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("HIIT Workout", "Cardio")
        assert met == 10.0
        assert intensity == "high"

    def test_get_met_for_exercise_pushup(self):
        """Test MET mapping for push-ups (high intensity)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("Push Up", "Chest")
        assert met == 8.0
        assert intensity == "high"

    def test_get_met_for_exercise_unknown(self):
        """Test MET mapping for unknown exercise (defaults to moderate)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        met, intensity = get_met_for_exercise("Some Random Exercise 12345", "Other")
        assert met == 3.5  # Default moderate
        assert intensity == "moderate"

    def test_get_met_with_tags(self):
        """Test MET mapping using tags for better matching."""
        from src.data_rag.met_mapping import get_met_for_exercise

        # Tags can help identify the exercise type
        met, intensity = get_met_for_exercise("My Custom Move", "Legs", ["squat", "bodyweight"])
        assert met == 5.0  # Should match "squat"
        assert intensity == "moderate"


class TestEquipmentType:
    """Test suite for equipment type detection."""

    def test_bodyweight_detection(self):
        """Test bodyweight exercise detection."""
        from src.data_rag.met_mapping import get_equipment_type

        equipment = get_equipment_type(["none (bodyweight exercise)", "Chest"], "Push Up")
        assert equipment == "bodyweight"

    def test_dumbbell_detection(self):
        """Test dumbbell equipment detection."""
        from src.data_rag.met_mapping import get_equipment_type

        equipment = get_equipment_type(["Dumbbell", "Bicep"], "Dumbbell Curl")
        assert equipment == "dumbbell"

    def test_barbell_detection(self):
        """Test barbell equipment detection."""
        from src.data_rag.met_mapping import get_equipment_type

        equipment = get_equipment_type(["Barbell", "Legs"], "Barbell Squat")
        assert equipment == "barbell"

    def test_machine_detection(self):
        """Test machine equipment detection."""
        from src.data_rag.met_mapping import get_equipment_type

        equipment = get_equipment_type(["Machine", "Legs"], "Leg Press")
        assert equipment == "machine"

    def test_unknown_equipment(self):
        """Test unknown equipment defaults to 'other'."""
        from src.data_rag.met_mapping import get_equipment_type

        equipment = get_equipment_type(["Some Muscle"], "Unknown Exercise")
        assert equipment == "other"


class TestCalorieCalculation:
    """Test suite for MET-based calorie calculation."""

    def test_calculate_calories_basic(self):
        """Test basic calorie calculation."""
        from src.data_rag.met_mapping import calculate_calories

        # MET 5.0, 70kg person, 30 minutes
        # Formula: 5.0 × 70 × 0.5 = 175 kcal
        calories = calculate_calories(5.0, 70, 30)
        assert calories == 175.0

    def test_calculate_calories_high_intensity(self):
        """Test calorie calculation for high intensity exercise."""
        from src.data_rag.met_mapping import calculate_calories

        # MET 10.0, 80kg person, 20 minutes
        # Formula: 10.0 × 80 × (20/60) = 266.67 kcal
        calories = calculate_calories(10.0, 80, 20)
        assert calories == pytest.approx(266.7, rel=0.01)

    def test_calculate_calories_low_intensity(self):
        """Test calorie calculation for low intensity exercise."""
        from src.data_rag.met_mapping import calculate_calories

        # MET 2.5, 60kg person, 60 minutes
        # Formula: 2.5 × 60 × 1.0 = 150 kcal
        calories = calculate_calories(2.5, 60, 60)
        assert calories == 150.0

    def test_calculate_calories_zero_duration(self):
        """Test calorie calculation with zero duration."""
        from src.data_rag.met_mapping import calculate_calories

        calories = calculate_calories(5.0, 70, 0)
        assert calories == 0.0

    def test_calculate_calories_zero_weight(self):
        """Test calorie calculation with zero weight."""
        from src.data_rag.met_mapping import calculate_calories

        calories = calculate_calories(5.0, 0, 30)
        assert calories == 0.0


class TestExerciseProfile:
    """Test suite for complete exercise profile generation."""

    def test_get_exercise_profile_complete(self):
        """Test complete exercise profile generation."""
        from src.data_rag.met_mapping import get_exercise_profile

        profile = get_exercise_profile(
            "Barbell Bench Press",
            "Chest",
            ["Barbell", "Pectoralis major", "Triceps"]
        )

        assert profile.met_value > 0
        assert profile.intensity in ["low", "moderate", "high"]
        assert profile.equipment_type == "barbell"
        assert "chest" in profile.primary_muscles

    def test_enrich_exercise_data(self):
        """Test exercise data enrichment."""
        from src.data_rag.met_mapping import enrich_exercise_data

        exercise = {
            "id": 1,
            "name": "Push Up",
            "category": "Chest",
            "tags": ["none (bodyweight exercise)", "Pectoralis major"],
        }

        enriched = enrich_exercise_data(exercise)

        assert "met_value" in enriched
        assert "intensity" in enriched
        assert "equipment_type" in enriched
        assert "primary_muscles" in enriched
        assert enriched["equipment_type"] == "bodyweight"
        assert enriched["intensity"] == "high"  # Push-ups are high intensity


class TestBatchEnrichment:
    """Test suite for batch exercise enrichment."""

    def test_batch_enrich_exercises(self):
        """Test batch enrichment of exercises."""
        from src.data_rag.met_mapping import batch_enrich_exercises

        exercises = [
            {"id": 1, "name": "Yoga", "category": "Stretching", "tags": []},
            {"id": 2, "name": "Running", "category": "Cardio", "tags": []},
            {"id": 3, "name": "Push Up", "category": "Chest", "tags": ["bodyweight"]},
        ]

        enriched = batch_enrich_exercises(exercises, verbose=False)

        assert len(enriched) == 3
        for ex in enriched:
            assert "met_value" in ex
            assert "intensity" in ex
            assert "equipment_type" in ex

    def test_batch_enrichment_statistics(self):
        """Test that batch enrichment produces correct statistics."""
        from src.data_rag.met_mapping import batch_enrich_exercises

        exercises = [
            {"id": 1, "name": "Yoga", "category": "Stretching", "tags": []},
            {"id": 2, "name": "Walking", "category": "Cardio", "tags": []},
            {"id": 3, "name": "HIIT", "category": "Cardio", "tags": []},
        ]

        enriched = batch_enrich_exercises(exercises, verbose=False)

        # Check intensity distribution
        intensities = [ex["intensity"] for ex in enriched]
        assert "low" in intensities  # Yoga
        assert "moderate" in intensities  # Walking
        assert "high" in intensities  # HIIT


class TestIntensityClassification:
    """Test suite for intensity classification thresholds."""

    def test_low_intensity_threshold(self):
        """Test low intensity threshold (MET < 3.0)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        # Stretching should be low intensity
        met, intensity = get_met_for_exercise("Stretching", "Recovery")
        assert met < 3.0
        assert intensity == "low"

    def test_moderate_intensity_range(self):
        """Test moderate intensity range (MET 3.0 - 6.0)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        # Walking should be moderate intensity
        met, intensity = get_met_for_exercise("Walking", "Cardio")
        assert 3.0 <= met <= 6.0
        assert intensity == "moderate"

    def test_high_intensity_threshold(self):
        """Test high intensity threshold (MET > 6.0)."""
        from src.data_rag.met_mapping import get_met_for_exercise

        # Running should be high intensity
        met, intensity = get_met_for_exercise("Running", "Cardio")
        assert met > 6.0
        assert intensity == "high"


class TestMuscleGroupExtraction:
    """Test suite for muscle group extraction."""

    def test_chest_muscle_extraction(self):
        """Test chest muscle extraction."""
        from src.data_rag.met_mapping import get_primary_muscles

        muscles = get_primary_muscles(["Pectoralis major", "Triceps"], "Chest")
        assert "chest" in muscles

    def test_back_muscle_extraction(self):
        """Test back muscle extraction."""
        from src.data_rag.met_mapping import get_primary_muscles

        muscles = get_primary_muscles(["Latissimus dorsi", "Bicep"], "Back")
        assert "back" in muscles

    def test_legs_muscle_extraction(self):
        """Test legs muscle extraction."""
        from src.data_rag.met_mapping import get_primary_muscles

        muscles = get_primary_muscles(["Quadriceps", "Gluteus maximus"], "Legs")
        assert "legs" in muscles

    def test_category_fallback(self):
        """Test category fallback when no muscle tags found."""
        from src.data_rag.met_mapping import get_primary_muscles

        muscles = get_primary_muscles([], "Chest")
        assert "chest" in muscles
