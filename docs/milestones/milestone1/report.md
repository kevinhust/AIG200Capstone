# Milestone 1 Report: Project Definition & Planning
**Date:** 2026-01-21
**Team:** Group 5 (Allen, Wangchuk, Aziz, Kevin)
**Project:** Personal Health Butler AI

---

## 1. Project Charter (Refined)

### Problem Statement
Current health applications often suffer from two main issues:
1.  **High Friction**: Manual logging of meals is tedious and prone to abandonment.
2.  **Generic Advice**: "Cookie-cutter" recommendations that lack personalization or scientific grounding.

### Goal
Build an **AI-powered Personal Health Butler** that creates a seamless "Snap & Ask" experience.
-   **Core Function**: Users upload a photo of their meal -> System recognizes food -> Retrieves validated nutrition data -> Offers personalized advice.
-   **Key Differentiator**: Use of **RAG (Retrieval-Augmented Generation)** to ground advice in trusted sources (USDA), preventing LLM hallucinations.

### Scope (In/Out)
| In-Scope (MVP) | Out-of-Scope |
| :--- | :--- |
| ✅ Image-based Food Recognition (ViT) | ❌ Medical Diagnosis/Treatment |
| ✅ Trusted Nutrition Retrieval (RAG) | ❌ Wearable Device Integration |
| ✅ Interactive Streamlit Dashboard | ❌ Multi-language Support |
| ✅ Dual-Agent Logic (Nutrition/Fitness) | ❌ Complex Predictive Analytics |

> *Reference: [PRD Section 1 & 2](../../project-design/PRD-Personal-Health-Butler.md)*

---

## 2. Data Acquisition & Exploration

### Data Sources
*   **Facts**: **USDA FoodData Central** (Foundation Foods).
    *   *Status*: ETL pipeline (`ingest_usda.py`) implemented. JSONs downloaded and cleaned.
*   **Visuals**: **Food-101 Dataset**.
    *   *Status*: Used for fine-tuning YOLO26 visuals. Sample images acquired.

### Data Strategy
*   **Storage**: **ChromaDB / FAISS** for vector embedding of nutrition facts.
*   **Privacy**: User images are processed in-memory (RAM) and **never written to disk**, ensuring privacy by design.

> *Reference: [L3 Data Architecture](../../project-design/L3-Data-Architecture.md)*

---

## 3. Technical Approach

### Architecture Pattern: "Agentic Swarm"
We employ a **Star Topology** where a central **Coordinator Agent** manages specialized workers.

*   **Coordinator**: Routes intent (Talk vs. Photo).
*   **Nutrition Agent**:
    *   *Vision*: **ViT** (Selected over YOLO for better HF integration).
    *   *Logic*: **RAG** (Grounding).
*   **Fitness Agent**: Simple rule-based logic logic + LLM reasoning.

### Technology Stack
*   **LangGraph**: For orchestrating the agent state machine.
*   **Gemini 2.5 Flash**: Primary LLM (Low latency, multimodal native).
*   **Streamlit**: For rapid UI prototyping.
*   **Docker**: For containerized deployment (Cloud Run).

> *Reference: [L2 Application Architecture](../../project-design/L2-Application-Architecture.md)*

---

## 4. Technical Challenges & Evolution (Architecture Pivot)

During the Phase 1 prototyping (Week 1-2), we encountered specific challenges that led to architectural pivots:

### Pivot: From YOLO26 to Vision Transformer (ViT)
*   **Initial Plan**: Use **YOLO26** for object detection (bounding boxes).
*   **Challenge**: Fine-tuning YOLO on the Food-101 dataset required complex format conversion (Darknet labeling) and significant GPU resources to retrain from scratch for acceptable accuracy.
*   **Resolution**: Switched to **ViT (Vision Transformer)** using HuggingFace (`nateraw/food-vit-101`).
    *   *Benefit 1*: Pre-trained specifically on Food-101, offering immediate high accuracy (~85%) without retraining.
    *   *Benefit 2*: Native integration with our Python stack via `transformers` library, removing the need for external C++ binaries or ONNX runtime complexity.
    *   *Trade-off*: ViT provides Classification (what is it?) rather than Detection (where is it?), which is acceptable for our Use Case ("Snap a meal").

---

## 5. Project Plan (Next 3 Weeks)

We are following a **Modular Parallel** development strategy.

| Week | Focus | Key Deliverable | Owner |
| :--- | :--- | :--- | :--- |
| **Week 4** | **Core Agents** | `NutritionAgent` (Real ViT/RAG) & `FitnessAgent` operational. | Wangchuk/Kevin |
| **Week 5** | **Orchestration** | `HealthSwarm` (Coordinator) wiring everything together. | Allen |
| **Week 6** | **UI & Proto** | Streamlit UI fully connected to Swarm. **Milestone 2 Check-in**. | All |

### Roles (RACI)
*   **Allen**: Orchestration & Integration.
*   **Wangchuk**: CV & UI.
*   **Aziz**: Data & RAG.
*   **Kevin**: Fitness Logic & Documentation.

---

## 6. Risks & Challenges

1.  **Hallucination Risk**: LLM inventing calories.
    *   *Mitigation*: Strict RAG. If data not in USDA, return "Unknown" rather than guessing.
2.  **Vision Accuracy**: Food-101 is limited.
    *   *Mitigation*: Allow user to edit/correct detected food labels in UI.
3.  **Latency**: RAG + Vision + LLM chain might be slow.
    *   *Mitigation*: Use `Gemini Flash` (fast) and local embedding models (`all-MiniLM`).
