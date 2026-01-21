
from src.agents.base_agent import BaseAgent

class NutritionAgent(BaseAgent):
    """
    Specialist agent for analyzing food, calculating nutrition, and providing diet advice.
    It utilizes retrieval tools (USDA database) and vision tools (YOLO) to understand food content.
    """
    
    def __init__(self):
        super().__init__(
            role="nutrition",
            system_prompt="""You are an expert Nutritionist and Dietitian AI.
            
Your responsibilities:
1. Identify food items from descriptions or analyzed image tags.
2. Estimate calories and macronutrients (Protein, Carbs, Fat) with high accuracy.
3. Provide breakdown of ingredients when possible.
4. Offer brief, actionable health tips based on the food content.

When you don't know the exact nutrition, use your general knowledge but mention it is an estimate.
If provided with tool outputs (like RAG search results), prioritize that data.
            """
        )
