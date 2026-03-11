# L1 Business Architecture
# Personal Health Butler AI

> **Version**: 6.1
> **Last Updated**: March 10, 2026
> **Parent Document**: [PRD v6.0](./PRD-Personal-Health-Butler.md)
> **TOGAF Layer**: L1 - Business Architecture

---

## 1. Business Context & Strategy

### 1.1 Value Proposition Canvas

| Segment | Customer Job | Pains | Gains |
|---------|--------------|-------|-------|
| **Busy Professional (Alex)** | Track nutrition intake | Manual logging is tedious | **Visual Logging**: Snap a photo, done |
| | Maintain balanced diet | Generic advice is useless | **Personalized**: Suggestions based on *my* TDEE and DV% |
| | Get quick health answers | "Dr. Google" is unreliable | **Grounded**: Evidence-based answers (USDA/WHO) |
| | Decide what to eat | Decision fatigue at mealtime | **Gamified**: Food Roulette🎰 solves "what to eat" |
| | Remember to log meals | Forgetfulness | **Proactive**: Pre-meal reminders (11:30/17:30) |

**Product Value Map:**
- **Product**: AI Health & Nutrition Assistant (v6.0)
- **Pain Relievers**: Instant calorie/macro estimation with DV%, evidence-backed answers, gamified suggestions.
- **Gain Creators**: Daily summaries, budget-aware meal inspiration, persistent profiles.

### 1.2 Quantitative Business Goals (KPIs)

| Metric | Target | Business Value |
|--------|--------|----------------|
| **Efficiency** | Reduce logging time by >80% | High retention via easy visual logging |
| **Trust** | >98% Semantic Accuracy | Gemini-powered multimodal verification |
| **Safety** | Zero Critical Errors | Safety RAG filtering for health conditions |
| **Latency** | <5s for Initial Detection | Fast feedback via YOLO11 |
| **Engagement** | +40% DAU vs v5 | Food Roulette usage, reminder response |
| **Retention** | Persistent profiles | Supabase-backed user data |

---

## 2. Business Process Architecture

### 2.1 Level 0: Context Diagram

```mermaid
graph LR
    %% Style Definitions
    classDef person fill:#FFD700,stroke:#333,stroke-width:2px,color:black,rx:10,ry:10;
    classDef system fill:#87CEEB,stroke:#2b4b6f,stroke-width:2px,color:black,rx:5,ry:5;
    classDef external fill:#98FB98,stroke:#2e8b57,stroke-width:2px,color:black,stroke-dasharray: 5 5;
    classDef db fill:#DDA0DD,stroke:#800080,stroke-width:2px,color:black,shape:cylinder;

    User((User)):::person
    PHB[Personal Health Butler v6.0]:::system
    External[Knowledge Sources<br/>USDA/WHO]:::external
    Supa[("Supabase<br/>Profiles/Logs")]:::db

    User -->|Uploads Meal Photo<br/>Asks Question<br/>Spins Roulette| PHB
    PHB -->|Provides Analysis<br/>& Advice + DV%| User
    PHB -->|Retrieves &<br/>Verifies Data| External
    PHB -->|Persist/Retrieve| Supa
```

### 2.2 Level 1: Business Capability Map

| Strategic | Core | Support |
|-----------|------|---------|
| **Health Insights**<br>- Nutrition Analysis<br>- DV% Budget Tracking<br>- Trend Forecasting | **Interaction**<br>- Visual Recognition (YOLO11)<br>- Natural Language QA<br>- Food Roulette🎰 | **Knowledge Mgmt**<br>- Data Ingestion<br>- Compliance/Privacy |
| **Orchestration**<br>- Intent Routing<br>- Agent Coordination | **Action Planning**<br>- Diet Recommendations<br>- Exercise Adjustment<br>- Meal Suggestions | **User Mgmt**<br>- Persistent Profiles<br>- Preference Storage<br>- Proactive Reminders |

### 2.3 Level 2: Core Business Processes

#### process_01: Meal Analysis & Budget Tracking (v6.0)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Bot as 🤖 Discord Bot
    participant Coord as 🧠 Coordinator
    participant NutAg as 🍎 Nutrition Agent
    participant FitAg as 🏃 Fitness Agent
    participant KB as 📚 Knowledge Base
    participant Supa as 🗄️ Supabase

    User->>Bot: 📸 Uploads Photo ("Analyze this!")
    activate Bot
    Bot->>Supa: 👤 Get User Profile
    Supa-->>Bot: Profile + TDEE Budget
    Bot->>Coord: 🔄 Route Task (Image + Profile)
    activate Coord
    Coord->>NutAg: 🔄 Route to Nutrition
    activate NutAg
    NutAg->>NutAg: 👁️ YOLO11 Detection
    NutAg->>NutAg: 🧠 Gemini Analysis
    NutAg->>KB: 🔍 Retrieve Nutrition Data
    NutAg->>NutAg: 📊 Calculate DV% Impact
    NutAg-->>Coord: ✅ Macros + DV% + Suggestions
    deactivate NutAg

    Coord->>FitAg: 💡 Request Safe Exercises
    activate FitAg
    FitAg->>FitAg: 🛡️ Check Safety Protocols
    FitAg-->>Coord: 🚶 "Swimming (Safe for Knee Injury)"
    deactivate FitAg

    Coord-->>Bot: 💬 Consolidated Response
    deactivate Coord
    Bot->>Supa: 💾 Store Meal Log
    Bot-->>User: 📱 Rich Embed + Progress Bars
    deactivate Bot
