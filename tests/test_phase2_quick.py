import logging
import sys
from pathlib import Path
import pytest

pytest.importorskip("numpy")
pytest.importorskip("chromadb")
pytest.importorskip("sentence_transformers")

from PIL import Image
import numpy as np

# Setup
logging.basicConfig(level=logging.INFO)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.data_rag.rag_tool import RagTool
from health_butler.data_rag.ingest_usda import download_usda_sample, process_and_index

def test_pipeline():
    print("=== Testing Phase 2 Core Capabilities ===")
    
    # 1. Test Ingestion & ChromaDB
    print("\n[1] Testing Data Ingestion & Indexing...")
    process_and_index()
    
    print("\n[2] Testing RAG Query...")
    rag = RagTool()
    results = rag.query("chicken breast")
    assert len(results) > 0, "RAG returned no results"
    print(f"RAG Result: {results[0]['text'][:100]}...")
    
    # 2. Test Vision (simulated)
    print("\n[3] Testing Vision Tool (ViT)...")
    vision = VisionTool() # Defaults to nateraw/food-vit-101
    
    # Create fake pizza image to test inference, since we don't have real Food-101 files yet
    # Or try to force download of one if needed. The tool handles non-existent gracefully.
    test_img_path = Path("temp_test_pizza.jpg")
    img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    img.save(test_img_path)
    
    # This will likely return a random label since it's noise, but verifies the pipeline
    res = vision.detect_food(str(test_img_path))
    print(f"Vision Result on Random Noise: {res}")
    
    test_img_path.unlink()
    
    print("\n=== Phase 2 Validation Complete ===")

if __name__ == "__main__":
    test_pipeline()
