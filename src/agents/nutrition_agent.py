from typing import Dict, Any, List
# Import mocks - in a real app these might be injected or imported from final modules
from src.cv_food_rec.food_recognition import FoodRecognitionService
from src.data_rag.rag_service import RAGService

class NutritionAgent:
    """
    Agent responsible for analyzing food photos and providing nutrition advice.
    """
    
    def __init__(self):
        self.cv_service = FoodRecognitionService()
        self.rag_service = RAGService()

    def analyze_meal(self, image_path: str, user_query: str = "") -> Dict[str, Any]:
        """
        Orchestrates the analysis of a meal from an image.
        
        1. Detects food in the image.
        2. Retrieves relevant info (internal step in generation usually, but we can explicit if needed).
        3. Generates advice.
        
        Args:
            image_path: Path to the image.
            user_query: Optional user question.
            
        Returns:
            Dictionary with detected foods and advice.
        """
        # 1. Vision Analysis
        detected_foods = self.cv_service.detect_food(image_path)
        
        if not detected_foods:
            return {
                "foods": [],
                "advice": "No food detected in the image. Please try again."
            }

        # 2. Nutrition Analysis & Advice Generation
        # (The RAG service handles retrieval + generation in this mock)
        advice = self.rag_service.generate_advice(detected_foods, user_query)
        
        return {
            "foods": detected_foods,
            "advice": advice
        }

if __name__ == "__main__":
    # Simple test
    agent = NutritionAgent()
    result = agent.analyze_meal("dummy_image.jpg", "Is this healthy?")
    print(result)
