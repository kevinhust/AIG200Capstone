from data_rag.simple_rag_tool import SimpleRagTool
import logging

logging.basicConfig(level=logging.INFO)

print("--- Testing Hybrid Cache SimpleRagTool ---")
tool = SimpleRagTool()

print("\n--- Testing Search 'biceps' ---")
res = tool.search_exercises("biceps", limit=2)
for r in res:
    print(f"- {r.get('name')} | Category: {r.get('category')}")

print("\n--- Testing Safety Routing (Dynamic Risk: 'fried') ---")
safe_res = tool.get_safe_recommendations("jump", user_conditions=[], dynamic_risks=["fried"])
print(f"Safety Warnings: {safe_res.get('safety_warnings')}")
print(f"Dynamic Adjustments: {safe_res.get('dynamic_adjustments')}")
print("Allowed Exercises:")
for r in safe_res.get('safe_exercises', []):
    print(f"- {r.get('name')}")
