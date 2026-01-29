#!/usr/bin/env python3
"""
Download real USDA nutrition data for Food-101 categories.
Uses USDA FoodData Central API.
"""

import json
import time
import requests
from pathlib import Path

API_KEY = "HI1Zkn5obOSoY7w1D1GwZVy1jmSUsmBbAfuyO0LH"
BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Food-101 categories
FOOD_101_CATEGORIES = [
    "apple pie", "baby back ribs", "baklava", "beef carpaccio", "beef tartare",
    "beignets", "bibimbap", "bread pudding", "bruschetta", "caesar salad",
    "cannoli", "caprese salad", "carrot cake", "cheesecake", "cheese plate",
    "chicken curry", "chicken quesadilla", "chicken wings", "chocolate cake",
    "chocolate mousse", "churros", "clam chowder", "club sandwich", "crab cakes",
    "creme brulee", "cupcakes", "deviled eggs", "donuts", "dumplings",
    "edamame", "eggs benedict", "escargots", "falafel", "filet mignon",
    "fish and chips", "foie gras", "french fries", "french onion soup",
    "french toast", "fried calamari", "fried rice", "frozen yogurt",
    "garlic bread", "gnocchi", "greek salad", "grilled cheese sandwich",
    "grilled salmon", "guacamole", "gyoza", "hamburger", "hot dog",
    "hot and sour soup", "huevos rancheros", "hummus", "ice cream",
    "lasagna", "lobster bisque", "lobster roll", "macaroni and cheese",
    "macarons", "miso soup", "mussels", "nachos", "omelette", "onion rings",
    "oysters", "pad thai", "paella", "pancakes", "panna cotta", "peking duck",
    "pho", "pizza", "pork chop", "poutine", "prime rib", "pulled pork sandwich",
    "ramen", "ravioli", "red velvet cake", "risotto", "samosa", "sashimi",
    "scallops", "seaweed salad", "shrimp and grits", "spaghetti bolognese",
    "spaghetti carbonara", "spring rolls", "steak", "strawberry shortcake",
    "sushi", "tacos", "takoyaki", "tiramisu", "tuna tartare", "waffles"
]

def search_food(query: str) -> dict | None:
    """Search USDA for a food item and return the best match."""
    params = {
        "api_key": API_KEY,
        "query": query,
        "pageSize": 1,
        "dataType": ["Survey (FNDDS)", "SR Legacy"]  # Prefer standard reference data
    }
    
    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("foods"):
            return data["foods"][0]
        
        # Fallback: try branded if no standard data
        params["dataType"] = ["Branded"]
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("foods"):
            return data["foods"][0]
            
    except Exception as e:
        print(f"  ❌ Error searching '{query}': {e}")
    
    return None

def extract_nutrients(food: dict) -> dict:
    """Extract key nutrients from USDA food data."""
    nutrients = {}
    nutrient_map = {
        "Energy": "calories",
        "Protein": "protein",
        "Total lipid (fat)": "fat",
        "Carbohydrate, by difference": "carbs",
        "Fiber, total dietary": "fiber",
        "Total Sugars": "sugar",
        "Sodium, Na": "sodium"
    }
    
    for n in food.get("foodNutrients", []):
        name = n.get("nutrientName", "")
        if name in nutrient_map:
            nutrients[nutrient_map[name]] = {
                "value": n.get("value", 0),
                "unit": n.get("unitName", "")
            }
    
    return nutrients

def main():
    output_path = Path("health_butler/data/raw/usda_food101.json")
    
    print(f"📥 Downloading USDA data for {len(FOOD_101_CATEGORIES)} Food-101 categories...")
    print(f"   API Key: {API_KEY[:10]}...")
    
    results = []
    
    for i, food_name in enumerate(FOOD_101_CATEGORIES, 1):
        print(f"[{i:3}/{len(FOOD_101_CATEGORIES)}] Searching: {food_name}...", end=" ")
        
        food = search_food(food_name)
        
        if food:
            nutrients = extract_nutrients(food)
            
            result = {
                "query": food_name,
                "fdcId": food.get("fdcId"),
                "description": food.get("description", food_name),
                "dataType": food.get("dataType"),
                "nutrients": nutrients
            }
            results.append(result)
            
            cal = nutrients.get("calories", {}).get("value", "?")
            print(f"✓ {food.get('description', '')[:30]} ({cal} kcal)")
        else:
            # Use fallback estimated data
            result = {
                "query": food_name,
                "fdcId": None,
                "description": food_name.title(),
                "dataType": "Estimated",
                "nutrients": {}
            }
            results.append(result)
            print("⚠ Not found, using estimate")
        
        # Rate limiting
        time.sleep(0.3)
    
    # Save results
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    found = sum(1 for r in results if r["fdcId"])
    print(f"\n✅ Complete! {found}/{len(results)} foods found in USDA database")
    print(f"   Saved to: {output_path}")

if __name__ == "__main__":
    main()
