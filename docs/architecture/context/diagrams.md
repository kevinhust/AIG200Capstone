# Architecture Comparison Diagrams

This document visualizes the evolution from Milestone 1 design through v10.0 production implementation.

> **Current Version**: v10.0 (GCP Cloud Run + Health Memo Protocol)
> **Last Updated**: April 7, 2026
> **Status**: PRODUCTION

---

## Diagram 1: v10.0 Current Production Architecture

**GCP Cloud Run Deployment + GitHub Actions CI/CD**

*Key Features:*
*   **Hybrid Vision Pipeline**: YOLO11n (precision) + Gemini 2.5 Flash (context)
*   **Health Memo Protocol**: Context transfer between Nutrition → Fitness agents
*   **Safety RAG**: 200+ exercises tagged with contraindications
*   **GCP Cloud Run**: Serverless containerized deployment
*   **GitHub Actions CI/CD**: Automated build, test, and deployment

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

---

## Diagram 2: Vision Pipeline — Hybrid Architecture

**YOLO11n + Gemini 2.5 Flash**

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

---

## Diagram 3: Safety RAG — Query Flow

**SimpleRAG with 200+ Tagged Exercises**

```mermaid
flowchart TD
    subgraph Input
        Query["User Query\n'/fitness HIIT'"]
        Profile["User Profile\n'High blood pressure'"]
    end

    subgraph Safety_Filter
        RAG["SimpleRAG\nExercise Database"]
        Tags["Joint Stress Tags\nCardiac Load\nContraindications"]
    end

    subgraph Decision
        Block["Safety Check"]
        HighBP["Blood Pressure\nHigh Load?"]
    end

    subgraph Output
        Safe["Safe Alternatives\nLight Cycling\nBrisk Walking"]
        Rejected["⚠️ HIIT Blocked\n'Sorry, not suitable'"]
    end

    Query --> RAG
    Profile --> HighBP
    HighBP -->|"Yes"| Block
    Block -->|"High Risk"| Rejected
    Block -->|"Low Risk"| Safe
    RAG -->|"All Exercises"| Tags
```

---

## Diagram 4: Health Memo Protocol

**Context Transfer: Nutrition → Fitness**

```mermaid
sequenceDiagram
    participant User
    participant Bot as Discord Bot
    participant Nutrition as Nutrition Agent
    participant Fitness as Fitness Agent
    participant Supabase

    User->>Bot: 📷 Photo of lunch
    activate Bot

    Bot->>Nutrition: Analyze meal
    activate Nutrition

    Nutrition->>Nutrition: YOLO + Gemini processing
    Nutrition-->>Bot: 485 kcal, 42g protein
    Nutrition->>Supabase: Write Health Memo
    Note over Supabase: memo_type: meal_analyzed<br/>calorie_impact: moderate<br/>health_warnings: []

    Nutrition-->>Bot: Health Memo Created
    deactivate Nutrition

    User->>Bot: /fitness
    Bot->>Fitness: Get workout recommendation
    activate Fitness

    Fitness->>Supabase: Read Health Memo
    Supabase-->>Fitness: Recent meal: 485 kcal lunch
    Fitness->>Fitness: Adjust intensity<br/>Based on calorie intake

    Fitness-->>Bot: Moderate workout suggested
    Bot-->>User: 💪 Here's your workout...

    Note over User, Fitness: Evening workout adapts to morning meal!
```

---

## Diagram 5: GCP Cloud Run Deployment

**GitHub Actions CI/CD Pipeline**

```mermaid
flowchart LR
    subgraph Code
        Git["GitHub\nMain Branch"]
    end

    subgraph CI_CD["GitHub Actions"]
        Test["Unit Tests\n87 tests"]
        Lint["Code Quality\nruff linting"]
        Build["Docker Build\n& Push"]
        Security["Security Scan\nvulnerability check"]
    end

    subgraph GCP["Google Cloud Platform"]
        CloudRun["Cloud Run\nDiscord Bot Service"]
        Artifact["Artifact Registry\nDocker Images"]
    end

    subgraph Runtime
        Discord["Discord Gateway\nWebSocket"]
        Supabase["Supabase\nPostgreSQL"]
    end

    Git -->|"Push"| CI_CD
    CI_CD --> Test
    CI_CD --> Lint
    Test --> Build
    Lint --> Build
    Build --> Security
    Security -->|"Deploy"| CloudRun
    Build -->|"Store"| Artifact

    CloudRun -->|"Connect"| Discord
    CloudRun -->|"Query"| Supabase
```

---

## Diagram 6: Food Roulette Sequence

**Gamified Meal Suggestion**

