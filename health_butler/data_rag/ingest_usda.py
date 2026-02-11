import os
import json
import logging
from pathlib import Path
import sys

# Add project root to path to import health_butler modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from health_butler.data_rag.rag_tool import RagTool

# Constants
DATA_RAW_DIR = Path("health_butler/data/raw")
DATA_PROCESSED_DIR = Path("health_butler/data/processed")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_dirs():
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def download_usda_sample():
    """
    Creates/Downloads a sample USDA dataset.
    """
    logger.info("Downloading/Creating USDA sample data...")
    
    sample_data = [
        {
            "fdcId": 1001,
            "description": "Chicken breast, raw",
            "foodNutrients": [
                {"nutrientName": "Protein", "value": 23.1, "unitName": "G"},
                {"nutrientName": "Energy", "value": 110, "unitName": "KCAL"},
                {"nutrientName": "Total lipid (fat)", "value": 1.2, "unitName": "G"}
            ]
        },
        {
            "fdcId": 1002,
            "description": "Broccoli, raw",
            "foodNutrients": [
                {"nutrientName": "Protein", "value": 2.8, "unitName": "G"},
                {"nutrientName": "Energy", "value": 34, "unitName": "KCAL"},
                {"nutrientName": "Carbohydrate, by difference", "value": 6.6, "unitName": "G"}
            ]
        },
        {
            "fdcId": 1003,
            "description": "Rice, white, cooked",
            "foodNutrients": [
                {"nutrientName": "Protein", "value": 2.7, "unitName": "G"},
                {"nutrientName": "Energy", "value": 130, "unitName": "KCAL"},
                {"nutrientName": "Carbohydrate, by difference", "value": 28.0, "unitName": "G"}
            ]
        }
    ]
    
    output_file = DATA_RAW_DIR / "usda_sample.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    logger.info("✅ Created synthetic USDA sample at %s", output_file)
    return output_file

def process_and_index():
    ensure_dirs()
    raw_file = download_usda_sample()
    
    logger.info("Processing %s...", raw_file)
    with open(raw_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rag_docs = []
    for item in data:
        desc = item.get("description", "Unknown Food")
        nutrients = item.get("foodNutrients", [])
        
        # Extract metadata
        nutrition_meta = {}
        nutrient_str_list = []
        for n in nutrients:
            name = n.get('nutrientName', '').lower()
            val = n.get('value', 0)
            unit = n.get('unitName', '')
            
            # Map common nutrients to metadata for filtering
            if 'protein' in name:
                nutrition_meta['protein'] = float(val)
            elif 'energy' in name:
                nutrition_meta['calories'] = float(val)
            elif 'lipid' in name or 'fat' in name:
                nutrition_meta['fat'] = float(val)
            elif 'carbohydrate' in name:
                nutrition_meta['carbs'] = float(val)
                
            nutrient_str_list.append(f"{n.get('nutrientName')}: {val} {unit}")

        nutrient_text = ", ".join(nutrient_str_list[:5])
        full_text = f"Food: {desc}. Nutrients per 100g: {nutrient_text}."
        
        doc = {
            "text": full_text,
            "metadata": {
                "source": "USDA",
                "description": desc,
                **nutrition_meta
            },
            "id": str(item.get("fdcId"))
        }
        rag_docs.append(doc)
    
    # Save processed JSON for reference
    output_file = DATA_PROCESSED_DIR / "usda_chunks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rag_docs, f, indent=2)
    logger.info("✅ Processed %d items saved to %s", len(rag_docs), output_file)

    # Index into ChromaDB
    logger.info("Indexing to ChromaDB...")
    try:
        rag_tool = RagTool()
        if rag_tool.collection.count() > 0:
            logger.info("Collection already has data. Skipping re-indexing for MVP speed.")
        else:
            rag_tool.add_documents(rag_docs)
            logger.info("✅ Indexing Complete.")
    except Exception as e:
        logger.error("Failed to index to ChromaDB: %s", e)

if __name__ == "__main__":
    process_and_index()
