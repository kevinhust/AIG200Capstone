import logging
from typing import List, Dict, Any
from pathlib import Path
from PIL import Image
import torch
from transformers import ViTImageProcessor, ViTForImageClassification

# Setup logging
logger = logging.getLogger(__name__)

class VisionTool:
    """
    Vision tool for food recognition using Vision Transformer (ViT).
    Phase 2: Integration with HuggingFace ViT (nateraw/food-vit-101).
    """
    
    def __init__(self, model_name: str = "nateraw/food-vit-101"):
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load the ViT model and processor."""
        try:
            logger.info(f"Loading ViT model: {self.model_name}...")
            self.processor = ViTImageProcessor.from_pretrained(self.model_name)
            self.model = ViTForImageClassification.from_pretrained(self.model_name)
            self.model.eval()
            logger.info("ViT model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load {self.model_name}: {e}. Trying fallback 'google/vit-base-patch16-224'...")
            try:
                fallback = "google/vit-base-patch16-224"
                self.processor = ViTImageProcessor.from_pretrained(fallback)
                self.model = ViTForImageClassification.from_pretrained(fallback)
                self.model.eval()
                self.model_name = fallback
                logger.info(f"Fallback model {fallback} loaded successfully.")
            except Exception as e2:
                logger.error(f"Critical: Failed to load fallback model: {e2}")
                self.model = None
            
    def detect_food(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Classify food items in the given image.
        Returns a list containing the top prediction with label and confidence.
        """
        logger.info(f"Analyzing image: {image_path}")
        image_path_obj = Path(image_path)
        
        if not image_path_obj.exists():
            return [{"error": "Image file not found"}]

        if self.model is None:
            return [{"error": "Model not loaded"}]

        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
            
            # Get predicted class
            predicted_class_idx = logits.argmax(-1).item()
            label = self.model.config.id2label[predicted_class_idx]
            confidence = torch.nn.functional.softmax(logits, dim=-1)[0, predicted_class_idx].item()
            
            logger.info(f"Detected: {label} ({confidence:.2f})")
            
            return [{
                "label": label,
                "confidence": confidence,
                "bbox": None  # ViT is classification only
            }]
            
        except Exception as e:
            logger.error(f"Error during food detection: {e}")
            return [{"error": str(e)}]

# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tool = VisionTool()
    
    # Use a placeholder image if available, else warn
    test_img = Path("data/raw/food-101/images/pizza/sample.jpg")
    try:
        if test_img.exists():
            # Create a real dummy image if it's 0 bytes or just text
            import numpy as np
            if test_img.stat().st_size < 100: # It was a text file in Phase 1
                 img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
                 img.save(test_img)
                 
            results = tool.detect_food(str(test_img))
            print(results)
        else:
            print(f"Test image {test_img} not found.")
    except Exception as e:
        print(f"Error during test: {e}")
