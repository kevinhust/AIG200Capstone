# Change: Prototype Agent Integration

## Why
To enable the "Swarm" architecture defined in the L4 Technology Architecture. Currently, the UI (`app.py`) calls tools directly. We need to shift this responsibility to the Agents (`NutritionAgent`, `FitnessAgent`) and use the `CoordinatorAgent` (Router) to manage the workflow. This completes the logic layer of Phase 2.

## What Changes
- **Agent Logic**:
  - `NutritionAgent`: Update to use `VisionTool` for image analysis and `RagTool` for macro lookup.
  - `FitnessAgent`: Update to provide workout recommendations (LLM-based).
- **Orchestration**:
  - Create `health_butler/swarm.py`: A specialized `SwarmOrchestrator` that manages the Health Butler agents.
- **UI Integration**:
  - Update `health_butler/app.py`: Replace direct tool usage with `swarm.execute(user_input)`.

## Impact
- **Architecture**: Moves from "Monolithic Script" (app.py) to "Agentic Swarm".
- **Extensibility**: Easier to add new agents (e.g., Mental Health) later.
- **Experience**: The "Thinking" process in the UI will reflect Agent delegation.
