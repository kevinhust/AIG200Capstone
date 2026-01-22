
from typing import Optional, List, Dict
import logging
from src.agents.base_agent import BaseAgent
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.data_rag.rag_tool import RagTool

logger = logging.getLogger(__name__)

class NutritionAgent(BaseAgent):
    """
    Specialist agent for analyzing food, calculating nutrition, and providing diet advice.
    It utilizes retrieval tools (USDA database) and vision tools (ViT) to understand food content.
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
        self.vision_tool = VisionTool()
        self.rag_tool = RagTool()

    def execute(self, task: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute nutrition analysis. 
        If 'image_path' is found in the task or context, use VisionTool.
        Then query RAG backbone for details.
        """
        logger.info(f"[NutritionAgent] Executing task: {task}")
        
        # Check for image path in context or task (simplified heuristic)
        image_path = None
        if context:
            for msg in context:
                if msg.get("type") == "image_path":
                    image_path = msg.get("content")
                    break
        
        # Also check if task string contains a path-like string (very basic check)
        if "image:" in task:
            parts = task.split("image:")
            if len(parts) > 1:
                image_path = parts[1].strip()

        vision_context = ""
        if image_path:
            logger.info(f"[NutritionAgent] Vision analysis on: {image_path}")
            vision_results = self.vision_tool.detect_food(image_path)
            if vision_results:
                top_item = vision_results[0]
                vision_context = f"Visual Analysis identified: {top_item['label']} (Confidence: {top_item['confidence']:.2f})."
                # Use the detected label to augment the RAG query
                task = f"{task}. logic: Access nutrition info for {top_item['label']}."

        # Perform RAG lookup based on the (potentially augmented) task
        # We extract keywords from task to query RAG. 
        # For prototype, we just pass the full task or the vision label if available.
        query_text = task
        if vision_context:
             # If we saw an image, the most relevant query is the label
             query_text = vision_results[0]['label']
             
        rag_results = self.rag_tool.query(query_text, top_k=3)
        rag_context = ""
        if rag_results:
            rag_context = "\nDatabase Information:\n"
            for res in rag_results:
                rag_context += f"- {res['text']}\n"
        
        # Augment the prompt with tool data
        augmented_task = f"{task}\n\n{vision_context}\n{rag_context}"
        
        return super().execute(augmented_task, context)
