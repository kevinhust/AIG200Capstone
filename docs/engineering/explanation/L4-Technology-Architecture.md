# L4 Technology Architecture
# Personal Health Butler AI

> **Version**: 6.1
> **Last Updated**: March 10, 2026
> **Parent Document**: [PRD v6.0](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L4 - Technology Architecture

---

## 1. Technology Stack (2026 Standards)

### 1.1 Core Development Stack

| Category | Component | Selection | Rationale |
|----------|-----------|-----------|-----------|
| **LLM Interface** | Multimodal AI | **Gemini 2.5 Flash** | Native multimodal support, extremely fast and cost-effective |
| **CV Engine** | Object Detection | **YOLO11n** | Superior accuracy-to-latency ratio, state-of-the-art in 2026 |
| **Interface** | Bot Framework | **discord.py** | Rich modals/views, professional UX, persistent connections |
| **Persistence** | Database | **Supabase (PostgreSQL)** | Managed Postgres, real-time subscriptions, auth built-in |
| **Data Layer** | Vector DB | **ChromaDB** | Native Python support, excellent for embedded RAG |
| **Embedding** | Model | **e5-large-v2** | Best-in-class open embedding for semantic search |
| **Runtime** | Containerization | **Docker (Python 3.12)** | Improved performance, modern library support |

### 1.2 Development Environment

- **Python**: 3.12+ (Stable 2026 choice)
- **Dependency Mgmt**: pip + pyproject.toml
- **Containerization**: Docker (Multi-stage builds)
- **CI/CD**: GitHub Actions

---

## 2. Infrastructure & Provisioning

### 2.1 Model Provisioning Strategy ("Bake-in" Pattern)

To simplify deployment on serverless platforms (Cloud Run), we adopt a **Self-Contained Container** strategy.

| Artifact | Location | Size | Provisioning |
|----------|----------|------|--------------|
| **YOLO11 Weights** | `/app/models/yolo11n.pt` | ~15 MB | Baked into Docker image |
| **Embedding Model** | `/app/models/sentence-transformers/` | ~500 MB | Cached during build |
| **ChromaDB Index** | `/app/data/chroma_db/` | ~100 MB | Baked into image |

**Trade-off Analysis:**
- *Pros*: Zero cold-start download time, consistent versioning, no external volume dependency.
- *Cons*: Image size increases (~1.5GB). Handled well by standard container registries.

### 2.2 Image Storage Infrastructure (Privacy-First)

We strictly adhere to a **Privacy-First (No-Log)** architecture for user images.

- **Ingest**: Discord attachment downloaded into RAM (`io.BytesIO`).
- **Process**: YOLO11 + Gemini accept PIL images directly from RAM.
- **Discard**: Memory freed immediately after request completes.
- **Logging**: Only metadata (e.g., "Food detected: Pizza, Conf: 0.95") logged; pixel data never serialized.

### 2.3 Supabase Integration (v6.0 NEW)

| Table | Purpose | Schema |
|-------|---------|--------|
| `profiles` | User onboarding data | id, discord_id, name, age, gender, height, weight, goal, activity, conditions, dietary_prefs |
| `meal_logs` | Meal tracking history | id, user_id, timestamp, foods, calories, protein, carbs, fat |
| `macro_budgets` | TDEE/DV% calculations | id, user_id, tdee, protein_goal, carb_goal, fat_goal, updated_at |

---

## 3. Dependency Specification

### 3.1 Core Requirements

```text
# LLM & AI
google-genai>=1.0
ultralytics>=8.3.0          # YOLO11

# Discord
discord.py>=2.4.0
aiohttp>=3.9.0

# Database
supabase>=2.0.0

# RAG
chromadb>=0.4.24
sentence-transformers>=2.7.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0
structlog>=24.0.0
```

---

## 4. Deployment Architecture

### 4.1 Container Design

```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app

# 1. Install Dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY pyproject.toml .
RUN uv pip install --system .

# 2. Provision Models (Bake-in)
RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/e5-large-v2')"

# 3. Copy Application & Data
COPY src/ ./src/
COPY data/ ./data/

# 4. Health Check Server + Bot
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-m", "src.discord_bot"]
```

### 4.2 Docker Compose (Production)

```yaml
services:
  bot:
    build: .
    container_name: health-butler-bot
    env_file: .env
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - PORT=8080
    ports:
      - "8085:8080"
    volumes:
      - health-butler-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  health-butler-data:
```

### 4.3 CI/CD Pipeline (GitHub Actions)

1. **Test**: Run pytest with coverage
2. **Security Scan**: Trivy vulnerability scan
3. **Build**: Docker image build with baked-in models
4. **Push**: Artifact Registry
5. **Deploy**: Cloud Run (optional) or local Docker

---

## 5. Environment Configuration

### 5.1 Required Environment Variables

```env
# Discord
DISCORD_TOKEN=your_bot_token
DISCORD_ALLOWED_CHANNEL_IDS=123456789
DISCORD_ALLOWED_USER_IDS=987654321

# Google AI (Unified Key - v6.0)
GOOGLE_API_KEY=your_google_ai_studio_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Runtime
DEPLOY_ENV=local|production
DEBUG_MODE=false
```

### 5.2 API Key Strategy (v6.0)

The system uses **unified `GOOGLE_API_KEY`** as the single source of truth:
- Primary: `GOOGLE_API_KEY`
- Fallback: `GEMINI_API_KEY` (via Pydantic AliasChoices)
- Precedence: Explicit constructor > `GOOGLE_API_KEY` > `GEMINI_API_KEY`

---

## 6. Monitoring & Observability

### 6.1 Health Check Endpoint

```
GET /health → 200 OK {"status": "healthy", "version": "6.0"}
```

### 6.2 Logging Strategy

- **Framework**: structlog (JSON structured logging)
- **Levels**: INFO for operations, WARNING for fallbacks, ERROR for failures
- **Privacy**: No PII or image data in logs

---

**Document Status**: 🟢 Version 6.0 - Production Infrastructure
