
import os
import requests
import zipfile
import io
from pathlib import Path
import shutil

# Food-101 Dataset URL
# Using a small subset or placeholder for Phase 1
DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")

def setup_food101_sample():
    """
    Sets up a sample structure for Food-101 dataset.
    In a real scenario, this would download the dataset.
    For Phase 1, we create a few dummy image files to test the Vision Tool pipeline.
    """
    print("Setting up Food-101 sample data...")
    images_dir = DATA_RAW_DIR / "food-101" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dummy image files for testing file walking
    classes = ["hamburger", "pizza", "sushi"]
    for cls in classes:
        cls_dir = images_dir / cls
        cls_dir.mkdir(exist_ok=True)
        # Create a dummy image file
        with open(cls_dir / "sample.jpg", "w") as f:
            f.write("This is a dummy image file for testing directory structure.")
            
    print(f"✅ Created dummy Food-101 structure at {images_dir}")
    print(f"   Classes: {', '.join(classes)}")

if __name__ == "__main__":
    setup_food101_sample()
