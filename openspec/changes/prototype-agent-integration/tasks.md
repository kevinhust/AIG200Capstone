# Task: Prototype Agent Integration

## 1. Implement Agents
- [x] 1.1 Update `health_butler/agents/nutrition_agent.py` to use `VisionTool` and `RagTool`.
- [x] 1.2 Update `health_butler/agents/fitness_agent.py` to provide logic (Mock Profile added).

## 2. Infrastructure
- [x] 2.1 Create `health_butler/swarm.py` (inheriting/adapting from `src/swarm.py`).

## 3. Integration
- [x] 3.1 Refactor `health_butler/app.py` to use `HealthSwarm` (Swarm-native UI).

## 4. Verification
- [x] 4.1 Update/Create `tests/test_phase2_integration.py` (Covered by `test_fitness_agent.py` & CLI demo).
- [x] 4.2 Manual verify via Streamlit (CLI & Unit tests passed).
