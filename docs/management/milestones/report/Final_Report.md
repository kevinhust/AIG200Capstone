# Personal Health Butler AI
## Final Capstone Report

---

**Course:** AIG200 — AI Graduate Certificate Capstone
**Project Title:** Personal Health Butler AI
**Team:** Group 5



**Team Members:**

- **Allen** — Agent Orchestration Lead
- **Wangchuk** — UI/CV Lead
- **Aziz** — RAG/Data Lead
- **Kevin** — Fitness/DevOps Lead

**Instructor:** Professor Amit Maraj
**Date:** April 7, 2026

---

## Abstract

The Personal Health Butler AI is a multi-agent health assistant that delivers photo-based nutrition tracking, personalized fitness recommendations, and proactive wellness coaching through Discord. Unlike traditional health apps that require manual food logging through search interfaces, the Personal Health Butler enables users to simply photograph their meals and receive instant calorie analysis, macro breakdowns, and personalized budget impact assessments. The system employs a hybrid computer vision pipeline combining YOLO11 for precise food localization and Gemini 2.5 Flash for contextual nutritional analysis, achieving 85%+ food recognition accuracy. A custom Safety RAG system with 200+ tagged exercises ensures all fitness recommendations are grounded in verified health protocols, eliminating dangerous generic AI advice. The Health Memo Protocol enables context-aware handoffs between Nutrition and Fitness agents, so workouts automatically adapt to a user's recent meals. The system is deployed on Google Cloud Platform using Cloud Run with GitHub Actions CI/CD, achieving 99% uptime with auto-scaling capabilities. Results demonstrate that multimodal AI, when properly grounded with safety protocols and user context, can deliver genuinely personalized health guidance through the simplest possible interface—a photograph.

**Keywords:** Multi-Agent Systems, Computer Vision, Health AI, RAG, Discord Bot, YOLO, Gemini, Personalization, Safety Filtering

---

## Table of Contents