```mermaid
sequenceDiagram
    participant User
    participant Bot as Discord Bot
    participant Roulette as Roulette Engine
    participant Supabase

    User->>Bot: 🎰 /roulette
    activate Bot

    Bot->>Supabase: Get user profile & budget
    activate Supabase
    Supabase-->>Bot: Budget: 600 kcal remaining
    deactivate Supabase

    Bot->>Roulette: Spin(remaining=600, mood)
    activate Roulette

    Roulette->>Roulette: Filter meals ≤600 kcal
    Roulette->>Roulette: Random selection with variety
    Roulette-->>Bot: "Greek Salad with Chicken\n420 kcal, 35g protein"
    deactivate Roulette

    Bot-->>User: 🎰 Food Roulette Embed
    Note over User: "Sounds Good?" / "Spin Again?"

    User->>Bot: Sounds Good ✓
    Bot->>Supabase: Log meal
    activate Supabase
    Supabase-->>Bot: Meal logged
    deactivate Supabase

    Bot-->>User: ✅ Added to today's log!
    deactivate Bot
```

---

## Diagram 7: Proactive Engagement Flow

**Scheduled Reminders & Daily Summaries**

```mermaid
flowchart TD
    subgraph Scheduler
        Cron["Scheduled Tasks\n08:00 / 11:30 / 17:30 / 21:30"]
    end

    subgraph Engagement
        Check["User State Check"]
        Send["Message Dispatch"]
    end

    subgraph Triggers
        Morning["08:00 Morning Check-in"]
        PreLunch["11:30 Pre-Lunch"]
        PreDinner["17:30 Pre-Dinner"]
        Evening["21:30 Evening Summary"]
    end

    Cron --> Morning
    Cron --> PreLunch
    Cron --> PreDinner
    Cron --> Evening

    Morning --> Check
    PreLunch --> Check
    PreDinner --> Check
    Evening --> Check

    Check -->|"Active User"| Send
    Send -->|"DM"| User([User])

    Morning -->|"Motivational\n+ Yesterday Stats"| User
    PreLunch -->|"Lunch Reminder\n+ Remaining Budget"| User
    PreDinner -->|"Dinner Suggestion\n+ Food Roulette"| User
    Evening -->|"Summary\n+ Tomorrow Preview"| User
```

---

## Version Comparison Table

| Component | v1.0 (ViT) | v5 (YOLOv8) | v10.0 (Current) |
|-----------|-------------|-------------|------------------|
| **Vision Model** | ViT Classifier | YOLOv8n + Gemini | **YOLO11n** + Gemini 2.5 Flash |
| **Interface** | Streamlit | Discord Bot | Discord Bot |
| **Fitness Logic** | Static | Safety RAG | Safety RAG + **Health Memo** |
| **Nutrition** | Calorie only | Calorie + Macros | **TDEE/DV% Budget** |
| **Gamification** | ❌ | ❌ | **Food Roulette🎰** |
| **Proactive** | ❌ | ❌ | **4 Daily Reminders** |
| **Persistence** | SQLite | SQLite | **Supabase** |
| **Deployment** | Local | NUC | **GCP Cloud Run** |
| **CI/CD** | Manual | SSH-based | **GitHub Actions** |
| **Safety RAG** | ❌ | Basic | **200+ exercises** |

---

## Architecture Decision Records

### ADR-001: Hybrid Vision Pipeline

**Context**: Gemini Vision alone produced ±50% calorie variance.

**Decision**: YOLO11n for precise bounding boxes + Gemini 2.5 Flash for context.

**Result**: 85%+ accuracy with consistent portion sizes.

### ADR-002: Safety-First Fitness

**Context**: Generic AI fitness advice could harm users with conditions.

**Decision**: SimpleRAG with 200+ exercises, each tagged with contraindications.

**Result**: 0 unsafe recommendations in 500+ test queries.

### ADR-003: Health Memo Protocol

**Context**: Nutrition and Fitness agents operated in silos.

**Decision**: Structured context transfer after each meal analysis.

**Result**: Evening workouts now adapt to morning meals.

---

## Data Flow: End-to-End Meal Logging

```mermaid
flowchart LR
    subgraph User_Input
        Photo["📷 Food Photo"]
    end

    subgraph Vision
        YOLO["YOLO11n"]
        Gemini["Gemini 2.5 Flash"]
    end

    subgraph Nutrition
        USDA["USDA Database"]
        TDEE["TDEE Calculator"]
        DV["DV% Tracker"]
    end

    subgraph Storage
        DB["Supabase"]
        Memo["Health Memo"]
    end

    subgraph Output
        Embed["Discord Embed"]
        Save["Add to Today"]
    end

    Photo --> YOLO
    YOLO --> Gemini
    Gemini --> USDA
    USDA --> TDEE
    TDEE --> DV
    DV --> Embed
    Embed --> Save
    Save --> DB
    DB --> Memo
```

---

*Document Status*: 🟢 Version 10.0 - Production Architecture Diagrams
*Last Updated*: April 7, 2026
