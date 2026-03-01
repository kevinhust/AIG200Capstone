# AI Capstone Project Workspace

## Project: Personal Health Butler AI (Prototype)

> **Welcome Developers!**
> This repository uses a specialized **Antigravity Scaffold** designed for efficient AI Agent development.
> Please read this guide carefully before contributing.

---

## 1. Directory Structure

This workspace is divided into two distinct areas:

```
├── agents/          # specialist agents (nutrition, fitness)
├── coordinator/     # main router and logic
├── cv_food_rec/      # Computer Vision food recognition
├── data/            # Persistence (SQLite, JSON, Embeddings)
├── data_rag/        # RAG Logic and Tools
├── discord_bot/     # Discord Transport and Bot implementation
├── scripts/         # Ingestion and setup scripts
├── src/             # Core base classes from scaffolding
├── tests/           # Comprehensive test suite
├── Dockerfile       # Cloud Run deployment
└── README.md        # This file
```

---

## 2. Quick Start

### 2.1 Dependencies
We use `pip` for this prototype phase.
```bash
# 1. Activate Environment (Assuming capstoneenv)
source capstoneenv/bin/activate  # or similar

# 2. Install Requirements
pip install -r requirements.txt
```

### 2.2 Running the App
The application currently runs as a Discord Bot via `src/discord_bot/bot.py` or the `src.discord_bot.bot` module.
```bash
python -m src.discord_bot.bot
```
> **Note**: Ensure your `.env` contains the required Discord Token and Google API Key.

---

## 3. Development Workflow

### 3.1 Making Changes (OpenSpec)
We strictly track requirements via OpenSpec.
1.  **Define**: Create a proposal in `openspec/changes/<feature-name>/proposal.md`.
2.  **Plan**: Define tasks in `openspec/changes/<feature-name>/tasks.md`.
3.  **Implement**: Write code in root.
4.  **Archive**: Run `openspec archive <feature-name>` to finalize.

### 3.2 Adding Agents
-   Create new agents in `agents/`.
-   Inherit from `src.agents.base_agent.BaseAgent`.

### 3.3 Adding Tools
-   Create tool modules in root or appropriate subdirectories.
-   Ensure they return standard dict-based outputs `{"status": "...", "data": ...}`.

---

## 4. Tech Stack (Phase 8)
-   **Orchestration**: Google GenAI Structured Routing
-   **Vision**: Gemini 2.5 Flash via `google.genai` SDK (w/ YOLO hints)
-   **RAG**: SimpleRagTool for JSON-based safety filtering
-   **UI**: Discord Bot with 5-step Profile Onboarding

---

## 5. Collaboration
-   **Branching**: Development happens on feature branches (e.g., `feature/login`).
-   **Sync**: Push to `origin/Kevin` (or your personal branch) frequently.
-   **Review**: Ensure `tests/` pass before merging.
