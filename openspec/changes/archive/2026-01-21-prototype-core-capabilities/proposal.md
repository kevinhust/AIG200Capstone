# Change: Prototype Core Capabilities (Phase 2)

## Why
To transition the Personal Health Butler from a foundational skeleton (Phase 1) to a functional prototype (Phase 2), aligning with Course Milestone 2. This involves replacing mock tools with actual machine learning models and providing an interactive user interface for demonstration.

## What Changes
- **Vision Capabilities**:
  - Upgrade `VisionTool` to use **HuggingFace Transformers (ViT)** for accurate food classification.
  - Use pre-trained `nateraw/food-vit-101` (or similar) model.
- **RAG Capabilities**:
  - Upgrade `RagTool` to use **ChromaDB** for local vector storage and retrieval.
  - Enable metadata filtering (e.g., retrieving items based on macronutrients).
  - Use `sentence-transformers` for embeddings.
- **User Interface**:
  - Create a Streamlit application (`health_butler/app.py`) to serve as the chat interface.
  - Display "Thinking" process (Agent delegation) and Multi-modal inputs (Image upload).
- **Dependencies**:
  - Add `transformers`, `torch`, `chromadb`, `sentence-transformers`, `streamlit`.

## Impact
- **Specs**: New `prototype` capability defines UI and Performance requirements.
- **Code**:
  - Significant updates to `health_butler/tools/`.
  - New `health_butler/app.py`.
  - Updates to `requirements.txt`.
