# AI Capstone Project Workspace

## Project: Personal Health Butler AI (Prototype)

> **Welcome Developers!**
> This repository uses a specialized **Antigravity Scaffold** designed for efficient AI Agent development.
> Please read this guide carefully before contributing.

---

## 1. Directory Structure

This workspace is divided into two distinct areas:

```
├── health_butler/           # 🍎 PRODUCT_ROOT: The core application functionality
│   ├── agents/              # - Agent definitions (Coordinator, Nutrition, Fitness)
│   ├── tools/               # - Capabilities (ViT Vision, RAG Engine)
│   ├── scripts/             # - Data ingestion and setup scripts
│   ├── app.py               # - Streamlit UI Entrypoint
│   └── README.md            # - Product Specific Documentation
│
├── src/                     # 🛠️ SCAFFOLD_ROOT: Shared utilities & base classes
│   └── agents/              # - BaseAgent, RouterAgent generic logic
│
├── openspec/                # 📋 SPEC_ROOT: Requirements & Change Management
│   ├── specs/               # - Functional requirements (Foundation, Prototype)
│   └── changes/             # - Proposed and archived changes
│
├── docs/                    # 📚 DOCS: Architecture (L1-L4), Research, and Milestones
│
└── tests/                   # ✅ TEST: Integration and Unit tests
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
The **Phase 2 Prototype** interface is built with Streamlit.
```bash
streamlit run health_butler/app.py
```
> **Note**: This launches the UI at `http://localhost:8501`.

---

## 3. Development Workflow

### 3.1 Making Changes (OpenSpec)
We strictly track requirements via OpenSpec.
1.  **Define**: Create a proposal in `openspec/changes/<feature-name>/proposal.md`.
2.  **Plan**: Define tasks in `openspec/changes/<feature-name>/tasks.md`.
3.  **Implement**: Write code in `health_butler/`.
4.  **Archive**: Run `openspec archive <feature-name>` to finalize.

### 3.2 Adding Agents
-   Create new agents in `health_butler/agents/`.
-   Inherit from `src.agents.base_agent.BaseAgent`.

### 3.3 Adding Tools
-   Create tool classes in `health_butler/tools/`.
-   Ensure they return standard dict-based outputs `{"status": "...", "data": ...}`.

---

## 4. Tech Stack (Phase 2)
-   **Orchestration**: OpenAI Swarm (Stateless Handoffs)
-   **Vision**: Vision Transformer (ViT-Base) using HuggingFace
-   **RAG**: ChromaDB + SentenceTransformers
-   **UI**: Streamlit

---

## 5. Collaboration
-   **Branching**: Development happens on feature branches (e.g., `feature/login`).
-   **Sync**: Push to `origin/Kevin` (or your personal branch) frequently.
-   **Review**: Ensure `tests/` pass before merging.
