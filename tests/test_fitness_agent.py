
import pytest
from unittest.mock import MagicMock, patch
from health_butler.agents.fitness.fitness_agent import FitnessAgent

@pytest.fixture
def fitness_agent():
    return FitnessAgent()

def test_fitness_agent_initialization(fitness_agent):
    """Test that the agent initializes with the correct role and profile."""
    assert fitness_agent.role == "fitness"
    assert "Kevin" in fitness_agent.system_prompt
    assert "Knee pain" in fitness_agent.system_prompt

@patch("src.agents.base_agent.BaseAgent.execute")
def test_fitness_advice_high_calorie(mock_base_execute, fitness_agent):
    """Test advice logic for high calorie input."""
    # Setup mock return
    mock_base_execute.return_value = "Suggesting a 30-min walk."
    
    # Define input
    task = "I just ate a big burger (800kcal)."
    context = []
    
    # Execute
    result = fitness_agent.execute(task, context)
    
    # Verify the correct prompt was constructed (checking if it includes nutrition context logic)
    # Since we mocked base_execute, we check what it was called with
    args, _ = mock_base_execute.call_args
    called_prompt = args[0]
    
    # The prompt passed to LLM should contain the task
    assert "I just ate a big burger" in called_prompt
    assert result == "Suggesting a 30-min walk."

@patch("src.agents.base_agent.BaseAgent.execute")
def test_fitness_with_nutrition_context(mock_base_execute, fitness_agent):
    """Test that context from Nutrition Agent is incorporated."""
    mock_base_execute.return_value = "Advice based on nutrition data."
    
    task = "What should I do?"
    context = [
        {"from": "nutrition", "content": "Meal contains 50g protein and 400kcal."}
    ]
    
    fitness_agent.execute(task, context)
    
    args, _ = mock_base_execute.call_args
    called_prompt = args[0]
    
    # Ensure nutrition data was injected into the prompt
    assert "RELEVANT NUTRITION DATA" in called_prompt
    assert "50g protein" in called_prompt
