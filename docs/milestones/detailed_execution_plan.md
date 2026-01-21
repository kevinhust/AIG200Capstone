# AI Capstone Execution Plan: Personal Health Butler AI

**Project**: Personal Health Butler AI
**Team**: Group 5
**Start Date**: Week 1 (Jan 20, 2026)

This document aligns the project's internal development roadmap with the course's Milestone requirements.

---

## 📅 High-Level Roadmap

| Phase | Duration | Course Milestone | Key Goal |
|-------|----------|------------------|----------|
| **Phase 1: Foundation** | Weeks 1-3 | **Milestone 1 (Week 3)** | Project definition, data pipeline setup, MVP design. |
| **Phase 2: Prototyping** | Weeks 4-6 | **Milestone 2 (Week 6)** | Functional prototypes of Core Agents (Nutrition/CV) and Data Pipeline. |
| **Phase 3: Integration** | Weeks 7-9 | **Milestone 3 (Week 9)** | Integrated System (Swarm + UI) running in Docker. |
| **Phase 4: Polish & Launch**| Weeks 10-12| **Final Presentation** | Feature freeze, testing, Cloud Run deployment. |

---

## 🚀 Phase 1: Foundation (Weeks 1-3)
**Target**: Milestone 1 Check-in

### Goals
- Finalize PRD and Architecture (Done).
- Set up development environment (Repo, Antigravity Scaffold).
- **Data**: Ingest USDA data sample & setup Food-101.
- **Tech**: Verify Swarm Orchestrator locally.

### Task Breakdown

#### Week 1: Setup & Definition
- [x] Integrate Antigravity Scaffold.
- [x] Finalize PRD/Architecture Docs.
- [ ] **Infrastructure**:
  - [ ] Configure `src/agents/` structure.
  - [ ] Set up `.env` and API keys (Gemini, LangSmith).
- [ ] **Data Plan**:
  - [ ] Download USDA FoodData Central sample (JSON).
  - [ ] Download Food-101 dataset (small sample for testing).

#### Week 2: Initial Pipelines
- [ ] **RAG Pipeline (Baseline)**:
  - [ ] Create `src/tools/rag_tool.py`: Script to load USDA JSON -> Text Chunks -> FAISS Index.
  - [ ] Verify retrieval relevance with 5 sample queries.
- [ ] **CV Pipeline (Baseline)**:
  - [ ] Create `src/tools/vision_tool.py`: Script to load YOLO26-Nano and run inference on 1 static image.

#### Week 3: Milestone 1 Preparation
- [ ] **Agent Skeleton**:
  - [ ] Implement `NutritionAgent` class (mocked logic).
  - [ ] Implement `CoordinatorAgent` class (mocked routing).
- [ ] **Milestone Artifacts**:
  - [ ] Presentation Deck: Problem, Solution, Tech Stack, Timeline.
  - [ ] Repo Walkthrough: Show scaffold and data samples.

---

## 🛠️ Phase 2: Prototyping (Weeks 4-6)
**Target**: Milestone 2 Check-in

### Goals
- Functional "Nutrition Service" (Image -> Calories).
- Functional "RAG Service" (Text -> Accurate Content).
- Basic Streamlit UI.

### Task Breakdown

#### Week 4: Core Logic
- [ ] **CV Model**:
  - [ ] Fine-tune YOLO26 on Food-101 (or find best pre-trained weights).
  - [ ] Wrap YOLO inference in `NutritionAgent`.
- [ ] **RAG Enhancement**:
  - [ ] Ingest full USDA dataset (or large subset).
  - [ ] Optimize chunking strategy (keep nutrition table intact).

#### Week 5: Agent Development
- [ ] **Nutrition Agent v1**:
  - [ ] Input: Image Path.
  - [ ] Logic: CV detection -> RAG lookup -> Summarize.
  - [ ] Output: JSON with calories/macros.
- [ ] **Fitness Agent v1**:
  - [ ] Rule-based logic: "If calories > X, suggest Walk".

#### Week 6: MVP Interface & MS2 Demo
- [ ] **Streamlit UI v0.1**:
  - [ ] File Uploader.
  - [ ] Display recognized food tags.
  - [ ] Display raw agent output (JSON/Text).
- [ ] **Milestone 2 Artifacts**:
  - [ ] Demo Video: Image upload -> Console Log -> Response.
  - [ ] Data Report: USDA coverage stats, YOLO accuracy metrics (mAP).

---

## 🔗 Phase 3: Integration (Weeks 7-9)
**Target**: Milestone 3 Check-in

### Goals
- Full Multi-Agent Swarm working.
- Docker containerization.
- End-to-End user flow.

### Task Breakdown

#### Week 7: Swarm Orchestration
- [ ] **Coordinator Implementation**:
  - [ ] Use LLM to route intent ("Is this a food photo?" vs "Is this a question?").
  - [ ] Connect `SwarmOrchestrator` to Streamlit UI.
- [ ] **Session Management**:
  - [ ] Implement short-term memory in `CoordinatorAgent`.

#### Week 8: System Integration
- [ ] **End-to-End Test**:
  - [ ] User uploads photo -> Coordinator -> Nutrition Agent -> Coordinator -> User.
  - [ ] User asks follow-up -> Coordinator -> Nutrition/Fitness Agent -> User.
- [ ] **Dockerization**:
  - [ ] Create `Dockerfile` (optimized for Torch/CPU).
  - [ ] Create `docker-compose.yml` for local services.

#### Week 9: Deployment Prep & MS3 Demo
- [ ] **Cloud Setup**:
  - [ ] Push to Google Container Registry (GCR).
  - [ ] Deploy to Cloud Run (Service 1).
- [ ] **Milestone 3 Artifacts**:
  - [ ] Live Demo URL (or local Docker demo).
  - [ ] Integration Test Report.

---

## ✨ Phase 4: Polish (Weeks 10-12)
**Target**: Final Presentation

#### Week 10: Feedback Loop
- [ ] User testing (Internal team).
- [ ] Fix latency issues (e.g., enable caching for RAG).
- [ ] Handle edge cases (non-food images).

#### Week 11: Final Presentation Prep
- [ ] Create Final Report (PDF).
- [ ] Record high-quality demo video.
- [ ] Prepare pitch deck.

#### Week 12: buffer / Submission
- [ ] Code cleanup & documentation.
- [ ] Final submission.
