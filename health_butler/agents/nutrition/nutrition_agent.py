
"""Nutrition Agent for food analysis and diet advice.

This specialist agent analyzes food items from text or images,
estimates calories/macros, and provides health tips using RAG
and vision tools.
"""

from typing import Optional, List, Dict, Any
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

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute nutrition analysis. 
        If 'image_path' is found in the task or context, use VisionTool.
        Then query RAG backbone for details.
        """
        logger.info("[NutritionAgent] Executing task: %s", task)
        
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
            logger.info("[NutritionAgent] Vision analysis on: %s", image_path)
            try:
                vision_results = self.vision_tool.detect_food(image_path)
                # Check if vision tool returned valid results (no errors)
                if vision_results and "error" not in vision_results[0]:
                    top_item = vision_results[0]
                    vision_context = f"Visual Analysis identified: {top_item['label']} (Confidence: {top_item['confidence']:.2f})."
                    # Use the detected label to augment the RAG query
                    task = f"{task}. logic: Access nutrition info for {top_item['label']}."
                else:
                    # Vision tool failed or returned an error
                    error_msg = vision_results[0].get("error", "Unknown error") if vision_results else "No results"
                    logger.warning("[NutritionAgent] Vision analysis failed: %s. Proceeding with text-only analysis.", error_msg)
                    vision_context = "(Visual analysis was unavailable - analyzing from text description only)"
            except Exception as e:
                # Catch any unexpected exceptions from vision tool
                logger.error("[NutritionAgent] Unexpected vision error: %s", e)
                vision_context = "(Visual analysis was unavailable - analyzing from text description only)"

        # Perform RAG lookup based on the (potentially augmented) task
        # We extract keywords from task to query RAG.
        # For prototype, we just pass the full task or the vision label if available.
        query_text = task
        # Only use vision label for RAG query if vision analysis succeeded
        # (i.e., vision_context contains actual identification, not an error message)
        if vision_context and "unavailable" not in vision_context.lower():
             # Extract the label from vision_context for more precise RAG query
             # Format: "Visual Analysis identified: <label> (Confidence: ...)"
             if "identified:" in vision_context:
                 label = vision_context.split("identified: ")[1].split(" (")[0]
                 query_text = label
             
        rag_results = self.rag_tool.query(query_text, top_k=3)
        rag_context = ""
        if rag_results:
            rag_context = "\nDatabase Information:\n"
            for res in rag_results:
                rag_context += f"- {res['text']}\n"
        
        # Augment the prompt with tool data
        augmented_task = f"{task}\n\n{vision_context}\n{rag_context}"
        
        return super().execute(augmented_task, context)
