# Architecture Feasibility & Implementation Path Review

## Executive Summary
Based on deep-dive research into 2025 best practices for Personal Health Agents, the current project path is **highly feasible** for a Capstone MVP, but specific component choices should be optimized for developer velocity and feature richness.

## 1. Orchestration: Swarm vs. LangGraph
**Current Plan**: OpenAI Swarm (via `src/swarm.py` mock or library).
**Research Findings**:
- **LangGraph** is the industry standard for stateful, complex agent workflows (Looping, Human-in-the-loop).
- **Swarm** is excellent for stateless, lightweight "handoffs" (Routing).
- **Recommendation**: **Stay with Swarm for Phase 2 (Prototyping)** to ensure rapid delivery of the demo. The current `Coordinator -> Agent` pattern fits Swarm perfectly. Moving to LangGraph would introduce unnecessary complexity right now but is a valid "Future Improvement" for the final report.

## 2. Vision Pipeline: Detection vs. Classification
**Current Plan**: YOLO26 (Detection).
**Research Findings**:
- Pre-trained YOLO models for *Food-101* are not standard in `ultralytics`. Training one requires GPU time.
- **HuggingFace ViT (Vision Transformer)** models (e.g., `nateraw/food-vit-101`) are readily available with 1-line Python support.
- **Recommendation**:
  - **Primary**: Use **HuggingFace ViT** for robust Image Classification (What is this?).
  - **Secondary**: Use generic YOLO only if *locating* the food (Bounding Box) is critical. For a Health Butler, *identifying* the simple meal is priority.
  - **Dataset**: Stick to **Food-101** for broad coverage. **Nutrition5k** is better for depth/mass but harder to implement quickly.

## 3. RAG Engine: FAISS vs. Chroma
**Current Plan**: FAISS (CPU).
**Research Findings**:
- **FAISS** is fast but low-level; handling metadata (Calories, Macros) requires custom mapping.
- **ChromaDB** is "battery-included" for Local RAG, supporting rich metadata filtering (e.g., "Find foods with > 20g protein") out of the box.
- **Recommendation**: **Switch to ChromaDB**. It simplifies the implementation of "Semantic Search" and allows structured filtering which is crucial for the Nutrition Agent.

## 4. User Interface: Streamlit vs. React
**Current Plan**: Streamlit.
**Research Findings**:
- **Streamlit** is the de-facto standard for AI Demos due to `st.chat_message` and `st.status` (for showing "Agent Thinking").
- **Recommendation**: **Confirm Streamlit**. It's 10x faster to build than React and perfectly supports the "streaming token" experience required for a chat bot.

## Modified Implementation Path (Proposed Phase 2)
1.  **Orchestrator**: Refine `CoordinatorAgent` (Swarm).
2.  **Vision Tool**: Implement `transformers` (ViT) instead of YOLO for immediate accuracy.
3.  **Data Tool**: Implement `chromadb` for USDA queries.
4.  **UI**: Build `health_butler/app.py` with Streamlit.

This path minimizes "Training" risk and maximizes "Integration" speed.
