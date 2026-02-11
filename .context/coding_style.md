# Health Butler Coding Standards & Best Practices

## Architecture
1. **Tool Isolation**: All external interactions (API calls, file I/O, model inference) MUST be encapsulated in tool classes within:
   - `health_butler/cv_food_rec/` - Vision tools
   - `health_butler/data_rag/` - RAG tools
   - `src/tools/` - Shared utilities

2. **Pydantic Everywhere**: Use `pydantic` models for function arguments and return values where complex data is involved.
   - *Why?* Ensures strict schema validation and clear type definitions.

3. **Agent Inheritance**: All agents MUST inherit from `src.agents.base_agent.BaseAgent`.

## Python Style

### Type Hints (Mandatory)
```python
# ✅ Correct
def analyze_food(image_path: str, top_k: int = 3) -> List[Dict[str, Any]]:
    ...

# ❌ Wrong
def analyze_food(image_path, top_k=3):
    ...
```

### Docstrings (Google-style, Mandatory)
```python
def analyze_food(image_path: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Analyze food items in an image using ViT model.

    Args:
        image_path: Path to the image file.
        top_k: Number of top predictions to return.

    Returns:
        List of dicts containing label, confidence, and metadata.

    Raises:
        FileNotFoundError: If image_path does not exist.
        ModelError: If the ViT model fails to load.
    """
    ...
```

### Imports Order
```python
# 1. Standard library
import os
import json
from typing import List, Dict, Any

# 2. Third-party
import torch
from pydantic import BaseModel

# 3. Local
from src.agents.base_agent import BaseAgent
from health_butler.data_rag.rag_tool import RagTool
```

## Agent Design Patterns

1. **Stateless Tools**: Tools should be stateless. Pass necessary context as arguments.

2. **Fail Gracefully**: Tools should return error dicts rather than raising exceptions:
   ```python
   # ✅ Correct
   if not image_path.exists():
       return [{"error": "Image file not found"}]
   
   # ❌ Wrong
   raise FileNotFoundError(f"Image not found: {image_path}")
   ```

3. **Logging**: Use Python logging, not print statements:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info(f"Processing image: {image_path}")
   ```

## Project-Specific Rules

### Health Butler Agents
| Agent | Location | Responsibility |
|-------|----------|----------------|
| CoordinatorAgent | `health_butler/coordinator/` | Intent routing |
| NutritionAgent | `health_butler/agents/nutrition/` | Food analysis |
| FitnessAgent | `health_butler/agents/fitness/` | Exercise advice |

### Data Flow
```
User Input → Coordinator → [Nutrition/Fitness] → Tools → Response
                                   ↓
                            VisionTool (ViT)
                            RagTool (ChromaDB)
```

### RAG Data Sources
- USDA FoodData Central (primary)
- Estimated values (fallback)
- All data in `health_butler/data/`
