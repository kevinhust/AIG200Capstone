# Product Requirements Document (PRD)
**Personal Health Butler AI**
**Version**: 6.0 (Performance & Play)
**Last Updated**: March 10, 2026
**Team**: Group 5 (Allen, Wangchuk, Aziz, Kevin)
**Status**: 🟢 In Production (v6.0)

### Document History
| Version | Date | Author | Description of Change |
| :--- | :--- | :--- | :--- |
| **1.0** | 2026-01-10 | Group 5 | Initial Draft |
| **1.1** | 2026-01-16 | Group 5 | Finalized for Milestone 1 MVP Scope |
| **1.2** | 2026-01-21 | Kevin (Docs) | Architecture Pivot: Exploration of ViT classification. |
| **1.3** | 2026-02-11 | Kevin (Docs) | **Final Architecture Realignment**: Implemented **Hybrid Vision (YOLOv8 + Gemini)**, **Discord Interface**, and **5-Step Safety Onboarding**. Replaced legacy ViT and Streamlit. |
| **6.0** | 2026-03-10 | Kevin (Docs) | **v6.0 Performance & Play**: YOLO11 upgrade, TDEE/DV% budgeting, Food Roulette🎰 gamification, proactive reminders, Supabase persistence. |

---

### 1. Executive Summary

#### 1.1 Product Vision
The **Personal Health Butler AI** is a professional-grade, AI-powered health and fitness assistant that leverages **Multi-Agent Architecture** and **Retrieval-Augmented Generation (RAG)** to deliver personalized, evidence-based wellness guidance. Version 6.0 introduces high-precision **YOLO11** vision, deep nutritional budgeting (**TDEE/DV%**), and gamified **Food Roulette🎰** interaction.

#### 1.2 Problem Statement
Current health apps often provide generic or ungrounded advice, lack integration across nutrition and fitness, and fail to deliver quick, visual-input-based insights. Users also face "decision fatigue" when choosing meals. This product addresses these by:
- **Visual meal analysis** with trustworthy, cited recommendations
- **Personalized budget tracking** showing real daily impact (DV%)
- **Gamified meal suggestions** to reduce decision fatigue

#### 1.3 Proposed Solution (v6.0)
A Multi-Agent system with:
- **Intelligent Coordinator**: LLM-based routing logic for specialist agents.
- **Nutrition Agent**: Hybrid Vision (YOLO11 + Gemini Flash) with TDEE/DV% budgeting.
- **Fitness Agent**: Safety-first advice filtered by structured health protocols.
- **Discord Bot**: Accessible, conversational interface with rich onboarding views.
- **Proactive Engagement**: Pre-meal reminders and nightly summaries.
- **Gamified Interaction**: Food Roulette🎰 for budget-aware meal inspiration.
- **Persistent Profiles**: Supabase-backed user profiles and meal logs.

---

### 2. Project Scope

#### 2.1 In-Scope (v6.0 Features)

| Feature | Description | Priority |
|---------|-------------|----------|
| **YOLO11 Vision** | State-of-the-art food localization and ingredient analysis | P0 |
| **TDEE/DV% Budgeting** | Mifflin-St Jeor calculation + real-time Daily Value % tracking | P0 |
| **Food Roulette🎰** | Gamified, budget-aware meal suggestion engine | P0 |
| **Proactive Reminders** | Pre-meal triggers (11:30/17:30) + daily summaries | P0 |
| **Safety RAG** | Enhanced RAG with custom safety protocols for health-sensitive advice | P0 |
| **Professional Onboarding** | 5-Step interactive flow (Basic Info, Goals, Conditions, Activity, Diet) | P0 |
| **Discord Integration** | Rich UI using Modals, Select Menus, and Multi-select Views | P0 |
| **Supabase Persistence** | User profiles, meal logs, and macro budgets | P0 |
| **Context-Aware Recommendations** | Personalized advice based on BMI, health conditions, and real-time calorie balance | P0 |

#### 2.2 Out-of-Scope (Future Extensions)
- Mental Health Agent
- Posture Analysis (MediaPipe)
- Voice Input (Whisper)
- Predictive Analytics (LSTM/Prophet trends)
- Smart Grocery Recommendations
- Wearable Device Integration
- Real medical diagnosis or multi-language support

#### 2.3 Success Criteria
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Food recognition accuracy | ≥85% | Test set evaluation (Food-101 subset) |
| RAG retrieval relevance (Recall@5) | ≥80% | Human evaluation on 50 sample queries |
| End-to-end response latency | <10s (P95) | End-to-end timing in production |
| User engagement (DAU) | +40% vs v5 | Food Roulette usage, reminder response rate |
| Demo completeness | 100% functional | All core scenarios working in Discord |

---

### 3. User Stories

#### 3.1 Primary Persona

