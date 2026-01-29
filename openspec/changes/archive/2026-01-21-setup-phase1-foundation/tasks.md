## 1. Environment & Data Setup
- [x] 1.1 Configure Project Structure: Ensure `src/agents`, `src/tools`, `data/raw`, `data/processed` exist.
- [x] 1.2 Data Ingestion Script (USDA): Create `src/scripts/ingest_usda.py` to download/load USDA JSON.
- [x] 1.3 Data Ingestion Script (Food-101): Create `src/scripts/setup_food101.py` to prepare image dataset.

## 2. Tool Implementation (Baseline)
- [x] 2.1 RAG Tool: Implement `src/tools/rag_tool.py` with `add_documents` and `query` methods using FAISS.
- [x] 2.2 Vision Tool: Implement `src/tools/vision_tool.py` using YOLO26 (or placeholder equivalent for start).

## 3. Agent Implementation (Skeleton)
- [x] 3.1 Nutrition Agent: Create `src/agents/nutrition_agent.py` inheriting base, with system prompt for nutrition analysis.
- [x] 3.2 Fitness Agent: Create `src/agents/fitness_agent.py` inheriting base, with system prompt for exercise advice.
- [x] 3.3 Coordinator Agent: Create `src/agents/coordinator_agent.py` capable of routing to Nutrition/Fitness.

## 4. Integration Verification
- [x] 4.1 Swarm Config: Update `src/swarm.py` or create `src/health_swarm.py` to register new agents.
- [x] 4.2 Test Script: Create `tests/test_phase1.py` to verify agent instantiation and basic tool calls.

## 5. Refactoring (User Request)
- [x] 5.1 Create App Directory: Create `src/health_butler` for project-specific code.
- [x] 5.2 Move Files: Move custom agents, tools, scripts into `src/health_butler`.
- [x] 5.3 Update Imports: Fix imports in Moved files and Tests.
