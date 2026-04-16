# 🛡️ Personal Health Butler AI v8.5 (Stage Ready Edition)

<div align="center">
  <img src="https://img.shields.io/badge/Version-8.5-blue.svg" alt="Version 8.5" />
  <img src="https://img.shields.io/badge/AI_Engine-Gemini_2.5_Flash-orange.svg" alt="AI Engine" />
  <img src="https://img.shields.io/badge/Vision-YOLO11-success.svg" alt="Vision" />
  <img src="https://img.shields.io/badge/Database-Supabase_v6.0-green.svg" alt="Supabase" />
</div>

> Your intelligent, proactive, and privacy-first digital health companion. Developed for Capstone 2026.

---

## 🌟 The v8.5 Architecture (Decoupled & Agentic)

Personal Health Butler v8.5 introduces a **Modular Decoupled Architecture**, transitioning from a monolithic Bot object to a specialized multi-agent swarm.

| Component | Core Technologies | Key Capabilities |
| :--- | :--- | :--- |
| **👁️ Perception** | **YOLO11 + Gemini 2.5 Flash** | Real-time food localization + semantic analysis. Latency < 5s. |
| **🧠 Intelligence** | **HealthSwarm Protocol** | 6-agent coordination: Nutrition, Fitness, Engagement, Analytics, RepCount, Coordinator. |
| **🛡️ Safety** | **BR-001 Safety Shield** | Dynamic RAG-based exercise filtering. Blocks intense workouts post-heavy-meals. |
| **🔒 Privacy** | **Sensitive Intent Rerouting** | Automated PII protection. Redirects trends/summaries from public channels to DMs. |
| **💾 Persistence** | **Supabase + RLS** | Secure, per-user health history, metabolic profiling, and achievement tracking. |

---

## 🛠️ User Commands & Interactions

The bot supports Slash commands (`/`), Natural Language triggers, and Interactive UI Views.

### 🎮 Command Registry

| Command | Category | Description |
| :--- | :--- | :--- |
| `/setup` | Onboarding | Initialize or update your health metrics (Height, Weight, Goals). |
| `/demo` | Quick Start | Activate demo mode with a pre-configured health persona. |
| `/reset` | Danger Zone | Wipe your persistent profile and history. |
| `/help` | Guidance | Tiered help system (Onboarding, Logging, Privacy, Support). |
| `/fitness [category]` | Fitness | Get workout recommendations (cardio, strength, yoga, hiit, etc.) |
| `/routine` | Fitness | View your saved workout routine and weekly progress. |
| `/roulette` | Gamification | Spin the 🎰 Food Roulette for budget-aware meal ideas. |
| `/trends` | Analytics | Generate a 30-day visual health report (Auto-rerouted to DM). |
| `/settings` | Preferences | Toggle proactive morning check-ins and notification intensity. |
| `/sync` | Recovery | Manual channel recovery / sync Discord private channel. |
| `/repcount [exercise]` | CV | AI rep counting from workout video using MediaPipe Pose. |
| `ping` | System | Health check — verify bot is online. |
| **Upload Food Photo** | Vision | YOLO11 + Gemini Vision analyzes meal, returns macros + health score. |

### 🧠 Intent-Based Triggers

| Pattern | Action |
| :--- | :--- |
| `hi`, `hello`, `start` | Triggers premium onboarding flow. |
| `Who am I?`, `my profile`, `whoami` | Displays current health metrics. |
| `Summary`, `stats`, `today's calories` | Real-time daily macro/calorie report (Auto-rerouted to DM). |
| `I need help`, `help`, `commands` | Triggers the segmented help embed. |
| Food photo upload | YOLO11 + Gemini Vision → macro analysis + DV% dashboard. |
| Health-related queries | Routes to appropriate agent (Nutrition/Fitness/Engagement). |

---

## 🏗️ Multi-Agent Coordination Flow

```mermaid
sequenceDiagram
    participant User
    participant Discord as Discord UI
    participant Swarm as HealthSwarm
    participant Coordinator as CoordinatorAgent
    participant Nutrition as Nutrition Agent
    participant Fitness as Fitness Agent
    participant Engagement as Engagement Agent

    User->>Discord: Uploads Meal Image
    Discord->>Swarm: Route to appropriate agent
    Swarm->>Coordinator: Health-specific routing
    Coordinator->>Nutrition: Detect & Analyze
    Nutrition-->>Nutrition: YOLO11 + Gemini Vision
    Nutrition-->>Discord: Macros + `HealthMemo`
    Discord->>User: Macro Dashboard
    Note over Coordinator: Health Memo Protocol
    Coordinator->>Fitness: Pass `HealthMemo` (Context Handoff)
    Fitness-->>Fitness: BR-001 Safety Filter
    Fitness-->>User: Safe workout recommendation
```

---

## 📂 Documentation & Engineering Logs

- **[Milestone 2 Report](docs/management/milestones/milestone2/milestone%202%20report.md)**: Evolution from v1.0 to v2.0.
- **[System Upgrade Log](system_upgrade.md)**: Detailed module-by-module engineering entries.
- **[Midterm Demo Plan](docs/management/milestones/milestone2/midterm_demo_plan.md)**: Presentation script and technical defense strategy.

---

## 🚀 Quick Start (Production Setup)

1. **Clone & Install**:
   ```bash
   git clone https://github.com/kevinhust/capstonetest.git
   pip install -r requirements.txt
   ```
2. **Configure environment variables** in `.env` (Consult `.env.template`).
3. **Launch the swarm**:
   ```bash
   PYTHONPATH=. python3 -m src.discord_bot.bot
   ```

---
*Generated by Antigravity - Version 8.5 | Architectural Excellence*
