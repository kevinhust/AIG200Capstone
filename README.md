# Personal Health Butler AI

> 🤖 A Multi-Agent AI Nutrition & Fitness Assistant (MVP v1.1)

## 📋 Project Overview

The **Personal Health Butler** is an AI-powered nutrition assistant that leverages **Multi-Agent Architecture** and **Retrieval-Augmented Generation (RAG)** to provide personalized, evidence-based wellness guidance.

**Core Value**: Snap a photo of your meal -> Get instant calorie/macro analysis + science-backed advice.

**Team**: Group 5 (Allen, Wangchuk, Aziz, Kevin)  
**Course**: AI Graduate Certificate Capstone (2026)  
**Duration**: 14 Weeks
**Repository**: [GitHub](https://github.com/kevinhust/AIG200Capstone)
**Agent Framework**: [Antigravity Template](docs/framework/en/README.md)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Coordinator Agent                               │
│                    (OpenAI Swarm Orchestration)                      │
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
│  │ (ChromaDB)  │  │(Transfmr ViT)│  │(Gemini 2.5) │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
AIG200Capstone/
├── docs/                           # 📚 Design Documents
├── health_butler/                  # 🏥 Core Application Code
│   ├── agents/                     # Agent Modules
│   ├── tools/                      # Setup Tools (RAG, Vision)
│   ├── scripts/                    # Data Ingestion
│   └── main.py                     # Entrypoint
├── openspec/                       # 📋 Spec-Driven Development
├── tests/                          # Automated Tests
└── README.md                       # This file
```

---

## 🛠️ Tech Stack (Prototype Phase 2)

| Category | Technologies |
|----------|-------------|
| Agent Orchestrator | **OpenAI Swarm** (Lightweight Routing) |
| LLM | **Gemini 2.5 Flash** |
| Computer Vision | **ViT (Vision Transformer)** (Classification) |
| Vector Database | **ChromaDB** (Local & Semantic) |
| Embedding | **Sentence Transformers** |
| Deployment | **Streamlit** (Local Prototype) |

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
| **MS2** | 6 | Data Prep & Core Prototypes (ViT/Chroma/Streamlit) | 🔵 In Progress |
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
