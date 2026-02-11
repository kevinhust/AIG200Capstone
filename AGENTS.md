<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Agent Guide

This repo is the **Personal Health Butler AI** project, built on the Antigravity Workspace Template.

## Must-Read Files (Before Any Work)

| File | Purpose |
|------|---------|
| `mission.md` | Project mission and success metrics |
| `.antigravity/rules.md` | Core agent behavior + coding standards |
| `.antigravity/mission.md` | Detailed project goals (copy of mission.md) |
| `CONTEXT.md` | Project architecture overview |
| `.context/coding_style.md` | Python coding standards |
| `.context/system_prompt.md` | AI assistant persona |
| `openspec/AGENTS.md` | When planning/spec/change work is needed |

## Artifact-First Workflow

For non-trivial tasks:
1. **Plan**: Create `artifacts/plans/plan_[task_id].md`
2. **Execute**: Implement the code
3. **Verify**: Run `pytest` and store logs in `artifacts/logs/`
4. **Update**: Mark tasks complete in `openspec/changes/*/tasks.md`

## Build / Lint / Test Commands

### Setup
```bash
source capstoneenv/bin/activate
pip install -r requirements.txt
```

### Run App
```bash
streamlit run health_butler/app.py
```

### Run Agent (standalone)
```bash
python -m health_butler.main
```

### Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agent.py -v

# With coverage
pytest --cov=health_butler tests/
```

### Lint / Format
```bash
# Syntax check
python -m py_compile health_butler/**/*.py

# Type check (optional)
mypy health_butler/
```

## Code Style (Python)

- **Type hints are required** for all function signatures
- **Docstrings are required** (Google-style with Args, Returns, Raises)
- **Use Pydantic** for data models
- **External API calls** must be wrapped in tools
- **Logging**: Use `logging` module, not `print()`

See `.context/coding_style.md` for details.

## Project Structure

```
AIG200Capstone/
├── .antigravity/          # Agent rules and mission
├── .context/              # Auto-injected context files
├── artifacts/             # Plans, logs, outputs
├── health_butler/         # 🍎 PRODUCT CODE
│   ├── agents/            # Nutrition, Fitness agents
│   ├── coordinator/       # Coordinator agent
│   ├── data_rag/          # RAG pipeline
│   ├── cv_food_rec/       # Vision tools
│   ├── ui_streamlit/      # Streamlit UI
│   ├── swarm.py           # HealthSwarm orchestrator
│   └── main.py            # Entry point
├── src/                   # 🛠️ Scaffold base classes
├── openspec/              # Spec-driven development
├── tests/                 # Pytest tests
└── docs/                  # Documentation
```

## Architecture

```
User Input → HealthSwarm → CoordinatorAgent
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
             NutritionAgent       FitnessAgent
                    ↓
            ┌───────┴───────┐
            ↓               ↓
        VisionTool      RagTool
         (ViT)        (ChromaDB)
```

## Testing & Reliability

- Use `pytest` fixtures
- Keep tests deterministic (no external network calls in tests)
- Store test logs in `artifacts/logs/`
- All agents should have unit tests

## Notes for AI Agents

1. Follow "Think → Act → Reflect" workflow
2. Avoid destructive commands (`rm -rf`, etc.)
3. For spec/proposal requests, follow OpenSpec flow before coding
4. Run `openspec validate --strict` before implementing changes
5. Update `mission.md` if scope changes significantly
