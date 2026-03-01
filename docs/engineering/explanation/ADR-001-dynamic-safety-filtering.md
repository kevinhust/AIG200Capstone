# ADR-001: Dynamic Safety Filtering System

## Status
**Accepted** (2026-02-28)

## Context

The Health Butler AI system needed a mechanism to provide safe exercise recommendations based on real-time nutritional analysis. Users often consume high-risk foods (fried, high-sugar, processed) and then request exercise advice that could be unsafe given their recent intake.

### Problem Statement
1. Static health conditions (e.g., knee injury) are handled, but dynamic risks from recent meals were not considered
2. Users could request high-intensity exercises immediately after eating heavy meals
3. No automated safety adjustments based on visual food analysis

## Decision

We implemented a **Dynamic Safety Filtering System** with the following components:

### 1. Health Memo Protocol
- **Location**: `src/coordinator/coordinator_agent.py`
- Extracts `visual_warnings` and `health_score` from Nutrition Agent results
- Injects context into Fitness Agent task descriptions
- Supports multilingual intent detection (EN/CN)

### 2. Dynamic Risk Filtering in RAG
- **Location**: `src/data_rag/simple_rag_tool.py`
- New parameter: `dynamic_risks: List[str]`
- Risk-to-intensity mapping:
  ```python
  DYNAMIC_RISK_BLOCKS = {
      "fried": {"blocked": HIGH_INTENSITY_KEYWORDS, "reason": "..."},
      "high_oil": {"blocked": HIGH_INTENSITY_KEYWORDS, "reason": "..."},
      "high_sugar": {"blocked": HIGH_INTENSITY_KEYWORDS + MODERATE_INTENSITY_KEYWORDS, ...},
      "processed": {"blocked": HIGH_INTENSITY_KEYWORDS, "reason": "..."}
  }
  ```

### 3. Double-Validation in FitnessAgent
- **Location**: `src/agents/fitness/fitness_agent.py`
- Extracts warnings from task description
- Validates recommendations against warnings
- Replaces blocked exercises with safe alternatives

### 4. BR-001 Safety Disclaimer
```
⚠️ Due to the recent consumption of fried/high-sugar food,
I've adjusted your plan to lower intensity for your safety.
```

## Technical Architecture

```
User Input: "I just ate a donut, can I go for a run?"
                    │
                    ▼
         ┌─────────────────────┐
         │   CoordinatorAgent   │
         │  - Intent Detection  │
         │  - Route to Nutrition│
         └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   NutritionAgent    │
         │  - Image Analysis   │
         │  - visual_warnings  │
         │  - health_score     │
         └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   HealthMemo        │
         │  {warnings: [...],  │
         │   score: 2,         │
         │   calories: 450}    │
         └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   FitnessAgent      │
         │  - Extract warnings │
         │  - RAG filtering    │
         │  - Double-validate  │
         │  - BR-001 disclaimer│
         └─────────────────────┘
                    │
                    ▼
    Output: Brisk Walking, Light Stretching
            (Fast Run BLOCKED)
```

## Consequences

### Positive
- ✅ Automated safety adjustments based on real-time nutrition analysis
- ✅ Consistent application of safety rules regardless of user request
- ✅ Clear audit trail via BR-001 disclaimer
- ✅ Multilingual support (EN/CN)
- ✅ Latency < 5s for full pipeline

### Negative
- ⚠️ Requires valid nutrition analysis (depends on image quality)
- ⚠️ May over-block exercises in edge cases
- ⚠️ Additional latency from context extraction

### Mitigations
- Fallback to neutral recommendations when nutrition data unavailable
- Configurable intensity thresholds in `DYNAMIC_RISK_BLOCKS`
- Memory cleanup via `finally` blocks (BR-005 compliance)

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| BR-001 Safety Disclaimer | ✅ | Automatically included when adjustments made |
| BR-005 Ephemeral Storage | ✅ | Image objects closed in `finally` blocks |
| KPI: <5s latency | ✅ | Typical: 3-4s for full pipeline |

## Testing

- `tests/test_health_memo_english.py` - English intent detection
- `tests/test_dynamic_safety_filter.py` - Dynamic filtering validation
- `tests/test_final_system_hardening.py` - Stress testing & edge cases

## References

- [L2-Application-Architecture.md](./L2-Application-Architecture.md)
- [safety_protocols.json](../../data/rag/safety_protocols.json)
