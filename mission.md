# 🎯 Mission: Personal Health Butler AI

> The single source of truth for the project's high-level objective.

## Vision

Build an **AI-powered nutrition assistant** that helps users track meals and make healthier choices.

## Core Features (MVP)

1. **Visual Food Recognition** - Snap a photo → instant food identification (ViT)
2. **Nutrition Analysis** - Accurate calorie and macro breakdown (RAG + USDA)
3. **Personalized Advice** - Evidence-based dietary suggestions (LLM)
4. **Fitness Integration** - Post-meal activity recommendations

## Success Metrics

| Metric | Target |
|--------|--------|
| Food Recognition Accuracy | ≥85% on Food-101 |
| RAG Retrieval Relevance | ≥80% Recall@5 |
| End-to-End Latency | <10s (P95) |
| Demo Completeness | 3 core scenarios |

## Team Roles (Updated 2026-01-27)

| Member | Responsibility |
|--------|----------------|
| Kevin | RAG Pipeline + Coordinator Agent |
| Wangchuk | Nutrition Agent + UI |
| Aziz | Fitness Agent |
| Allen | UI Integration |

## Current Phase: Prototype Integration

- [x] ViT model setup (StatsGary/VIT-food101-image-classifier)
- [x] ChromaDB RAG pipeline (338 documents)
- [x] USDA data ingestion (137 common foods + 97 Food-101)
- [x] HealthSwarm orchestrator created
- [ ] Swarm integration with UI
- [ ] End-to-end testing
- [ ] Demo scenarios

## Out of Scope (This Phase)

- Mental health features
- Wearable device integration
- Voice input (Whisper)
- Production deployment
- Multi-language support

## Note

This file defines the project mission. Update it when scope changes.
