# L4 Technology Architecture
# Personal Health Butler AI

> **Version**: 1.1
> **Last Updated**: 2026-01-16
> **Parent Document**: [PRD v1.1](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L4 - Technology Architecture

---

## 1. Technology Stack (2026 Standards)

### 1.1 Stack Summary

| Layer | Component | Technology | Rationale |
|-------|-----------|------------|-----------|
| **Frontend** | Web UI | **Streamlit** (v1.40+) | Fast iteration, Python native |
| **Orchestration** | Agent Framework | **LangGraph** | Strong cyclic graph support for agents |
| **Logic/Reasoning** | Primary LLM | **Gemini 2.5 Flash** | Low latency, multimodal native, cost-effective |
| | Fallback LLM | **DeepSeek-V3** | High intelligence/cost ratio |
| **Vision** | Object Detection | **YOLO26-Nano** | Optimized for edge/CPU inference |
| **Data** | Vector DB | **FAISS** (Local) | Simple, no-cloud-dependency retrieval |
| | Embedding | **e5-large-v2** | High quality semantic search |

### 1.2 Development Environment

- **Python**: 3.11+ (Stable 2026 choice)
- **Dependency Mgmt**: **uv** (Fast rust-based installer)
- **Containerization**: Docker (Multi-stage builds)

---

## 2. Dependency Specification

### 2.1 Core Requirements (`pyproject.toml`)

```toml
[project]
name = "health-butler-ai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.1.0",
    "langchain-google-genai>=1.0",     # Gemini Integration
    "langchain-community>=0.2",
    "streamlit>=1.40.0",
    "ultralytics>=8.3.0",              # Support for YOLO26
    "sentence-transformers>=3.0.0",
    "faiss-cpu>=1.8.0",
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.0"
]
```

### 2.2 Dev & Security Tools

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.4.0",           # Linter/Formatter
    "pytest>=8.0.0",
    "trivy-client>=0.1.0"    # Vulnerability Scanning
]
```

---

## 3. Deployment Architecture (Serverless First)

### 3.1 container Design

Single container strategy for MVP to minimize complexity (Monolithic Modular).

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install uv for speed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install dependencies
COPY pyproject.toml .
RUN uv pip install --system .

# Copy Source (Modular structure)
COPY src/ ./src/
COPY data/knowledge_base/ ./data/knowledge_base/

# Run
CMD ["streamlit", "run", "src/ui_streamlit/main.py", "--server.port", "8080"]
```

### 3.2 CI/CD Pipeline (GitHub Actions)

```yaml
jobs:
  security-scan:
    steps:
      - name: Trivy Vulnerability Scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'local/health-butler:${{ github.sha }}'
          format: 'table'
          exit-code: '1' # Fail on high severity

  deploy:
    needs: [test, security-scan]
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: health-butler-mvp
          region: us-central1
          flags: '--allow-unauthenticated'
```

---

## 4. Monitoring & Observability

### 4.1 Metrics Strategy
- **Application Logs**: StructLog (JSON format) -> Cloud Logging.
- **LLM Tracing**: **LangSmith** (Developer Tier) for tracing agent chains and costs.
- **Model Drift**: Simple weekly cron job comparing "Average Food Confidence" to detect if model needs retraining.

---

**Document Status**: 🟢 Draft v1.1 - 2026 Ready