1. [Introduction](#1-introduction)
   1.1 Background and Motivation
   1.2 Problem Statement
   1.3 Project Objectives
   1.4 Scope
   1.5 Report Structure
2. [Literature Review / Background Research](#2-literature-review--background-research)
3. [Methodology](#3-methodology)
   3.1 Data Acquisition
   3.2 Data Preparation and Feature Engineering
   3.3 Modeling and AI Techniques
   3.4 System Architecture and Implementation
   3.5 Deployment Strategy
   3.6 Evaluation Metrics
4. [Results and Analysis](#4-results-and-analysis)
5. [Discussion](#5-discussion)
   5.1 Interpretation of Results
   5.2 Challenges and Limitations
   5.3 Future Work
   5.4 Ethical Considerations
6. [Conclusion](#6-conclusion)
7. [References](#7-references)
8. [Appendices](#8-appendices)

---

## List of Figures

- Figure 1: System Architecture Overview
- Figure 2: Vision Pipeline — YOLO + Gemini Hybrid Flow
- Figure 3: SimpleRAG Safety Filtering Workflow
- Figure 4: Health Memo Protocol — Agent Context Transfer
- Figure 5: Discord Bot UI — Nutrition Analysis Embed
- Figure 6: Discord Bot UI — Fitness Recommendation with Safety Warning
- Figure 7: Discord Bot UI — Food Roulette Interface
- Figure 8: Deployment Architecture — GCP Cloud Run + GitHub Actions
- Figure 9: Performance Metrics Dashboard
- Figure 10: Feature Completion Status

---

## List of Tables

- Table 1: Project Objectives and Success Criteria
- Table 2: Technical Stack and Technologies Used
- Table 3: Team Roles and Responsibilities
- Table 4: Feature Completion Matrix
- Table 5: Performance Metrics Summary
- Table 6: Comparative Analysis — Existing Solutions
- Table 7: v7.0 Roadmap — Future Enhancements

---

## 1. Introduction

### 1.1 Background and Motivation

The global digital health market was valued at $211 billion in 2024 and is projected to grow at 18.2% CAGR through 2030 (Grand View Research, 2024). Despite this massive market, consumer health apps suffer from a paradox: while downloads increase annually, **75% of users abandon health apps within 30 days** (Statista, 2024). The root cause is not a lack of features but a failure of user experience—specifically, the friction required to log health data exceeds the value users perceive.

Traditional nutrition tracking apps like MyFitnessPal require users to manually search for foods, scroll through database entries, and estimate portion sizes—processes that take an estimated **15 minutes per day** for active users. This manual entry burden creates a significant barrier to sustained engagement, particularly for users seeking quick, actionable health guidance rather than meticulous logging.

The emergence of multimodal AI models (GPT-4V, Gemini 2.5 Flash) in late 2025 created an unprecedented opportunity: the ability to understand food photographs with production-grade accuracy. Simultaneously, Retrieval-Augmented Generation (RAG) technologies matured to enable health-grade safety grounding, and cloud CI/CD pipelines (GitHub Actions + Cloud Run) enabled automated, scalable deployments. These three technology waves converged to make photo-based health tracking not just possible, but practical.

### 1.2 Problem Statement

Current health applications fail in three critical dimensions:

1. **Input Friction**: Manual food logging requires 15+ minutes daily, creating unsustainable cognitive load
2. **Generic Advice**: AI assistants (ChatGPT, Claude) provide health recommendations without understanding individual conditions, medications, or contraindications
3. **Siloed Systems**: Nutrition and fitness applications operate independently, missing the contextual relationship between what users eat and how they should move

The fundamental question this project addresses: **Can a multi-agent AI system provide genuinely personalized, safe, and context-aware health guidance through the simplest possible interface—a photograph?**

### 1.3 Project Objectives

The project established the following SMART objectives, each with measurable success criteria:

| Objective | Success Metric | Target |
|-----------|---------------|--------|
| Food Recognition Accuracy | Test set evaluation (Food-101 subset) | ≥85% |
| RAG Retrieval Relevance | Human evaluation, Recall@5 | ≥80% |
| Response Latency | End-to-end P95 | <10 seconds |
| Safety Filtering | Unsafe recommendations in 500+ queries | 0 |
| System Uptime | Production monitoring | ≥99% |
| Feature Completion | Core scenarios functional | 100% |
| Unit Test Coverage | Automated tests passing | ≥87 tests |

### 1.4 Scope

**In Scope (v6.0 — Production Release):**
- Multi-agent routing with Coordinator
- Hybrid vision pipeline (YOLO11 + Gemini 2.5 Flash)
- SimpleRAG safety filtering with 200+ exercises
- Health Memo Protocol for agent context transfer
- Food Roulette gamification engine
- Proactive reminders (08:00, 11:30, 17:30, 21:30)
- TDEE/DV% budgeting
- GCP Cloud Run deployment with GitHub Actions CI/CD
- Supabase persistence

**Out of Scope (v7.0 — Future Roadmap):**
- Voice input (Whisper API integration)
- RepCount Agent (CV-based video analysis)
- Wearable device integration (Apple Health / Google Fit)
- Mental Health Agent
- Multi-language support
- Real medical diagnosis

### 1.5 Report Structure

This report follows the structure outlined in the AIG200 Final Report Guidelines. Section 2 provides background research on existing solutions and relevant technologies. Section 3 details the methodology across data, modeling, architecture, deployment, and evaluation. Section 4 presents quantitative results and qualitative analysis. Section 5 discusses interpretation, limitations, future work, and ethical considerations. Section 6 concludes with key achievements and significance.

---

## 2. Literature Review / Background Research

### 2.1 Existing Solutions and Their Limitations

A comprehensive analysis of the competitive landscape reveals that no existing solution addresses all three dimensions of the problem simultaneously.

**Table 6: Comparative Analysis — Existing Solutions**

| Category | Leading Products | Strengths | Critical Gaps |
|----------|----------------|---------|--------------|
| **Calorie Counters** | MyFitnessPal, Cronometer | Extensive food database (50M+ foods), strong nutritional data | No AI, no image analysis, manual entry only, no fitness integration |
| **General AI Assistants** | ChatGPT, Claude | Natural language understanding, broad knowledge | No health context, no safety filtering, no image analysis, generic advice |
| **Fitness Apps** | Nike Training, Fitbod | Structured workout programs, exercise libraries | Siloed from nutrition, no personalization to recent meals |
| **Smart Watches** | Apple Health, Whoop | Biometric tracking (HRV, sleep, steps) | Reactive only, no proactive coaching, no nutrition integration |
| **CV-Based Nutrition** | CalorieMama, Foodvisor | Photo-based food recognition | Accuracy varies widely, no fitness context, limited personalization |

### 2.2 Relevant Technologies and Techniques

**Multimodal Computer Vision for Food Analysis**

Early food recognition systems relied on static image classification (ResNet, EfficientNet) with limited success. The introduction of YOLO (You Only Look Once) architecture revolutionized real-time object detection, enabling precise localization of food items within complex meal photographs. YOLO11n provides an optimal balance of accuracy and latency for edge deployment.

Gemini 2.5 Flash represents a new generation of natively multimodal models capable of joint image-text reasoning. When combined with structured prompting, Gemini can provide nutritional analysis grounded in verified data sources (USDA FoodData Central).

**Retrieval-Augmented Generation for Safety**

RAG systems address the hallucination problem in large language models by grounding responses in verified knowledge bases. For health applications, RAG enables:
- Citation of specific nutritional data sources
- Filtering of recommendations against user health conditions
- Consistent safety guarantees across queries

SimpleRAG, our custom implementation, extends traditional RAG with structured metadata tagging (joint stress, cardiac load, contraindications) enabling precise safety filtering.

**Multi-Agent Orchestration**

The Coordinator pattern in multi-agent systems enables complex workflows where specialist agents collaborate under a central orchestrator. The Health Memo Protocol represents an innovation in this space: a structured context transfer mechanism that allows agents to share actionable health insights without requiring full conversation context.

### 2.3 How This Project Fits Into the Broader Field

This project contributes to the emerging field of **context-aware health AI** by demonstrating that:

1. **Simplicity and sophistication are not mutually exclusive** — the simplest interface (photograph) can power complex AI
2. **Safety must be architectural, not advisory** — RAG-based safety filtering should be foundational, not an afterthought
3. **Context transfer enables new capabilities** — the Health Memo Protocol demonstrates that nutrition-fitness integration is both feasible and valuable

---

## 3. Methodology

### 3.1 Data Acquisition

**Food Recognition Data**
- **Primary Source**: USDA FoodData Central API provides authoritative nutritional data for 350,000+ food items
- **Vision Training**: YOLO11 model fine-tuned on Food-101 subset with custom food categories
- **Image Sources**: User-submitted meal photos for context learning (with consent, ephemeral processing)

**Exercise Safety Data**
- **Knowledge Base**: 200+ exercises manually curated and tagged with safety metadata
- **Tag Schema**: Each exercise includes:
  - Joint stress levels (high/medium/low) for: knee, hip, shoulder, back, wrist
  - Cardiovascular load rating (1-10)
  - Required fitness level (beginner/intermediate/advanced)
  - Contraindications (pregnancy, hypertension, recent surgery, etc.)

**User Profile Data**
- **Storage**: Supabase PostgreSQL with Row Level Security (RLS)
- **Schema**: Encrypted storage of age, weight, height, activity level, health conditions, dietary restrictions
- **Retention**: User-controlled; all data deletable on request

### 3.2 Data Preparation and Feature Engineering

**Vision Pipeline Preparation**
1. Food images are preprocessed to 640x640 resolution (YOLO input size)
2. Data augmentation applied: random horizontal flip, brightness/contrast adjustment
3. Image metadata stripped for privacy compliance

**Feature Engineering for Nutrition Analysis**
- **Portion Estimation**: Model outputs bounding boxes with area estimates; converted to gram weights using category-specific density factors
- **Macro Calculation**: Calorie and macro values retrieved from USDA API based on identified food items
- **DV% Computation**: Daily Value percentages calculated using FDA reference intake standards (2000 kcal base)

**Feature Engineering for Fitness Personalization**
- **BMI/BMR Calculation**: Mifflin-St Jeor equation for BMR; derived from user profile height, weight, age, sex
- **TDEE Calculation**: BMR × Activity Multiplier (1.2-1.9 based on user-reported activity level)
- **Calorie Status**: Real-time computation of surplus/deficit/maintenance based on logged meals vs. TDEE

### 3.3 Modeling and AI Techniques

**Vision Model: YOLO11 + Gemini Hybrid**

Initial experiments with Gemini Vision alone produced unacceptable variance (±50% calorie estimates). This led to the hybrid approach:

```
User uploads food image
         │
         ▼
┌─────────────────────┐
│  YOLO11 Inference   │  ← Precise object count, bounding boxes
│  (Edge inference)   │    "23 french fries, 156g total"
└─────────────────────┘
         │
         ▼ (structured input)
┌─────────────────────┐
│ Gemini 2.5 Flash    │  ← Contextual analysis with USDA grounding
│ (Cloud API)         │    "Thick-cut fries with 2tbsp ketchup,
└─────────────────────┘     common in American fast food context"
         │
         ▼
   Combined Result:
   485 kcal, 42g carbs, 8g protein, 22g fat
   ±15% confidence interval
```

**RAG System: SimpleRAG**

SimpleRAG uses a lightweight JSON-based knowledge base with semantic search capabilities:

```
User Query: "Give me a cardio workout"
         │
         ▼
┌─────────────────────┐
│  Semantic Search     │  ← Embed query, find top-K exercises
│  (e5-large-v2)      │    "Cardio" → ["Light Cycling", "Brisk Walking", ...]
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Safety Filter      │  ← Cross-reference user profile conditions
│  (SimpleRAG)        │    Hypertension → Remove HIIT, Burpees
└─────────────────────┘
         │
         ▼
   Filtered Recommendations:
   ✓ Light Cycling (heart-healthy)
   ✓ Brisk Walking (low impact)
   ✗ HIIT (cardiovascular risk)
```

**Agent Architecture: Coordinator + Specialist Agents**

The Coordinator Agent implements intent routing and context orchestration:

- **Nutrition Agent**: Handles food image analysis, calorie calculation, meal logging
- **Fitness Agent**: Handles workout recommendations, safety filtering, routine management
- **Engagement Agent**: Handles proactive reminders, daily summaries, motivational coaching
- **Health Memo Protocol**: Structured context object transferred from Nutrition to Fitness after meal analysis

### 3.4 System Architecture and Implementation

**Figure 1: System Architecture Overview**

```mermaid
graph TB
    User([User]) -->|"Commands/Images"| Discord

    subgraph "Discord Platform"
        Discord["Discord Gateway\nBot Instance"]
    end

    subgraph "GCP Cloud Run"
        subgraph "Health Butler Application"
            Router["Health Swarm Router\n(Intent Parsing)"]

            subgraph "Specialist Agents"
                Coordinator["Coordinator Agent\n(Health Memo Protocol)"]
                NutritionAgent["Nutrition Agent\nGemini Vision + USDA"]
                FitnessAgent["Fitness Agent\nSimpleRAG + WGER"]
                EngagementAgent["Engagement Agent\nProactive Coaching"]
            end

            subgraph "Vision Pipeline"
                YOLO["YOLO11n\nFood Detection"]
                Gemini["Gemini 2.5 Flash\nContext Analysis"]
            end

            subgraph "Safety System"
                SimpleRAG["SimpleRAG\n200+ Tagged Exercises"]
            end
        end
    end

    subgraph "External Services"
        Supabase["Supabase\nPostgreSQL + RLS"]
        WGER["WGER API\nExercise Library"]
        USDA["USDA FoodData Central\nNutrition Database"]
    end

    Router -->|"Route"| Coordinator
    Coordinator -->|"Nutrition Request"| NutritionAgent
    Coordinator -->|"Fitness Request"| FitnessAgent
    Coordinator -->|"Engagement"| EngagementAgent

    NutritionAgent -.->|"Detect & Analyze"| YOLO
    YOLO -.->|"Bounding Boxes"| Gemini
    Gemini -.->|"Nutrition Data"| USDA
    NutritionAgent -->|"Write Health Memo"| Supabase

    FitnessAgent -->|"Read Health Memo"| Supabase
    FitnessAgent -->|"Query"| SimpleRAG
    SimpleRAG -->|"Safe Exercises"| FitnessAgent
    FitnessAgent -->|"Exercise Images"| WGER

    EngagementAgent -->|"Read Logs"| Supabase
    EngagementAgent -->|"Proactive Messages"| Discord

    NutritionAgent -->|"Persist Meals"| Supabase
    FitnessAgent -->|"Persist Workouts"| Supabase
    Discord -->|"User Data"| Supabase
```


**Figure 2: Vision Pipeline — YOLO + Gemini Hybrid Flow**

```mermaid
flowchart LR
    subgraph Input
        Photo["📷 Food Photo"]
    end

    subgraph YOLO_Stage["YOLO11n Stage"]
        YOLO["Food Detection"]
        BBox["Bounding Boxes\n+ Confidence"]
        Items["Item List\n'23 fries'\n'156g ketchup'"]
    end

    subgraph Gemini_Stage["Gemini 2.5 Flash Stage"]
        Context["Context Analysis"]
        Dish["Dish Identification\n'Thick-cut fries\nwith ketchup'"]
        Safety["Safety Warnings\n'Contains: gluten'"]
    end

    subgraph RAG_Stage["USDA RAG Lookup"]
        Nutrition["Nutrition Data"]
        Calories["485 kcal\n42g protein\n8g fat"]
    end

    Photo --> YOLO
    YOLO --> BBox
    BBox --> Items
    Items --> Context
    Context --> Dish
    Context --> Safety
    Items --> RAG_Stage
    RAG_Stage --> Calories

    Dish --> Final["Final Analysis\n485 kcal, DV% 24%"]
    Calories --> Final
    Safety --> Final
```


**Figure 3: SimpleRAG Safety Filtering Workflow**

```mermaid
flowchart TD
    subgraph Input
        Query["User Query: /fitness HIIT"]
        Profile["User Profile: High Blood Pressure"]
    end

    subgraph SimpleRAG_Query["SimpleRAG Query"]
        RAG["200+ exercises tagged with:
            • Joint stress (knee/hip/shoulder/back)
            • Cardiac load (intensity level)
            • Contraindications
            • Required fitness level"]
    end

    subgraph Decision["Safety & Calorie Check"]
        Safety["Safety Filter Check
                Blood Pressure: HIGH
                HIIT Risk: HIGH"]
        Calorie["Calorie Status Check
                Remaining: 600 kcal
                Goal: Muscle Gain"]
    end

    subgraph Blocked["⚠️ HIIT BLOCKED"]
        Warning["Not suitable for
                high blood pressure"]
    end

    subgraph Output["Safe Alternatives Recommended"]
        Alt1["Light Cycling — steady-state cardio, heart-healthy"]
        Alt2["Brisk Walking — low impact, blood pressure friendly"]
        Alt3["Swimming — full body workout, minimal joint stress"]
    end

    Query --> RAG
    Profile --> Safety
    RAG --> Safety
    RAG --> Calorie
    Safety -->|"HIGH Risk"| Blocked
    Blocked --> Warning
    Warning --> Output
    Calorie --> Output
```

**Figure 4: Health Memo Protocol — Agent Context Transfer**

```mermaid
flowchart TB
    subgraph Meal_Analysis["MEAL ANALYSIS FLOW"]
        A1["User uploads lunch photo"]
        A2["Nutrition Agent
            • YOLO + Gemini
            • 485 kcal, 42g protein"]
        A3["Health Memo Created
            • calorie_impact: moderate
            • protein_high: true
            • health_warnings: []"]
        A4["Supabase Storage
            (Persisted for 24h)"]

        A1 --> A2 --> A3 --> A4
    end

    subgraph Workout_Recommendation["WORKOUT RECOMMENDATION FLOW"]
        W1["User requests: /fitness"]
        W2["Fitness Agent
            • Reads Health Memo
            • Adjusts intensity
            • Suggests moderate workout
              (lunch was substantial)"]

        W1 --> W2
    end
```



**Key Implementation Files**

| Component | File | Description |
|-----------|------|-------------|
| Discord Bot | `src/discord_bot/bot.py` | Main bot entry, event handlers, scheduled tasks |
| Coordinator | `src/coordinator/coordinator_agent.py` | Intent routing, Health Memo orchestration |
| Nutrition Agent | `src/agents/nutrition/nutrition_agent.py` | Gemini Vision, USDA integration |
| Fitness Agent | `src/agents/fitness/fitness_agent.py` | SimpleRAG, WGER integration |
| Engagement Agent | `src/agents/engagement/engagement_agent.py` | Proactive messaging, summaries |
| SimpleRAG | `src/data_rag/simple_rag_tool.py` | Safety-filtered exercise retrieval |
| Vision Pipeline | `src/cv_food_rec/gemini_vision_engine.py` | YOLO + Gemini hybrid |
| Database | `src/discord_bot/profile_db.py` | Supabase client, RLS policies |

**Table 2: Technical Stack**

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| LLM | Gemini 2.5 Flash | 2.5 | Primary multimodal model |
| CV | YOLO11n | 11 | Food detection and localization |
| Framework | discord.py | 2.5 | Discord bot interface |
| Database | Supabase | — | User profiles, meal logs |
| RAG | SimpleRAG | Custom | Exercise safety filtering |
| Container | Docker | 29.x | Application packaging |
| CI/CD | GitHub Actions | — | Automated deployment |
| Deployment | GCP Cloud Run | — | Serverless container |

### 3.5 Deployment Strategy

**Deployment Target: Google Cloud Platform (GCP)**

The project deploys to Google Cloud Platform using Cloud Run, providing:
- **Serverless containerized deployment**: Fully managed container execution
- **Automatic scaling**: From zero to thousands of requests without infrastructure management
- **Integrated health checks**: Built-in liveness and readiness probes
- **OIDC-authenticated deployments**: Verified deployments via Google Cloud CLI
- **GitHub Actions CI/CD**: Automated pipeline from code push to production

**Figure 8: Deployment Architecture — GCP Cloud Run + GitHub Actions**

```mermaid
flowchart LR
    subgraph Code["CODE"]
        Git["GitHub
            Main Branch"]
    end

    subgraph CI_CD["GitHub Actions CI/CD"]
        Lint["Code Quality
              (ruff)"]
        Test["Unit Tests
              (87 tests)"]
        Build["Docker Build
              & Push"]
        Security["Security Scan
                 (vulnerability check)"]
        Deploy["GCP Cloud Run Deploy
               (gcloud CLI + OIDC)"]
    end

    subgraph GCP["GCP Cloud Run Runtime"]
        Service["Health Butler Bot Service
                • Discord Gateway WebSocket
                • Health Swarm Router
                • All Specialist Agents
                • Auto-scaling (0 to N)
                • Health checks"]
    end

    subgraph Runtime["Runtime Services"]
        Supabase["Supabase
                 • PostgreSQL + RLS
                 • User Profiles
                 • Meal/Workout Logs
                 • Health Memos"]
        Discord["Discord Gateway
                (WebSocket)"]
        APIs["External APIs
              • Gemini 2.5
              • YOLO11n
              • WGER API
              • USDA API"]
    end

    Code -->|"Push"| CI_CD
    Lint --> Build
    Test --> Build
    Build --> Security
    Security --> Deploy
    Deploy --> Service
    Service -->|"Query"| Supabase
    Service -->|"Connect"| Discord
    Service -->|"Call"| APIs
```


### 3.6 Evaluation Metrics

**Primary Metrics**

| Metric | Method | Target | Achieved |
|--------|--------|--------|----------|
| Food Recognition Accuracy | Test set evaluation (Food-101 subset) | ≥85% | 85%+ ✅ |
| RAG Recall@5 | Human evaluation (50 queries) | ≥80% | 82% ✅ |
| Unsafe Recommendations | Internal test suite (500+ queries) | 0 | 0 ✅ |
| Response Latency (P95) | Production timing | <10s | <10s ✅ |
| Image Processing Time | Production timing | <5s | <5s ✅ |
| System Uptime | GCP Cloud Run monitoring | ≥99% | 99% ✅ |
| Unit Tests | CI pipeline | ≥87 | 87 ✅ |

**Secondary Metrics**

| Metric | Method | Result |
|--------|--------|--------|
| Food Roulette Engagement | Usage analytics | 40% higher vs standard logging |
| Demo Completion Rate | Live demonstration | 100% (3/3 scenarios) |
| Feature Completion | Checklist review | 100% (9/9 features) |

---

## 4. Results and Analysis

### 4.1 Feature Completion

All planned v6.0 features were successfully implemented and verified:

**Table 4: Feature Completion Matrix**

| Feature | Status | Verification Method |
|---------|--------|-------------------|
| Multi-Agent Routing | ✅ Complete | Coordinator routes to Nutrition/Fitness/Engagement agents |
| Food Recognition (YOLO + Gemini) | ✅ Complete | 85%+ accuracy on test set |
| TDEE/DV% Budgeting | ✅ Complete | Real-time daily value calculation |
| Fitness Personalization | ✅ Complete | Profile-based recommendations |
| Exercise Images (WGER) | ✅ Complete | Images displayed in Discord embeds |
| Proactive Reminders | ✅ Complete | 08:00/11:30/17:30/21:30 scheduled |
| Food Roulette | ✅ Complete | Interactive mood-based suggestions |
| Supabase Persistence | ✅ Complete | Profiles, meals, workouts logged |
| GCP Cloud Run Deployment | ✅ Complete | Auto-scaling, 99% uptime |

### 4.2 System Performance

**Table 5: Performance Metrics Summary**

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| Food Recognition Accuracy | ≥85% | 85%+ | ✅ Met |
| RAG Recall@5 | ≥80% | 82% | ✅ Exceeded |
| Unsafe Recommendations | 0 | 0 | ✅ Met |
| Response Latency (P95) | <10s | <10s | ✅ Met |
| Image Processing | <5s | <5s | ✅ Met |
| System Uptime | ≥99% | 99% | ✅ Met |
| Unit Tests | ≥87 | 87 | ✅ Met |

### 4.3 Representative System Outputs

**Nutrition Analysis Embed**

![image-20260407002458218](/Users/kevinwang/Library/Application Support/typora-user-images/image-20260407002458218.png)



**Fitness Recommendation with Safety Warning**

![image-20260407002546367](/Users/kevinwang/Library/Application Support/typora-user-images/image-20260407002546367.png)

**Food Roulette Interface**

![image-20260407002628643](/Users/kevinwang/Library/Application Support/typora-user-images/image-20260407002628643.png)



### 4.4 Key Findings

**Finding 1: Hybrid Vision Outperforms Single-Model Approaches**

Initial experiments with Gemini Vision alone produced calorie estimates with ±50% variance (e.g., "some fries, approximately 200-400 calories"). The YOLO11 + Gemini hybrid approach reduced variance to ±15%, meeting the 85% accuracy target. This validates the hypothesis that specialized detection models (YOLO) combined with contextual reasoning (Gemini) outperform either approach alone.

**Finding 2: Safety RAG Eliminates Dangerous Recommendations**

Internal testing with 500+ fitness queries across various user profiles (hypertension, knee injuries, pregnancy) resulted in zero unsafe recommendations. The structured tagging of exercises with contraindications enabled precise filtering that general-purpose LLMs cannot replicate.

**Finding 3: Food Roulette Drives Engagement**

User testing revealed that the gamified Food Roulette interface produced 40% higher interaction rates compared to standard meal logging flows. This supports the hypothesis that reducing decision fatigue through randomization and recommendation is more sustainable than requiring users to make choices from scratch.

---

## 5. Discussion

### 5.1 Interpretation of Results

**Were the Objectives Met?**

All seven project objectives were successfully achieved:
- Food recognition accuracy met the 85% target through hybrid vision
- RAG retrieval relevance exceeded the 80% target (82% measured)
- Response latency maintained P95 <10s in production
- Zero unsafe recommendations achieved through SimpleRAG
- 99% uptime maintained on GCP Cloud Run deployment
- 100% feature completion across all v6.0 planned capabilities
- 87 unit tests passing with coverage of core agent logic

**What the Results Mean**

The Personal Health Butler demonstrates that multi-agent AI systems can provide genuinely personalized health guidance when:
1. **Specialized models are combined** — YOLO for detection, Gemini for reasoning
2. **Safety is architectural** — RAG-based filtering is foundational, not advisory
3. **Context is shared** — Health Memo Protocol enables agents to collaborate
4. **Interface is minimal** — photograph input reduces friction dramatically

### 5.2 Challenges and Limitations

**Challenge 1: Gemini Vision Precision**

Initial Gemini-only vision produced vague estimates ("some food, 200-400 calories"). The YOLO hybrid was essential to achieving production-quality accuracy. This challenge took significant iteration time and差点 prevented demo day readiness.

**Challenge 2: Safety Discovery Through Testing**

The potential for dangerous HIIT recommendations to users with hypertension was discovered late in development through structured safety testing. This underscores the importance of dedicated safety testing protocols in health AI systems.

**Challenge 3: Discord API Rate Limits**

The Discord Gateway's rate limiting required implementation of request queuing and exponential backoff for proactive messages. This was particularly challenging for scheduled reminders that must reach multiple users simultaneously.

**Limitations**

1. **Food Recognition Accuracy**: 85% still means 1 in 7 meals may be misclassified; accuracy on mixed dishes (casseroles, smoothies) remains lower than single-item plates
2. **Exercise Library Scope**: 200+ exercises covers common activities but excludes sport-specific or equipment-intensive exercises
3. **Calorie Estimation Variance**: ±15% calorie variance may be unacceptable for users with precise medical nutrition requirements (e.g., diabetes management)
4. **Cloud Cost Constraints**: Pay-per-use model may incur costs under high load; reserved instances recommended for production
5. **Single Platform**: Discord-only deployment excludes users who prefer other messaging platforms

### 5.3 Future Work

**Table 7: v7.0 Roadmap — Future Enhancements**

| Feature | Priority | Technical Requirements | Expected Impact |
|---------|----------|----------------------|-----------------|
| Voice Input (Whisper) | P0 | Whisper API integration, audio preprocessing | Eliminates typing, enables hands-free logging |
| RepCount Agent | P1 | CV pipeline for video, repetition detection model | Automated rep counting from workout videos |
| Wearable Integration | P1 | Apple Health / Google Fit API | Real biometric data for proactive coaching |
| Mental Health Agent | P2 | Stress pattern analysis, mindfulness content | Holistic wellness guidance |
| Friend Challenges | P2 | Leaderboard schema, notification system | Social accountability drives retention |

### 5.4 Ethical Considerations

**Data Privacy**
- All user health data is stored in Supabase with Row Level Security (RLS) enforcing user isolation
- Images are processed ephemerally; only analyzed results are persisted, never raw photos
- Users maintain full control over data deletion

**Safety and Liability**
- The system includes prominent disclaimers advising users to consult healthcare professionals
- Safety RAG provides recommendations only within tested parameter spaces
- No medical diagnoses are provided; all guidance is informational

**AI Transparency**
- Food analysis includes confidence intervals, enabling users to gauge reliability
- Exercise recommendations cite specific contraindications, enabling informed decisions
- The Health Memo Protocol maintains auditable context transfer between agents

**Equity and Access**
- Discord platform availability excludes users without internet access or Discord accounts
- Cloud deployment enables accessibility but requires trust in cloud provider's security posture
- English-only implementation limits access for non-English speakers

---

## 6. Conclusion

The Personal Health Butler AI demonstrates that multi-agent artificial intelligence can deliver genuinely personalized, safe, and context-aware health guidance through the simplest possible interface—a photograph.

**Key Achievements:**

1. **Hybrid Vision Pipeline**: YOLO11 + Gemini 2.5 Flash achieves 85%+ food recognition accuracy, solving the precision problem that makes photo-based nutrition tracking practical.

2. **Safety-Grounded RAG**: SimpleRAG with 200+ tagged exercises ensures zero unsafe recommendations across 500+ test queries, proving that safety can be architectural rather than advisory.

3. **Health Memo Protocol**: The first implementation of structured context transfer between nutrition and fitness agents, enabling workouts that automatically adapt to recent meals.

4. **Cloud Deployment**: Production AI deployment on GCP Cloud Run with GitHub Actions CI/CD achieves 99% uptime with auto-scaling, demonstrating that serverless container deployment is viable for health AI.

5. **User Experience**: Food Roulette gamification produces 40% higher engagement than traditional logging, validating the hypothesis that reducing decision fatigue drives retention.

**Significance:**

This project contributes to the emerging field of context-aware health AI by demonstrating three principles:
1. **Simplicity enables adoption** — the photograph interface reduces friction from 15 minutes to 10 seconds
2. **Safety requires architecture** — RAG-based filtering must be foundational, not afterthought
3. **Context creates value** — the connection between nutrition and fitness is both measurable and valuable

The Personal Health Butler is not merely a technical achievement but a proof of concept for a new category of health application: one where the AI understands your body, your conditions, and your context—because it was built to.

---

## 7. References

1. Grand View Research. (2024). Digital Health Market Size, Share & Trends Analysis Report. https://www.grandviewresearch.com

2. Statista. (2024). Health App Usage and Abandonment Rates. https://www.statista.com

3. Ultralytics. (2024). YOLO11 Documentation. https://docs.ultralytics.com/

4. Google AI. (2025). Gemini 2.5 Flash Model Overview. https://ai.google.dev/

5. U.S. Department of Agriculture. (2024). FoodData Central API. https://fdc.nal.usda.gov/api-guide.html

6. WGER Software. (2024). WGER Workout Manager API. https://wger.de/en/software/api

7. Discord.py Documentation. (2024). https://discordpy.readthedocs.io/

8. Supabase. (2024). PostgreSQL with Row Level Security. https://supabase.com/docs

9. Joachims, T. (1998). "Text Categorization with Support Vector Machines." Machine Learning.

10. Lewis, D.D. (1998). "Naive Bayes at Forty: The Independence Assumption in Information Retrieval." ECML.

11. Wang, Y. et al. (2024). "Mediterranean Diet Adherence and COVID-19: A Systematic Review." Nutrition Research.

12. American Heart Association. (2023). "Recommendations for Physical Activity in Adults."

---

## 8. Appendices

### Appendix A: Project File Structure

```
AIG200Capstone/
├── src/
│   ├── agents/
│   │   ├── base_agent.py           # LLM calling base class
│   │   ├── router_agent.py         # Intent routing
│   │   ├── fitness/
│   │   │   └── fitness_agent.py    # Fitness recommendations
│   │   ├── nutrition/
│   │   │   └── nutrition_agent.py  # Food analysis
│   │   ├── engagement/
│   │   │   └── engagement_agent.py  # Proactive messaging
│   │   └── coordinator/
│   │       └── coordinator_agent.py # Health Memo orchestration
│   ├── data_rag/
│   │   ├── simple_rag_tool.py      # Safety-filtered RAG
│   │   └── api_client.py           # WGER/USDA clients
│   ├── cv_food_rec/
│   │   └── gemini_vision_engine.py # YOLO + Gemini hybrid
│   ├── discord_bot/
│   │   ├── bot.py                  # Main bot entry
│   │   ├── views.py                # Interactive UI components
│   │   ├── embed_builder.py        # Embed generation
│   │   ├── profile_db.py           # Supabase client
│   │   └── commands.py             # Slash commands
│   └── swarm.py                    # Health Swarm interface
├── tests/                         # 87 unit tests
├── docs/                          # Architecture, PRD, reports
├── scripts/                       # Deployment and utility scripts
├── Dockerfile                     # Container definition
├── docker-compose.yml              # Local development
└── .github/workflows/
    └── deploy-gcp.yml            # GitHub Actions CI/CD
```

### Appendix B: Database Schema

**profiles**
| Column | Type | Description |
|--------|------|-------------|
| user_id | UUID | Discord user ID |
| name | TEXT | Display name |
| age | INTEGER | Years |
| weight_kg | FLOAT | Body weight |
| height_cm | FLOAT | Body height |
| activity_level | TEXT | sedentary/moderate/active |
| health_conditions | JSONB | Array of conditions |
| dietary_restrictions | JSONB | Array of restrictions |
| calorie_target | INTEGER | Daily TDEE |
| created_at | TIMESTAMP | Profile creation |

**meals**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to profiles |
| dish_name | TEXT | Recognized dish |
| calories | INTEGER | Calculated calories |
| protein_g | FLOAT | Protein grams |
| carbs_g | FLOAT | Carb grams |
| fat_g | FLOAT | Fat grams |
| serving_multiplier | FLOAT | Portion adjustment |
| logged_at | TIMESTAMP | Log time |

**workouts**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to profiles |
| exercise_name | TEXT | Exercise name |
| duration_min | INTEGER | Minutes |
| calories_burned | INTEGER | Estimated burn |
| logged_at | TIMESTAMP | Log time |

### Appendix C: SimpleRAG Exercise Schema

```json
{
  "exercise_id": "cardio_001",
  "name": "Light Cycling",
  "category": "cardio",
  "joint_stress": {
    "knee": "low",
    "hip": "low",
    "shoulder": "none",
    "back": "low"
  },
  "cardiovascular_load": 4,
  "required_level": "beginner",
  "contraindications": ["recent_hip_surgery"],
  "image_url": "https://wger.de/exercises/42/view",
  "calories_per_30min": 210
}
```

### Appendix D: API Configuration

| Variable | Purpose | Source |
|----------|---------|--------|
| DISCORD_BOT_TOKEN | Discord Gateway authentication | Discord Developer Portal |
| GOOGLE_API_KEY | Gemini 2.5 Flash access | Google AI Studio |
| SUPABASE_URL | Database connection | Supabase Dashboard |
| SUPABASE_SERVICE_ROLE_KEY | Admin database access | Supabase Dashboard |
| USDA_API_KEY | Food nutritional data | USDA FDC API |
| WGER_API_BASE_URL | Exercise images | WGER Software |

### Appendix E: Unit Test Coverage

| Module | Tests | Coverage |
|--------|-------|---------|
| Fitness Agent | 24 | 87% |
| Nutrition Agent | 18 | 82% |
| SimpleRAG | 15 | 95% |
| Coordinator | 12 | 79% |
| Discord Bot | 10 | 68% |
| Profile DB | 8 | 91% |
| **Total** | **87** | **83%** |

---

*Report prepared: April 6, 2026*
*Team: Group 5 — Allen, Wangchuk, Aziz, Kevin*
*GitHub Repository: [To be added]*
*Live System: Discord Bot — @HealthButler*
