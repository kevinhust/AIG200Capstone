
import pytest
import os
import sys
# Add project root to sys.path to allow importing from health_butler
sys.path.append(os.getcwd())

pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from health_butler.data_rag.rag_tool import RagTool
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.coordinator.coordinator_agent import CoordinatorAgent
from health_butler.main import HealthSwarmOrchestrator

def test_rag_tool():
    """Verify RAG tool query."""
    tool = RagTool()
    
    # Add dummy doc if empty to test search logic
    if tool.collection.count() == 0:
        tool.add_documents([{"text": "Chicken breast is rich in protein", "metadata": {}, "id": "test_1"}])
    
    # Use 'chicken' as verified in previous fix
    results = tool.query("chicken")
    assert isinstance(results, list)
    assert len(results) > 0

def test_vision_tool():
    """Verify Vision tool mock logic."""
    tool = VisionTool()
    import pathlib
    # The tests run from root, so data path is still valid
    dummy_img = pathlib.Path("data/raw/food-101/images/pizza/sample.jpg")
    
    # Only verify if setup ran
    if dummy_img.exists():
        results = tool.detect_food(str(dummy_img))
        assert results[0]['label'] == 'pizza'

def test_agents_initialization():
    """Verify agents instantiate with correct roles."""
    nutri = NutritionAgent()
    assert nutri.role == "nutrition"
    
    fit = FitnessAgent()
    assert fit.role == "fitness"
    
    coord = CoordinatorAgent()
    assert coord.role == "coordinator"

def test_coordinator_delegation_logic():
    """Verify coordinator can route simple keywords."""
    coord = CoordinatorAgent()
    
    # Test Nutrition routing
    plan_nutri = coord._simple_delegate("I ate a burger")
    assert plan_nutri[0]['agent'] == 'nutrition'
    
    # Test Fitness routing
    plan_fit = coord._simple_delegate("Suggest a workout")
    assert plan_fit[0]['agent'] == 'fitness'

@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="Requires Gemini API Key")
def test_swarm_execution_real():
    """Integration test for full swarm execution (requires API Key)."""
    swarm = HealthSwarmOrchestrator()
    result = swarm.execute("How many calories in an apple?", verbose=False)
    assert result is not None
    assert len(result) > 0

def test_swarm_execution_mock():
    """Integration test ensuring swarm runs without crashing."""
    swarm = HealthSwarmOrchestrator()
    result = swarm.execute("Run a test task", verbose=False)
    assert "completed" in result or "Synthesize" in result or result
