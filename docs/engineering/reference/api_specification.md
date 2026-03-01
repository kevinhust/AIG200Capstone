# API Configuration Specification (v2026.03)

## 🔑 Overview
This document defines the standardized API configuration for the Personal Health Butler AI. Starting from **v6.0**, we have unified our environment variable strategy to reduce conflicts and improve developer experience.

## 🛡️ Core API Key: `GOOGLE_API_KEY`
The system has been standardized to use `GOOGLE_API_KEY` as the primary identifier for Google GenAI services (Gemini).

### Configuration Rules
1. **Primary Key**: `GOOGLE_API_KEY`
2. **Fallback Support**: For backward compatibility, the system gracefully handles `GEMINI_API_KEY` via Pydantic `AliasChoices`.
3. **Precedence**:
   - Explicitly provided `api_key` in constructor.
   - `GOOGLE_API_KEY` environment variable.
   - `GEMINI_API_KEY` environment variable (Fallback).

### Example `.env` Configuration
```env
# Google GenAI Settings (Standardized)
GOOGLE_API_KEY=your_google_ai_studio_key_here

# Model Selection
GEMINI_MODEL_NAME=gemini-2.5-flash
```

---

## 🏗️ Implementation Details

### 1. Configuration Center (`src/config.py`)
All agents and tools MUST consume API keys through the centralized `settings` object:
```python
from src.config import settings
api_key = settings.GOOGLE_API_KEY
```

### 2. Multi-Agent Standardization
| Component | Key Source | Behavior |
|-----------|------------|----------|
| `BaseAgent` | `settings.GOOGLE_API_KEY` | Unified client initialization. |
| `GeminiVisionEngine` | `settings.GOOGLE_API_KEY` | Standardized for vision analysis. |
| `NutritionAgent` | `settings.GOOGLE_API_KEY` | Inherits from Base + local safety net. |

---

## 🚨 Troubleshooting
- **Error**: `Both GOOGLE_API_KEY and GEMINI_API_KEY are set.`
  - **Reason**: The SDK detects redundant variables.
  - **Resolution**: Remove `GEMINI_API_KEY` from your `.env` and only keep `GOOGLE_API_KEY`.
- **Error**: `API Key missing`
  - **Reason**: The key is not present in `.env` or environment.
  - **Resolution**: Ensure the variable name is exactly `GOOGLE_API_KEY`.

---
*Last Updated: 2026-03-01 | Antigravity Engine v6.0*
