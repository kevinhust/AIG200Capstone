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
| **Orchestration** | Agent Framework | **OpenAI Swarm** | Lightweight, stateless agent handoffs |
| **Logic/Reasoning** | Primary LLM | **Gemini 2.5 Flash** | Low latency, multimodal native, cost-effective |
| | Fallback LLM | **DeepSeek-V3** | High intelligence/cost ratio |
| **Vision** | Object Classification | **ViT-Base** (HuggingFace) | High accuracy on Food-101, easy integration |
| **Data** | Vector DB | **ChromaDB** (Local) | Metadata filtering support, easy setup |
| | Embedding | **Sentence Transformers** | High quality semantic search |

### 1.2 Development Environment

- **Python**: 3.11+ (Stable 2026 choice)
- **Dependency Mgmt**: **pip** (Standard)
- **Containerization**: Docker (Multi-stage builds)

---

## 2. Infrastructure & Provisioning

### 2.1 Model Provisioning Strategy ("Bake-in" Pattern)

To simplify deployment on serverless platforms (Cloud Run), we adopt a **Self-Contained Container** strategy.

-   **ViT Model**: Downloaded via `transformers` cache during build.
-   **ChromaDB**: Local persistence at `/app/data/chroma_db`.
-   **Embedding Model**: Cached in `/app/models/sentence-transformers/` during build.

**Trade-off Analysis:**
-   *Pros*: Zero cold-start download time, consistent versioning, no external volume dependency.
-   *Cons*: Image size increases (~2GB+). Handled well by standard container registries.

### 2.2 Image Storage Infrastructure

We strictly adhere to a **Privacy-First (No-Log)** architecture for user images.

-   **Ingest**: Streamlit `file_uploader` reads image into RAM (`io.BytesIO`).
-   **Process**: ViT accepts PIL images directly from RAM.
-   **Discard**: Memory is freed immediately after the request completes.
-   **Logging**: Only metadata (e.g., "Food detected: Pizza, Conf: 0.95") is logged; pixel data is never serialized.

---

## 3. Dependency Specification

### 3.1 Core Requirements (`requirements.txt`)

```text
google-genai>=1.0
streamlit>=1.40.0
transformers>=4.40.0
torch>=2.2.0
torchvision>=0.17.0
chromadb>=0.4.24
sentence-transformers>=2.7.0
watchdog>=4.0.0
python-dotenv>=1.0.0
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
