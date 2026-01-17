# Personal Health Butler AI - Project Context

> This file provides context for AI assistants (Cursor, Gemini, Copilot) to understand the project.

## Project Summary

**Personal Health Butler** is a Multi-Agent AI health management system combining:
- **Multi-Agent Architecture**: Coordinator + specialized agents (Nutrition, Fitness, Mental Health, Diagnostic)
- **RAG Pipeline**: Vector database with verified health knowledge
- **Multimodal AI**: CV (food recognition, posture), NLP (voice, sentiment), Predictive (health forecasting)

## Tech Stack

- **Agent Framework**: LangChain or AutoGen
- **Vector DB**: FAISS (local) or Pinecone (cloud)
- **ML Framework**: PyTorch, Hugging Face Transformers
- **CV Models**: YOLOv11 (food), MediaPipe (posture)
- **NLP Models**: Whisper (speech), RoBERTa (sentiment)
- **Frontend**: Streamlit
- **Deployment**: Docker, GCP

## Key Directories

| Path | Purpose |
|------|---------|
| `src/agents/` | Multi-agent implementations |
| `src/rag/` | RAG pipeline (embeddings, retrieval) |
| `src/models/cv/` | Computer vision models |
| `src/models/nlp/` | NLP models |
| `src/app/` | Streamlit dashboard |
| `data/knowledge_base/` | RAG knowledge documents |
| `config/prompts/` | Agent system prompts |

## Coding Conventions

- Python 3.10+
- Use type hints
- Docstrings for all public functions
- Black formatter, isort for imports
- Pytest for testing

## Current Phase

Milestone 1 - Project Definition & Planning (Week 3)

## Team

4 members: Aziz Rahman, Tsering Wangchuk Sherpa, Mingxuan Li, Zhihuai Wang
