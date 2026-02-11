#!/usr/bin/env python3
"""
Download common everyday foods from USDA API.
Extends the Food-101 dataset with basic ingredients and common foods.
"""

import json
import time
import requests
from pathlib import Path

API_KEY = "HI1Zkn5obOSoY7w1D1GwZVy1jmSUsmBbAfuyO0LH"
BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Common everyday foods by category
COMMON_FOODS = {
    "fruits": [
        "apple", "banana", "orange", "strawberry", "blueberry", "grape",
        "watermelon", "mango", "pineapple", "peach", "pear", "cherry",
        "kiwi", "lemon", "lime", "grapefruit", "avocado", "coconut",
        "raspberry", "blackberry", "cantaloupe", "honeydew melon"
    ],
    "vegetables": [
        "broccoli", "carrot", "spinach", "lettuce", "tomato", "cucumber",
        "onion", "garlic", "potato", "sweet potato", "corn", "peas",
        "green beans", "asparagus", "cauliflower", "cabbage", "kale",
        "celery", "bell pepper", "mushroom", "zucchini", "eggplant",
        "brussels sprouts", "artichoke", "beet", "radish"
    ],
    "proteins": [
        "chicken breast", "chicken thigh", "beef steak", "ground beef",
        "pork chop", "bacon", "ham", "turkey breast", "lamb chop",
        "salmon fillet", "tuna", "shrimp", "lobster", "crab", "cod",
        "tilapia", "egg", "tofu", "tempeh", "black beans", "kidney beans",
        "chickpeas", "lentils", "almonds", "peanuts", "walnuts"
    ],
    "dairy": [
        "milk", "cheese", "yogurt", "butter", "cream cheese", "sour cream",
        "cottage cheese", "mozzarella", "cheddar cheese", "parmesan cheese",
        "cream", "ice cream", "greek yogurt", "whipped cream"
    ],
    "grains": [
        "white rice", "brown rice", "pasta", "bread", "whole wheat bread",
        "oatmeal", "quinoa", "couscous", "tortilla", "bagel", "croissant",
        "muffin", "cereal", "granola", "crackers", "noodles"
    ],
    "beverages": [
        "coffee", "tea", "orange juice", "apple juice", "milk",
        "soda", "beer", "wine", "smoothie", "protein shake"
    ],
    "snacks": [
        "chips", "popcorn", "pretzels", "cookies", "chocolate",
        "candy", "granola bar", "trail mix", "nuts", "dried fruit"
    ],
    "condiments": [
        "ketchup", "mustard", "mayonnaise", "soy sauce", "olive oil",
        "vinegar", "honey", "maple syrup", "salsa", "hot sauce",
        "ranch dressing", "barbecue sauce", "peanut butter", "jam"
    ]
}

def search_food(query: str) -> dict | None:
    """Search USDA for a food item."""
    # Try without dataType filter first (simpler, more reliable)
    params = {
        "api_key": API_KEY,
        "query": query,
        "pageSize": 1
    }
    
    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("foods"):
            return data["foods"][0]
            
    except Exception as e:
        print(f"  ❌ {e}")
    
    return None

def extract_nutrients(food: dict) -> dict:
    """Extract key nutrients."""
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
    output_path = Path("health_butler/data/raw/usda_common_foods.json")
    
    all_foods = []
    for category in COMMON_FOODS.values():
        all_foods.extend(category)
    
    # Remove duplicates
    all_foods = list(set(all_foods))
    
    print(f"📥 Downloading USDA data for {len(all_foods)} common foods...")
    
    results = []
    
    for i, food_name in enumerate(sorted(all_foods), 1):
        print(f"[{i:3}/{len(all_foods)}] {food_name}...", end=" ", flush=True)
        
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
            print(f"✓ ({cal} kcal)")
        else:
            print("⚠ Not found")
        
        time.sleep(0.25)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    found = len(results)
    print(f"\n✅ Complete! {found}/{len(all_foods)} foods found")
    print(f"   Saved to: {output_path}")

if __name__ == "__main__":
    main()
