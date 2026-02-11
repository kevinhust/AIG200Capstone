# Architecture Comparison Diagrams

Based on `docs/ARCHITECTURE_COMPREHENSIVE_EVOLUTION.md`, these diagrams visualize the critical evolution from the original Milestone 1 design to the current implementation.

## Diagram 1: Original Design (L2 Architecture v2.0 - ViT)

**Key Characteristics:**
*   **Model**: **ViT (Vision Transformer)** (`StatsGary/VIT-food101-image-classifier`) for image classification.
*   **Linear Flow**: User -> Bot -> Coordinator -> Nutrition Agent -> ViT -> RAG.
*   **Simple Logic**: Fitness Agent was a basic calculator (Calories In - Out).
*   **Single RAG**: Only for nutrition data.

```mermaid
graph TD
    User([User]) -->|"Uploads Image"| APP/Web
    User -->|"Text Query"| APP/Web

    subgraph "Monolithic Bot Process"
        APP/Web --> Coordinator[Coordinator Agent]
        
        Coordinator -->|"Routing (Keywords)"| NutritionAgent
        Coordinator -->|"Routing (Keywords)"| FitnessAgent
    end

    subgraph "Vision System (Original - ViT)"
        NutritionAgent -->|"Call"| VisionTool["Vision Tool\n(ViT Model)"]
        VisionTool -->|"Classify"| Label["Food Label\n(e.g. 'Pizza')"]
        
        Label -->|"Lookup"| RAG1[RAG: Nutrition DB]
    end

    subgraph "Fitness System (Original)"
        FitnessAgent -->|"Calc"| formula[Simple Calorie Math]
        formula -->|"Recommend"| StaticEx[Static Exercises]
    end

    RAG1 --> Response
    StaticEx --> Response
    Response --> APP/Web
```

---

## Diagram 2: Actual Implementation (YOLO + Gemini + Safety)

**Key Innovations:**
*   **Hybrid Vision**: YOLO (Where?) + Gemini (What?).
*   **Shared Singleton**: Single `VisionTool` instance passed to all agents.
*   **Safety-First Fitness**: Dynamic prompts + 3-Layer RAG Safety Filter.
*   **Context-Aware**: Coordinator uses Gemini Function Calling & User Profile (Health Conditions).

```mermaid
graph LR
    User([User]) -->|"Image/Text"| DiscordBot
    
    subgraph "Optimized Core"
        DiscordBot -->|"Shared Instance"| VisionSingleton["Singleton VisionTool\nYOLOv8n + Gemini Client"]
        DiscordBot -->|Context| UserProfile["User Profile\n(Conditions + Goals)"]
        
        DiscordBot --> Coordinator["Coordinator Agent\n(Gemini Function Calling)"]
    end

    Coordinator -->|"Route Request"| NutritionAgent
    Coordinator -->|"Route Request"| FitnessAgent

    subgraph "Hybrid Vision Pipeline"
        NutritionAgent -.->|"Use Shared"| VisionSingleton
        VisionSingleton -->|"1. Detect (100ms)"| YOLO["YOLOv8n\n(Boundaries/Count)"]
        VisionSingleton -->|"2. Analyze (2s)"| Gemini["Gemini 2.5 Flash\n(Dish Name/Ingredients)"]
        Gemini -->|"3. Verify"| RAG_Nut[RAG: Nutrition DB]
    end

    subgraph "Safety-First Fitness Pipeline"
        FitnessAgent -->|"1. Get Status"| CalorieCalc["Calorie Status\n(Surplus/Deficit)"]
        FitnessAgent -->|"2. Get Restrictions"| Conditions["Health Conditions\n(Knee/Heart/etc)"]
        
        Conditions -->|Filter| RAG_Safe["Enhanced RAG\n(Safety Protocols)"]
        RAG_Safe -->|"Safe Exercises Only"| DynamicPrompt
        CalorieCalc -->|"Adjust Intensity"| DynamicPrompt
        
        DynamicPrompt["Dynamic Prompt"] -->|Generate| SafeRecs["Personalized\nSafe Advice"]
    end

    RAG_Nut --> Response
    SafeRecs --> Response
    Response --> DiscordBot
```
