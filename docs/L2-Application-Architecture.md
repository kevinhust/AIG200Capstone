# L2 Application Architecture
# Personal Health Butler AI

> **Version**: 1.1
> **Last Updated**: 2026-01-16
> **Parent Document**: [PRD v1.1](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L2 - Application Architecture

---

## 1. System Overview

### 1.1 C4 Level 1: System Context

```mermaid
graph TB
    %% Styles
    classDef user fill:#FFD700,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10;
    classDef system fill:#87CEEB,stroke:#2b4b6f,stroke-width:2px,color:black,rx:5,ry:5;
    classDef external fill:#D3D3D3,stroke:#666,stroke-width:2px,color:black,stroke-dasharray: 5 5;
    classDef ai fill:#FFB6C1,stroke:#C71585,stroke-width:2px,color:black;

    User["User (Alex)"]:::user
    subgraph "Personal Health Butler System"
        PHB["Health Butler App"]:::system
    end
    ExternalKB["External Knowledge<br/>(USDA, Open Food Facts)"]:::external
    LLM["LLM Provider<br/>(Gemini 2.5 / DeepSeek)"]:::ai

    User -->|Uploads Image/Chat| PHB
    PHB -->|Queries| ExternalKB
    PHB -->|Inference| LLM
    PHB -->|Response| User
```

### 1.2 C4 Level 2: Container Diagram

```mermaid
graph TB
    %% Styles
    classDef user fill:#FFD700,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10;
    classDef ui fill:#ADD8E6,stroke:#4682B4,stroke-width:2px,color:black;
    classDef logic fill:#98FB98,stroke:#2E8B57,stroke-width:2px,color:black;
    classDef db fill:#DDA0DD,stroke:#800080,stroke-width:2px,color:black,shape:cylinder;

    User[User]:::user
    
    subgraph "Docker Compose Cluster"
        direction TB
        UI["Streamlit Frontend<br/>(Python/Streamlit)"]:::ui
        Coord["Coordinator Service<br/>(LangGraph API)"]:::logic
        NutSvc["Nutrition Service<br/>(YOLO26 + RAG)"]:::logic
        FitSvc["Fitness Service<br/>(Rule-based)"]:::logic
        
        UI -->|HTTP/REST| Coord
        Coord -->|Internal API| NutSvc
        Coord -->|Internal API| FitSvc
    end
    
    VDB[("FAISS Vector Store")]:::db
    NutSvc --> VDB
```

---

## 2. Component Design (Modular MVP)

### 2.1 Service Catalog

| Service | Responsibility | Key Tech | 2026 Trend Alignment |
|---------|----------------|----------|----------------------|
| **Frontend** | User Interaction, Session State | Streamlit | Rapid prototyping |
| **Coordinator** | Intent Routing, Synthesis | LangGraph | Agentic Orchestration |
| **Nutrition Svc** | Food Recognition, Diet Advice | YOLO26, RAG | Edge-friendly CV |
| **Fitness Svc** | Exercise Suggestions | Logic/Rules | - |

### 2.2 Component: Nutrition Service

**Internal Structure:**
- **CV Module**: Loads `yolo26-n.pt` for fast inference. Pre-processes image (resize/norm).
- **RAG Module**: Embedding client (SentenceTransformer `all-MiniLM` or `e5-large`), FAISS index searcher.
- **Analyst**: Logic to combine detected foods with retrieved nutrition facts.

**Interface (JSON Contract):**

```json
// Input: RunAnalysisRequest
{
  "image_base64": "...",
  "user_context": {"goal": "weight_loss"}
}

// Output: AnalysisResult
{
  "foods": [
    {"name": "pizza", "confidence": 0.92, "calories": 285}
  ],
  "total_calories": 285,
  "macros": {"protein": 12, "carbs": 36, "fat": 10},
  "suggestions": ["Add a side salad for fiber."]
}
```

---

## 3. Technology Stack & Integration

### 3.1 LLM Strategy (Tiered)

| Tier | Model | Use Case | Justification |
|------|-------|----------|---------------|
| **Primary** | **Gemini 2.5 Flash** | General Reasoning, Synthesis | Low cost, high speed, multimodal native |
| **Fallback** | **DeepSeek-V3 / GLM-4** | Complex reasoning (if needed) | Open weight / Cost effective |
| **Embedding** | **e5-large-v2** | Knowledge Retrieval | Best-in-class open embedding |

### 3.2 Computer Vision

- **Model**: **YOLO26 (Nano/Small)**
- **Optimization**: ONNX Runtime or TorchScript for CPU inference optimization.
- **Dataset**: Pre-trained on COCO, Fine-tuned on **Food-101**.

---

## 4. State Management

### 4.1 Implementation
- **Session State**: Managed in-memory via Streamlit Session State (ephemeral).
- **Conversation Memory**: `LangChain.memory.ConversationBufferWindowMemory` (k=5 rounds).

### 4.2 Data Flow

1. **User Upload** -> UI stores in RAM.
2. UI calls **Coordinator** with inputs.
3. Coordinator maintains short-term conversational context.
4. Coordinator calls **Nutrition Agent**.
5. Nutrition Agent runs **YOLO** (stateless).
6. Result returns to UI for display.
7. **No persistent DB** for user data (Privacy by Design).

---

## 5. Security Architecture (Zero Trust Lite)

- **API Security**: Although internal, services use strict Pydantic validation.
- **Secret Management**: `.env` files for keys (Gemini API, etc.), strictly git-ignored.
- **Input Sanitization**: All text inputs scanned for prompt injection markers before LLM processing.

---

## 6. Deployment View (Cloud Run)

```yaml
# Simplified Structure
services:
  app:
    image: health-butler-mvp:latest
    ports: [8080]
    env_file: .env
    resources:
      memory: 4GB  # Enough for YOLO + FAISS
```

**Scalability Strategy**:
- Cloud Run automatically scales to 0 when unused (Cost saving).
- Stateless design allows horizontal scaling if demo traffic spikes.

---

**Document Status**: 🟢 Draft v1.1 - Modular MVP Design
