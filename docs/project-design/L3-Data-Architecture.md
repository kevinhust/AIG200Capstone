# L3 Data Architecture
# Personal Health Butler AI

> **Version**: 1.2
> **Last Updated**: 2026-01-18
> **Parent Document**: [PRD v1.1](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L3 - Data Architecture

---

## 1. Data Strategy: Hybrid Intelligence

Our system distinguishes between **Pattern Recognition** (done by pre-trained models) and **Factual Knowledge** (sourced from trusted databases) to prevent hallucinations.

| Feature | Data Source | Technology | Update Freq |
|---------|-------------|------------|-------------|
| **Visual Detection** | Pre-trained Patterns | **YOLO26** (COCO + Synthetic Food-101) | Static (Build-time) |
| **Nutritional Facts** | Trusted Database | **USDA Food Data** (RAG Retrieval) | Monthly (ETL) |
| **User Context** | User Input | **Ephemeral Session** (RAM) | Real-time |

> **Addressing Source Feedback**: We do NOT rely on the LLM's internal knowledge for nutrition facts (which are prone to hallucination). We use the LLM only for reasoning, while facts are retrieved from the USDA database.

---

## 2. Data Architecture Overview

### 2.1 Data Domains

```mermaid
graph TB
    %% Styles
    classDef know fill:#E0FFFF,stroke:#008B8B,stroke-width:2px,color:black,rx:5,ry:5;
    classDef runtime fill:#FFFFE0,stroke:#DAA520,stroke-width:2px,color:black,rx:5,ry:5;
    classDef model fill:#E6E6FA,stroke:#9370DB,stroke-width:2px,color:black,rx:5,ry:5;

    subgraph "Knowledge Data (Public)"
        NUT[Nutrition KB]:::know
        FIT[Fitness KB]:::know
    end
    
    subgraph "Runtime Data (Ephemeral)"
        SES[Session Context]:::runtime
        IMG[User Uploads]:::runtime
    end
    
    subgraph "Model Artifacts"
        YOLO[YOLO26 Weights]:::model
        IDX[FAISS Index]:::model
    end
```

### 2.2 Data Flow & Privacy

-   **Ingestion (Build Time)**: Public data (USDA) -> Chunking -> Vector Store -> **Baked into Container**.
-   **Runtime**: User Image -> RAM -> Inference -> **Delete**.
-   **Privacy Guarantee**: 
    -   No user images are written to disk. 
    -   Images are processed in-memory using `io.BytesIO`.
    -   No conversation logs persist after session end.

---

## 3. Detailed ETL Pipeline (Knowledge Base)

To ensure trusted data, we implement a strict ETL pipeline for the RAG Knowledge Base.

**Source**: `USDA FoodData Central` (JSON API)

1.  **Extract**: Download "Foundation Foods" dataset (approx 30k verified items).
2.  **Transform**:
    -   Clean and normalize fields (Calories, Protein, Fat, Carbs).
    -   Format into text chunks: *"100g of raw Broccoli contains 34 calories, 2.8g protein..."*
3.  **Embed**:
    -   Model: `intfloat/e5-large-v2` (1024 dimensions).
    -   Process: Batch embed -> Normalize vectors.
4.  **Load**:
    -   Build `FAISS` Index (`IndexFlatIP`).
    -   Save `index.faiss` and `metadata.json` to `data/knowledge_base/`.

---

## 4. Storage Architecture

### 4.1 Knowledge Storage (Read-Only)

| Component | Format | Est. Size | Provisioning |
|-----------|--------|-----------|--------------|
| **FAISS Index** | Binary (`.faiss`) | ~500 MB | **Baked into Docker Image** |
| **Metadata** | JSON/SQLite | ~100 MB | **Baked into Docker Image** |
| **YOLO Weights**| `.pt` / `.onnx` | ~15 MB | **Baked into Docker Image** |

*Rationale*: Baking data into the image ensures zero-latency startup and consistency across Cloud Run instances.

### 4.2 Runtime Storage (Ephemeral)

| Data Type | Storage Mechanism | Lifecycle |
|-----------|------------------|-----------|
| **User Images** | `io.BytesIO` (RAM) | Dropped after inference |
| **Chat History** | `Streamlit Session State` | Dropped on tab close |
| **Feedback** | `structlog` (JSON) | Streamed to Cloud Logging (Anonymized) |

---

## 5. Knowledge Base Schema

### 5.1 Chunk Structure

```python
@dataclass
class KnowledgeChunk:
    """Standardized Knowledge Unit"""
    id: str
    content: str          # "Broccoli: 34kcal/100g..."
    source: str           # "USDA ID: 11090"
    embedding: List[float] # 1024-dim
    metadata: Dict[str, Any] # {"macros": {"p": 2.8, "c": 7, "f": 0.4}}
```

---

**Document Status**: 🟢 Version 1.2 - Detailed Infrastructure
