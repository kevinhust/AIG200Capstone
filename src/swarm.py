"""
HealthSwarm - A compatibility bridge for the Discord bot to the agent swarm.
Wraps specialized agents (Fitness, Nutrition) into a unified interface.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from src.agents.router_agent import RouterAgent
from src.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

def handoff_to_nutrition(kcal_burned: Optional[float] = None) -> str:
    """Signal to handoff to the Nutrition Agent."""
    return f"transfer_to_nutrition:{kcal_burned or 0}"

def handoff_to_fitness() -> str:
    """Signal to handoff to the Fitness Agent."""
    return "transfer_to_fitness"

class HealthSwarm:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.router = RouterAgent()
        self.rag = SimpleRagTool()
        logger.info("HealthSwarm initialized with RouterAgent and Swarm Handoff support")

    async def execute_async(
        self, 
        user_input: str, 
        image_path: Optional[str] = None, 
        user_context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        [Phase 3] High-level async execution with proactive handoffs.
        """
        lower_input = user_input.lower()
        
        # 1. Check for explicit handoff signals (e.g. from Button interactions)
        if lower_input.startswith("transfer_to_nutrition"):
            from src.agents.nutrition.nutrition_agent import NutritionAgent
            logger.info("Swarm Handoff: Force Routing to Nutrition")
            agent = NutritionAgent()
            
            # Extract kcal if present in signal
            kcal_hint = 0
            if ":" in lower_input:
                try: kcal_hint = float(lower_input.split(":")[1])
                except: pass
            
            prompt = f"The user just finished a workout burning {kcal_hint} kcal. Suggest a recovery meal."
            if user_context:
                prompt += f" Context: {json.dumps(user_context)}"
            
            # NutritionAgent execute_async handles the rest
            response = await agent.execute_async(prompt)
            return {"response": response, "agent": "nutrition"}

        if lower_input.startswith("transfer_to_fitness"):
            from src.agents.fitness.fitness_agent import FitnessAgent
            logger.info("Swarm Handoff: Force Routing to Fitness")
            agent = FitnessAgent()
            response = await agent.execute_async(user_input, [{"type": "user_context", "content": json.dumps(user_context or {})}])
            return {"response": response, "agent": "fitness"}

        # 2. Collaborative Delegation via RouterAgent
        delegations = self.router.analyze_and_delegate(user_input)
        
        results = []
        final_agent = "router"
        
        for delegation in delegations:
            agent_type = delegation["agent"]
            task = delegation["task"]
            
            if agent_type == "fitness":
                from src.agents.fitness.fitness_agent import FitnessAgent
                agent = FitnessAgent()
                context = [{"type": "user_context", "content": json.dumps(user_context or {})}]
                res = await agent.execute_async(task, context)
                results.append(res)
                final_agent = "fitness"
            
            elif agent_type == "nutrition":
                from src.agents.nutrition.nutrition_agent import NutritionAgent
                agent = NutritionAgent()
                context = [{"type": "user_context", "content": json.dumps(user_context or {})}]
                if image_path:
                    context.append({"type": "image_path", "content": image_path})
                    
                # Handle image if available for the nutrition part of task
                res = await agent.execute_async(task, context, progress_callback=progress_callback)
                
                # Phase 6: Calorie Balance Shield Checking
                try:
                    res_json = json.loads(res)
                    cal_pct = res_json.get("daily_value_percentage", {}).get("calories", 0)
                    warnings = [w.lower() for w in res_json.get("visual_warnings", [])]
                    
                    suggest_fitness_transfer = cal_pct > 50.0 or any("fried" in w or "oil" in w or "greasy" in w for w in warnings)
                    
                    if suggest_fitness_transfer:
                        res_json["suggest_fitness_transfer"] = True
                        res = json.dumps(res_json)
                except Exception as e:
                    logger.warning(f"Error checking fitness transfer: {e}")

                results.append(res)
                final_agent = "nutrition"
            
            else:
                # Fallback for coder/researcher/etc.
                res = await asyncio.to_thread(self.router.execute, task)
                results.append(res)

        # Synthesis: If multiple results, combine them. If one, return as is (for specialized JSON handling)
        if len(results) == 1:
            return {"response": results[0], "agent": final_agent}
        
        # Multi-agent synthesis
        combined_response = self.router.synthesize_results(delegations, results)
        return {"response": combined_response, "agent": "router"}

    def execute(self, user_input: str, image_path: Optional[str] = None, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronous wrapper."""
        import asyncio
        try:
            return asyncio.run(self.execute_async(user_input, image_path, user_context))
        except RuntimeError:
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.get_event_loop().run_until_complete(self.execute_async(user_input, image_path, user_context))
