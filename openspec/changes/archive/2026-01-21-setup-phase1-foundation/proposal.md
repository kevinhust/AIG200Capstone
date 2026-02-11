# Change: Setup Phase 1 Foundation

## Why
To establish the foundational architecture for the "Personal Health Butler AI" capstone project, aligning with Course Milestone 1 requirements. This foundation is necessary to support subsequent development of the Multi-Agent Swarm (Coordinator, Nutrition, Fitness) and the key pipelines (RAG, CV).

## What Changes
- **Agent Architecture**:
  - Implement `NutritionAgent` (Skeleton).
  - Implement `FitnessAgent` (Skeleton).
  - Implement `CoordinatorAgent` (Skeleton/Router Logic).
- **Tooling**:
  - Create `RagTool` (Baseline: USDA Data Load -> FAISS).
  - Create `VisionTool` (Baseline: YOLO Inference).
- **Data Ingestion**:
  - Scripts to download and index USDA FoodData Central sample.
  - Setup for Food-101 dataset usage.

## Impact
- **Specs**: New `foundation` capability.
- **Code**:
  - New files in `src/agents/`.
  - New files in `src/tools/`.
  - New configuration in `.env` (templates).
