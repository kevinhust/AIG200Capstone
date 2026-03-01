# Architectural Decision Record: Phase 6 Perception & Gamification

## Context
As the Personal Health Butler AI moves towards a more professional and engaging product (v6.0), several technical bottlenecks needed addressing:
1. **Vision Precision**: YOLOv8 was sufficient for prototyping but lacked the localization accuracy needed for complex multi-ingredient dishes in 2026.
2. **User Insight**: Calorie counting alone is too abstract; users need to know their "Daily Value %" and "Remaining Budget".
3. **Engagement**: Static bots have low retention; interactive, gamified features are necessary for habit formation.

## Decision
Upgrade the system to **Version 6.0: Performance & Play**, implementing the following architectural changes:

### 1. YOLO11 Integration
- **Action**: Replace `yolov8n.pt` with `yolo11n.pt`.
- **Rationale**: YOLO11 provides superior accuracy-to-latency ratio, ensuring perception remains under the 5s threshold while improving ingredient localization.

### 2. Nutritional Budgeting Engine
- **Action**: Implement Mifflin-St Jeor TDEE calculation and personal macro budgets in the `NutritionAgent`.
- **Rationale**: Provides grounded, personalized feedback. Instead of just "400 calories", the system says "400 calories (18% of your daily goal)".

### 3. Gamified Interaction Loop (Food Roulette🎰)
- **Action**: Introduction of `RouletteView`—an animated, budget-aware meal suggestion engine.
- **Rationale**: Solves "decision fatigue" while ensuring recommendations are always compliant with the user's remaining calories for the day.

### 4. Scheduled Proactive Triggers
- **Action**: Add 11:30 and 17:30 pre-meal reminder task loops.
- **Rationale**: Increases DAU (Daily Active Users) by providing value *before* the user decides what to eat.

## Status
✅ **Accepted & Implemented** (2026-03-01)

## Consequences
- **Positive**: significantly higher user engagement, more accurate food logging, and professional-grade UI.
- **Positive**: Unified API key strategy reduces configuration errors.
- **Neutral**: Slightly larger model weight (`yolo11n.pt` instead of `yolov8n.pt`), but inference time remains stable.

---
*Reference: [system_upgrade.md](../../../system_upgrade.md)*
