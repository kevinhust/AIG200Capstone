# L4 Technology Architecture
# Personal Health Butler AI

> **Version**: 1.2
> **Last Updated**: 2026-01-18
> **Parent Document**: [PRD v1.1](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L4 - Technology Architecture

---

## 1. Technology Stack (2026 Standards)

### 1.1 Stack Summary

| Layer | Component | Technology | Rationale |
|-------|-----------|------------|-----------|
| **Frontend** | Web UI | **Streamlit** (v1.40+) | Fast iteration, Python native |
| **Logic** | Orchestration | **LangGraph** | Cyclic agentic workflows |
| **Reasoning** | LLM | **Gemini 2.5 Flash** | Low latency, multimodal, cost-effective |
| **Vision** | Object Detection | **YOLO26-Nano** | Edge-optimized (15MB), CPU-friendly |
| **Retrieval** | Vector DB | **FAISS** (Local Index) | No external DB dependency (Self-contained) |
| **Embedding** | Model | **e5-large-v2** | State-of-the-art open embedding |

---

## 2. Infrastructure & Provisioning

### 2.1 Model Provisioning Strategy ("Bake-in" Pattern)

To simplify deployment on serverless platforms (Cloud Run), we adopt a **Self-Contained Container** strategy.

-   **YOLO26 Weights**: Included in the Docker image at `/app/models/yolo26-n.pt`.
-   **FAISS Index**: Pre-computed during CI/CD and copied to `/app/data/knowledge_base/index.faiss`.
-   **Embedding Model**: Cached in `/app/models/sentence-transformers/` during build to avoid runtime download.

**Trade-off Analysis:**
-   *Pros*: Zero cold-start download time, consistent versioning, no external volume dependency.
-   *Cons*: Image size increases (~1GB total). Handled well by standard container registries.

### 2.2 Image Storage Infrastructure

We strictly adhere to a **Privacy-First (No-Log)** architecture for user images.

-   **Ingest**: Streamlit `file_uploader` reads image into RAM (`io.BytesIO`).
-   **Process**: YOLO and Gemini accept base64-encoded strings or byte streams directly from RAM.
-   **Discard**: Memory is freed immediately after the request completes.
-   **Logging**: Only metadata (e.g., "Food detected: Pizza, Conf: 0.95") is logged; pixel data is never serialized.

---

## 3. Dependency Specification

### 3.1 Core Requirements (`pyproject.toml`)

```toml
[project]
name = "health-butler-ai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.1.0",
    "langchain-google-genai>=1.0",
    "streamlit>=1.40.0",
    "ultralytics>=8.3.0",              # YOLO26
    "sentence-transformers>=3.0.0",
    "faiss-cpu>=1.8.0",
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.0"
]
```

---

## 4. Deployment Architecture (Serverless)

### 4.1 Container Design (Monolithic Modular)

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# 1. Install Dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY pyproject.toml .
RUN uv pip install --system .

# 2. Provision Models (Burn-in)
# Pre-download embedding model to cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/e5-large-v2')"

# 3. Copy Application & Data
COPY src/ ./src/
COPY data/knowledge_base/ ./data/knowledge_base/  # Includes index.faiss
COPY models/ ./models/                             # Includes yolo26.pt

# 4. Run
CMD ["streamlit", "run", "src/ui_streamlit/main.py", "--server.port", "8080"]
```

### 4.2 CI/CD Pipeline (GitHub Actions)

1.  **Test**: Run Unit Tests.
2.  **Security Scan**: Trivy scan for vulnerability.
3.  **Data Build**: Run `scripts/build_vector_index.py` to regenerate FAISS index from latest JSON.
4.  **Build & Push**: Build Docker image (with verified index) -> Artifact Registry.
5.  **Deploy**: Update Cloud Run service.

---

**Document Status**: 🟢 Version 1.2 - Detailed Provisioning
