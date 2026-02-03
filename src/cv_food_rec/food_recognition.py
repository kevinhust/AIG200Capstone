import torch
from transformers import ViTImageProcessor, ViTForImageClassification
from PIL import Image
from typing import List, Dict

class FoodRecognitionService:
    """
    Service for Food Recognition using Vision Transformer (ViT).
    Uses a model fine-tuned on food datasets (e.g., Food-101) if available.
    """

    def __init__(self, model_name: str = "nateraw/food"):
        """
        Initialize the ViT model and processor.
        
        Args:
            model_name: Hugging Face model hub name.
                        Defaults to 'nateraw/food' which is ViT fine-tuned on Food-101.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # On Mac with MPS (Metal Performance Shaders), we might want to use 'mps' if available and stable, 
        # but 'cpu' is safer for compatibility unless we check.
        # torch.backends.mps.is_available() check could be added.
        if torch.backends.mps.is_available():
            self.device = "mps"
            
        print(f"Loading Food Recognition model: {model_name} on {self.device}...")
        try:
            self.processor = ViTImageProcessor.from_pretrained(model_name)
            self.model = ViTForImageClassification.from_pretrained(model_name).to(self.device)
        except Exception as e:
            print(f"Failed to load user-specified model {model_name}: {e}")
            print("Falling back to standard ViT-base...")
            fallback_model = "google/vit-base-patch16-224"
            self.processor = ViTImageProcessor.from_pretrained(fallback_model)
            self.model = ViTForImageClassification.from_pretrained(fallback_model).to(self.device)

    def detect_food(self, image_path: str, top_k: int = 3) -> List[Dict]:
        """
        Detects food items in the given image.
        
        Args:
            image_path: Path to the image file.
            top_k: Number of top predictions to return.
            
        Returns:
            List of dictionaries containing detected food items.
            Example: [{"name": "pizza", "confidence": 0.95, "bbox": None}]
        """
        try:
            image = Image.open(image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
                
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]
            
            # Get top k predictions
            top_probs, top_indices = torch.topk(probs, top_k)
            
            results = []
            for prob, idx in zip(top_probs, top_indices):
                label = self.model.config.id2label[idx.item()]
                results.append({
                    "name": label,
                    "confidence": float(prob),
                    "bbox": None 
                })
                
            return results
            
        except Exception as e:
            print(f"Error analyzing image {image_path}: {e}")
            return []
