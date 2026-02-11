## 1. Environment & Dependencies
- [x] 1.1 Install Libraries: `pip install transformers torch torchvision chromadb sentence-transformers streamlit watchdog`.
- [x] 1.2 Update Requirements: Freeze `requirements.txt`.

## 2. Advanced Tool Implementation
- [x] 2.1 Real Vision Tool:
    - Modify `health_butler/tools/vision_tool.py` to import `transformers`.
    - Implement `ViTForImageClassification` loading (`nateraw/food-vit-101` w/ fallback).
    - Implement `detect_food` (classification) using the model.
- [x] 2.2 Real RAG Tool:
    - Modify `health_butler/tools/rag_tool.py` to use `chromadb`.
    - Implement collection creation and embedding generation via `SentenceTransformer`.
    - Update `health_butler/scripts/ingest_usda.py` to push data to ChromaDB.

## 3. User Interface (Streamlit)
- [x] 3.1 App Skeleton: Create `health_butler/app.py` with basic chat layout.
- [x] 3.2 Tools Integration: Connect `VisionTool` and `RagTool` to the UI.
- [x] 3.3 Visual Feedback: Implement "Thinking" status, Vision results display.

## 4. Verification
- [x] 4.1 Integration Test: Create `tests/test_phase2_quick.py`.
- [x] 4.2 Manual Verification: Verify UI flow (User -> Image -> ViT -> RAG -> Response).lay (capturing standard output or using a callback).

## 4. Verification
- [ ] 4.1 Script Verification: Run `ingest_usda.py` with embedding generation.
- [ ] 4.2 App Test: Launch `streamlit run health_butler/app.py` and manually verify flow.
