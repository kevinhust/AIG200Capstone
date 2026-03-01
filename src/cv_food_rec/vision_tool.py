"""Vision Tool for food detection using YOLO11.

Finds food items in images and returns bounding boxes for Phase 2 semantic analysis.
Uses a Singleton pattern to ensure the YOLO model is loaded only once.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image

# Setup logging
logger = logging.getLogger(__name__)

class VisionTool:
    """
    Vision tool for food detection.
    
    Pivot (Milestone 2): Uses YOLO11 for object detection.
    This tool is responsible for "where" the food is.
    """
    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VisionTool, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "yolo11n.pt") -> None:
        # Avoid re-initialization if already initialized
        if hasattr(self, 'initialized'):
            return
        
        self.model_name = model_name
        self.initialized = True
        logger.info("VisionTool initialized (Lazy Loading enabled)")
    
    def _load_model(self) -> None:
        """Lazy load the YOLO11 model on first use."""
        if VisionTool._model is not None:
            return

        try:
            from ultralytics import YOLO
            logger.info("🚀 Loading YOLO11 model: %s...", self.model_name)
            VisionTool._model = YOLO(self.model_name)
            logger.info("✅ YOLO11 model loaded successfully.")
        except Exception as e:
            logger.error("❌ Failed to load YOLOv8 model: %s. Vision features will be limited.", e)
            VisionTool._model = None

    def detect_food(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect food items using YOLOv8 and return bounding boxes.
        """
        self._load_model()
        
        logger.info("🔍 Analyzing image for objects: %s", image_path)
        image_path_obj = Path(image_path)
        
        if not image_path_obj.exists():
            return [{"error": "Image file not found"}]

        if VisionTool._model is None:
            return [{"error": "Model not loaded"}]

        try:
            # Run inference
            results = VisionTool._model(image_path, verbose=False)
            
            detections = []
            if results and len(results) > 0:
                result = results[0]
                for box in result.boxes:
                    # Filter for 'food' related classes or just take all for now 
                    # as we rely on Gemini to filter semantics
                    class_id = int(box.cls[0])
                    label = result.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # Convert bbox to list [x1, y1, x2, y2]
                    bbox = box.xyxy[0].tolist()
                    
                    detections.append({
                        "label": label,
                        "confidence": confidence,
                        "bbox": bbox
                    })
            
            if not detections:
                logger.info("⚠️ No objects detected in image.")
                
            return detections
            
        except Exception as e:
            logger.error("❌ Error during food detection: %s", e)
            return [{"error": str(e)}]

    async def detect_food_async(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect food items asynchronously using a thread pool.
        """
        import asyncio
        return await asyncio.to_thread(self.detect_food, image_path)

# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = VisionTool()
    
    # Test with a dummy image or common paths
    test_img = Path("data/raw/sample_food.jpg")
    if test_img.exists():
        results = tool.detect_food(str(test_img))
        print(f"Results: {results}")
    else:
        print(f"Test image not found at {test_img}")