```

#### process_02: Food Roulette🎰 (v6.0 NEW)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Bot as 🤖 Discord Bot
    participant Roulette as 🎰 Roulette Engine
    participant Supa as 🗄️ Supabase

    User->>Bot: 🎰 "Spin for dinner suggestion"
    activate Bot
    Bot->>Supa: 📊 Get Remaining Budget
    Supa-->>Bot: 450 cal remaining
    Bot->>Roulette: 🎲 Generate Suggestions
    activate Roulette
    Roulette->>Roulette: 🔍 Filter by Budget
    Roulette-->>Bot: 🍜 3 Budget-Compliant Options
    deactivate Roulette
    Bot-->>User: 🎰 Animated Selection View
    User->>Bot: ✅ Select Option
    Bot-->>User: 📋 Meal Details + Macros
    deactivate Bot
```

#### process_03: Proactive Reminders (v6.0 NEW)

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as ⏰ Task Scheduler
    participant Bot as 🤖 Discord Bot
    participant Supa as 🗄️ Supabase
    actor User

    Note over Scheduler: 11:30 / 17:30 Trigger
    Scheduler->>Bot: 🔔 Pre-meal Reminder
    activate Bot
    Bot->>Supa: 📊 Check Today's Logs
    Supa-->>Bot: Logs + Remaining Budget
    Bot->>User: 💬 "Lunch time! Budget: 600 cal remaining"
    User->>Bot: 📸 Upload Meal
    Bot->>Bot: 🔄 Process & Log
    Bot-->>User: ✅ Logged + Updated Budget
    deactivate Bot
```

---

## 3. Agent Collaboration Model

### 3.1 Agent Responsibility Matrix

| Agent | Role | Input | Output | Success Metric |
|-------|------|-------|--------|----------------|
| **Coordinator** | Traffic Control | User Query/media | Routed Task / Final Response | 99% routing accuracy |
| **Nutrition Agent** | Domain Expert | Image/Food Name + Profile | Macros + DV% + Diet Advice | 85% food recognition recall |
| **Fitness Agent** | Support Coach | Calorie surplus/deficit | Activity Recommendation | Relevant, safe suggestions |
| **Roulette Engine** | Gamification | Remaining budget + Preferences | Budget-compliant meal options | +40% engagement |
| **Task Scheduler** | Proactive Engagement | Time triggers | Reminder messages | Improved DAU |

### 3.2 Interaction Pattern (Star Topology)

- **Central Hub**: Coordinator Agent manages all state and routing.
- **Spokes**: Specialized agents (Nutrition, Fitness, Roulette) are stateless workers.
- **Persistence**: Supabase stores profiles, logs, and budgets.
- **Protocol**: JSON-structured messages (AgentTask → AgentResult).

---

## 4. Business Rules & Compliance

### 4.1 Ethical AI Rules (BR-ETHICS)

- **BR-001 (No Diagnosis)**: System MUST NOT provide medical diagnoses. All responses regarding symptoms must contain a disclaimer: "Consult a medical professional."
- **BR-002 (Bias Mitigation)**: Food recognition and health advice MUST cover diverse cultural diets and body types.
- **BR-003 (Citation)**: All health claims MUST cite a verified source (USDA, WHO, or peer-reviewed DB).

### 4.2 Privacy Rules (BR-PRIVACY) (GDPR/HIPAA-aligned)

- **BR-004 (Data Minimization)**: Only collect data strictly necessary for the immediate analysis.
- **BR-005 (Ephemeral Image Storage)**: User photos are processed in-memory and never persisted to disk.
- **BR-006 (Anonymization)**: Any analytics data MUST be stripped of all PII.
- **BR-007 (User Control)**: Users can delete their profiles and logs from Supabase at any time.

### 4.3 Gamification Rules (BR-GAME) - v6.0 NEW

- **BR-008 (Budget Compliance)**: Roulette suggestions MUST NOT exceed remaining calorie budget.
- **BR-009 (Preference Respect)**: Suggestions MUST respect dietary preferences (vegetarian, halal, etc.).

---

## 5. v6.0 Feature Summary

| Feature | Business Value | User Value |
|---------|----------------|------------|
| **YOLO11 Vision** | Higher accuracy → more trust | Better food recognition |
| **TDEE/DV% Budgeting** | Personalized insights | Know real daily impact |
| **Food Roulette🎰** | Increased engagement | Decision fatigue relief |
| **Proactive Reminders** | Higher DAU | Don't forget to log |
| **Supabase Persistence** | Better retention | Seamless cross-session experience |

---

**Document Status**: 🟢 Version 6.0 - Aligned with v6.0 Features
