# Personal Health Butler AI

> 🤖 A Multi-Agent AI Nutrition & Fitness Assistant (MVP v1.1)

## 📋 Project Overview

The **Personal Health Butler** is an AI-powered nutrition assistant that leverages **Multi-Agent Architecture** and **Retrieval-Augmented Generation (RAG)** to provide personalized, evidence-based wellness guidance.

**Core Value**: Snap a photo of your meal -> Get instant calorie/macro analysis + science-backed advice.

**Team**: Group 5 (Allen, Wangchuk, Aziz, Kevin)  
**Course**: AI Graduate Certificate Capstone (2026)  
**Duration**: 14 Weeks

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Coordinator Agent                               │
│                    (LangGraph Orchestration)                         │
└───┬───────────────┬───────────────┬───────────────┬─────────────────┘
    │               │               │               │
┌───▼───┐     ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
│Nutrition│   │  Fitness  │   │  RAG      │   │   User    │
│ Agent  │    │   Agent   │   │ Pipeline  │   │  Session  │
└───┬────┘    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
    │               │               │               │
    └───────────────┴───────┬───────┴───────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                    Shared Services Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ RAG VectorDB│  │  CV Models  │  │ LLM Reasoner│                  │
│  │   (FAISS)   │  │   (YOLO26)  │  │(Gemini 2.5) │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
AIG200Capstone/
├── docs/                           # 📚 Design Documents
│   ├── PRD-Personal-Health-Butler.md    # Product Requirements (v1.1)
│   ├── L1-Business-Architecture.md      # Business Processes
│   ├── L2-Application-Architecture.md   # System Components
│   ├── L3-Data-Architecture.md          # Data & Privacy
│   └── L4-Technology-Architecture.md    # Tech Stack (2026)
│
├── src/                            # Source Code (Modular)
│   ├── data_rag/                   # Data Pipeline
│   ├── cv_food_rec/                # Vision Models
│   ├── agents/                     # Agent Logic
│   └── ui_streamlit/               # Frontend
│
└── README.md                       # This file
```

---

## 🛠️ Tech Stack (MVP)

| Category | Technologies |
|----------|-------------|
| Agent Framework | **LangGraph** |
| LLM | **Gemini 2.5 Flash** (Primary), DeepSeek (Fallback) |
| Computer Vision | **YOLO26-Nano** |
| Vector Database | **FAISS** (Local) |
| Embedding | **e5-large-v2** |
| Deployment | **Cloud Run** (Serverless) |

---

## 👥 Team & Modules

| Member | Role | Key Modules |
|--------|------|-------------|
| **Allen** | Orchestration Lead | Coordinator, Integration |
| **Wangchuk** | CV/UI Lead | Food Recognition, Streamlit |
| **Aziz** | Data/RAG Lead | Knowledge Pipeline, USDA Data |
| **Kevin** | Fitness/Docs Lead | Fitness Agent, Documentation |

---

## 📅 Milestones

| Milestone | Week | Focus | Status |
|-----------|------|-------|--------|
| **MS1** | 3 | Project Definition & Architecture | 🟢 Complete |
| **MS2** | 6 | Data Prep & Core Prototypes (YOLO/RAG) | ⬜ Next |
| **MS3** | 9 | Integration & Agent Logic | ⬜ Planned |
| **MS4** | 12 | Deployment & Polish | ⬜ Planned |

---

## 📄 Design Documents

1. **[PRD v1.1](docs/PRD-Personal-Health-Butler.md)**: MVP Scope, Success Criteria
2. **[L1 Business](docs/L1-Business-Architecture.md)**: Value Proposition, User Journeys
3. **[L2 Application](docs/L2-Application-Architecture.md)**: Service Design, Interfaces
4. **[L3 Data](docs/L3-Data-Architecture.md)**: Privacy, Knowledge Schema
5. **[L4 Technology](docs/L4-Technology-Architecture.md)**: Stack, Security, CI/CD

---
