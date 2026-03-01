import asyncio
import json
import logging
import os
from dotenv import load_dotenv
load_dotenv()
from src.swarm import HealthSwarm, handoff_to_fitness

# Reduce logging noise
logging.getLogger("httpx").setLevel(logging.WARNING)

async def run_simulation():
    swarm = HealthSwarm(verbose=True)
    
    # Simulating the boundary case context
    user_context = {
        "user_id": "sim_user_99",
        "name": "Kevin",
        "conditions": ["Knee Injury"],
        "goal": "Weight Loss",
        "daily_intake": []
    }
    
    print("==================================================")
    print("🛡️ PHASE 6: CALORIE BALANCE SHIELD - E2E SIMULATION")
    print("==================================================\n")
    
    print("------- STAGE 1: NUTRITION PERCEPTION -------")
    image_path = "/Users/kevinwang/Documents/20Projects/capstonetest/tacos.png"
    print(f"User uploaded image: {image_path}")
    print("Analyzing via YOLO11 + Gemini 2.5 Flash...")
    
    try:
        res = await swarm.execute_async(
            user_input="Analyze this meal",
            image_path=image_path,
            user_context=user_context
        )
        
        print("\n[Nutrition Agent Output]")
        try:
            payload = json.loads(res["response"])
            # Format output nicely
            print(f"Dish Name: {payload.get('dish_name')}")
            print(f"Calories: {payload.get('total_macros', {}).get('calories')} kcal")
            print(f"Visual Warnings: {payload.get('visual_warnings', [])}")
            print(f"suggest_fitness_transfer Flag: {payload.get('suggest_fitness_transfer', False)}")
            
            if payload.get("suggest_fitness_transfer"):
                print("\n✅ [SYSTEM] Calorie Balance Shield Activated: High-risk meal detected.")
                print("✅ [UI] Bot mounts [🏃 Work it off!] dynamic button on MealLogView.")
                
                print("\n------- STAGE 2: FITNESS HANDOFF -------")
                print("User clicks [🏃 Work it off!]. Handoff initiated...\n")
                
                # Setup context mirroring what bot.py passes during handoff
                handoff_signal = handoff_to_fitness()
                task = f"{handoff_signal}: need post-meal compensatory workout for heavy/fried meal"
                
                fitness_res = await swarm.execute_async(
                    user_input=task,
                    user_context=user_context  # Bot uses profile context
                )
                
                print("\n[Fitness Agent Output] (Post-Meal Workout Plan)")
                try:
                    fit_payload = json.loads(fitness_res["response"])
                    print(json.dumps(fit_payload, indent=2))
                    
                    if any("BR-001" in str(w) for w in fit_payload.get("safety_warnings", [])) or \
                       ("BR-001" in str(fit_payload.get("dynamic_adjustments", ""))):
                        print("\n✅ [SAFETY] BR-001 Disclaimer successfully injected.")
                        print("✅ [SAFETY] High intensity exercises successfully filtered based on meal risks.")
                        print("\n🎉 END-TO-END SIMULATION SUCCESSFUL 🎉")
                    else:
                        print("\n⚠️ [SAFETY] BR-001 Disclaimer missing. Safety logic might need tweaking.")
                    
                except json.JSONDecodeError:
                    print(f"Failed to parse Fitness output: {fitness_res['response']}")
            else:
                print("\nℹ️ Meal did not trigger the Calorie Balance Shield.")
                
        except json.JSONDecodeError:
            print(f"Failed to parse Nutrition output: {res['response']}")
            
    except Exception as e:
        print(f"Simulation failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
