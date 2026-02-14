import sys
import os
import pytest

# Add project root to python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)

pytest.importorskip("torch")

from src.agents.nutrition_agent import NutritionAgent

def test_nutrition_agent_flow():
    print("Testing Nutrition Agent Flow...")
    
    agent = NutritionAgent()
    
    image_path = "test_meal.jpg"
    query = "Is this good for building muscle?"
    
    print(f"Input: Image='{image_path}', Query='{query}'")
    
    result = agent.analyze_meal(image_path, query)
    
    print("\n--- Result ---")
    print(result)
    
    # Simple assertions
    assert "foods" in result
    assert "advice" in result
    assert len(result["foods"]) > 0
    assert "building muscle" in result["advice"] or "good" in result["advice"] or "fit" in result["advice"] # Loose check on mock
    
    print("\n✅ Test Passed!")

if __name__ == "__main__":
    test_nutrition_agent_flow()
