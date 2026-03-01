import asyncio
import json

class MockSwarm:
    async def execute_async(self, user_input, user_context=None, **kwargs):
        print(f"[Swarm Mock] Received execution for: {user_input}")
        
        # Test case 1: It's an image analysis that yields fried foods
        if "Analyze this meal" in user_input:
            mock_nutrition_result = {
                "dish_name": "Fried Chicken Platter",
                "total_macros": {"calories": 1200, "protein": 40, "carbs": 80, "fat": 60},
                "daily_value_percentage": {"calories": 60.0},
                "visual_warnings": ["Fried", "High-oil"]
            }
            # Simulate swarm.py adding the flag
            cal_pct = mock_nutrition_result.get("daily_value_percentage", {}).get("calories", 0)
            warnings = [w.lower() for w in mock_nutrition_result.get("visual_warnings", [])]
            suggest_fitness_transfer = cal_pct > 50.0 or any("fried" in w or "oil" in w or "greasy" in w for w in warnings)
            
            if suggest_fitness_transfer:
                mock_nutrition_result["suggest_fitness_transfer"] = True
            
            return {"response": json.dumps(mock_nutrition_result), "agent": "nutrition"}
            
        return {"response": json.dumps({"status": "unknown"}), "agent": "router"}

async def test_phase_6():
    print("--- Phase 6: Calorie Balance Shield Verification ---")
    swarm = MockSwarm()
    res = await swarm.execute_async("Analyze this meal")
    payload = json.loads(res["response"])
    print(f"Nutrition Agent Output: {json.dumps(payload, indent=2)}")
    
    if payload.get("suggest_fitness_transfer"):
        print("\n✅ Calorie Balance Shield Condition Met!")
        print("Bot logic would mount the [🏃 Work it off!] button to the view.")
        
        print("\nSimulating button click execution against actual FitnessAgent...")
        try:
            from src.agents.fitness.fitness_agent import FitnessAgent
            fitness = FitnessAgent()
            # Context passed effectively from the button
            context = [
                {"type": "user_context", "content": json.dumps({"name": "TestUser", "conditions": []})},
                {"type": "nutrition_summary", "content": json.dumps(payload)}
            ]
            
            # The handoff signal
            from src.swarm import handoff_to_fitness
            handoff = handoff_to_fitness()
            task = f"{handoff}: need post-meal compensatory workout for heavy/fried meal"
            
            result = fitness.execute(task, context)
            print(f"Fitness Agent Result: {result}")
        except Exception as e:
            print(f"Error executing fitness agent: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ Calorie Balance Shield NOT triggerd.")

if __name__ == "__main__":
    asyncio.run(test_phase_6())