**Name**: Alex (Demo User)
**Age**: 30
**Location/Context**: Busy professional in Toronto, Canada; enjoys diverse foods but aims for balanced nutrition.
**Goals**: Improve overall health through better meal tracking and simple fitness integration.
**Pain Points**:
- Unsure of meal calories/macros
- Needs evidence-based suggestions
- Wants quick, visual input methods
- Suffers from "decision fatigue" at mealtime

#### 3.2 Core User Stories

| ID | As a... | I want to... | So that... | Priority |
|----|---------|--------------|------------|----------|
| US-01 | User | Upload a photo of my meal | I can get calories/macros + DV% impact | P0 |
| US-02 | User | See my remaining calorie budget | I know what I can still eat today | P0 |
| US-03 | User | Spin Food Roulette🎰 | I get budget-aware meal inspiration without decision fatigue | P0 |
| US-04 | User | Get pre-meal reminders | I don't forget to log my meals | P0 |
| US-05 | User | Ask natural language questions about nutrition/fitness | I get evidence-based answers with citations | P0 |
| US-06 | User | Have my profile persist across sessions | I don't need to re-onboard every time | P0 |

---

### 4. Functional Requirements

#### 4.1 Multi-Agent System

| FR-ID | Component | Description | Input | Output |
|-------|-----------|-------------|-------|--------|
| FR-001 | Coordinator Agent | Routes user input to agents and synthesizes responses | Text/photo + context | Integrated response with evidence |
| FR-002 | Nutrition Agent | Analyzes food photo, provides nutrition advice with DV% | Image + query + profile | Calories/macros + DV% + suggestions |
| FR-003 | Fitness Agent | Generates exercise suggestions based on nutrition input | Nutrition data + user goals | Personalized recommendations |
| FR-004 | RAG Pipeline | Retrieves and grounds knowledge from verified sources | Query | Relevant chunks with sources |
| FR-005 | Discord Bot | Handles user interaction with rich UI | Uploads/queries | Embedded results + views |
| FR-006 | Budget Engine | Calculates TDEE and tracks DV% consumption | User profile + meal logs | Remaining budget + progress bars |
| FR-007 | Roulette Engine | Generates budget-compliant meal suggestions | Remaining budget + preferences | Animated suggestion carousel |

---

### 5. Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| **Performance** | E2E response time | <10s (P95) |
| **Performance** | Image processing | <5s |
| **Privacy** | Data handling | Ephemeral image processing, no PII in logs |
| **Cost** | LLM budget | <$15/month |
| **Scalability** | Deployment | Docker + Cloud Run ready |
| **Availability** | Uptime | 99% (Discord Gateway persistent) |

---

### 6. Technical Stack (v6.0)

| Category | Component | Selection | Rationale |
|----------|-----------|-----------|-----------|
| **LLM Interface** | Multimodal AI | **Gemini 2.5 Flash** | Native multimodal, fast, cost-effective |
| **CV Engine** | Object Detection | **YOLO11n** | Superior accuracy-to-latency ratio |
| **Interface** | Bot Framework | **discord.py** | Rich modals/views, professional UX |
| **Persistence** | Database | **Supabase (PostgreSQL)** | User profiles, meal logs, macro budgets |
| **RAG** | Vector Store | **ChromaDB** | Native Python, embedded workflow |
| **Embedding** | Model | **e5-large-v2** | Best-in-class open embedding |
| **Runtime** | Containerization | **Docker (Python 3.12)** | Modern deployment standard |

---

### 7. Team Roles & Responsibilities

| Member | Primary Role | Modules | Secondary |
|--------|--------------|---------|-----------|
| **Allen** | Agent Orchestration Lead | Coordinator, Integration/Deployment | Full-stack support |
| **Wangchuk** | UI/CV Lead | Discord Bot, Nutrition Agent | Data exploration |
| **Aziz** | RAG/Data Lead | RAG Pipeline, Safety Protocols | Knowledge curation |
| **Kevin** | Fitness/Docs Lead | Fitness Agent, Documentation | Deployment polish |

---

### 8. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM cost overrun | High | Medium | Monitor usage, use Gemini Flash + caching |
| Vision accuracy below target | Medium | Low | YOLO11 + Gemini dual verification |
| Discord API rate limits | Medium | Low | Implement backoff, queue non-critical messages |
| Supabase connection issues | High | Low | Connection pooling, graceful degradation |

---

## 9. Appendix

### 9.1 Glossary
- **RAG**: Retrieval-Augmented Generation
- **TDEE**: Total Daily Energy Expenditure (Mifflin-St Jeor formula)
- **DV%**: Daily Value Percentage (nutrition budget tracking)
- **YOLO**: You Only Look Once (real-time object detection)

### 9.2 References
- USDA API: https://fdc.nal.usda.gov/api-guide.html
- YOLO11: https://docs.ultralytics.com/
- Discord.py: https://discordpy.readthedocs.io/
- Supabase: https://supabase.com/docs
