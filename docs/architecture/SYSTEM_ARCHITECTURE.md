# Health Butler — System Architecture

> **Version**: 1.0.0
> **Last Updated**: 2026-03-25
> **Status**: **PRODUCTION** — Discord Bot + Cloud Run Deployment
> **Codename**: *Antigravity Health Swarm*

---

## 1. 系统概览

Health Butler 是一个基于 Discord 的 AI 健康助手系统，通过多 Agent 协作（Nutrition、Fitness、RepCount）为用户提供营养分析和健身建议。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Health Butler Architecture                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │  Discord     │────▶│  Health      │────▶│  Multi-Agent│             │
│  │  Gateway     │     │  Swarm       │     │  Swarm      │             │
│  │              │     │  (Router)    │     │             │             │
│  │ - Commands   │     │              │     │ - Fitness   │             │
│  │ - Messages   │     │ - Intent     │     │ - Nutrition │             │
│  │ - Buttons    │     │   Parsing    │     │ - RepCount  │             │
│  │ - Modals     │     │ - Handoff    │     │ - Analytics │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│                              │                      │                    │
│                              ▼                      ▼                    │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │  Supabase    │◀───▶│  Simple RAG  │     │  External    │             │
│  │  (Profile +  │     │  (Exercise   │     │  APIs        │             │
│  │   Workout)   │     │   DB)         │     │              │             │
│  └──────────────┘     └──────────────┘     │ - Gemini     │             │
│                                              │ - OpenAI     │             │
│                                              │ - WGER       │             │
│                                              │ - USDA       │             │
│                                              └──────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心能力

| Domain | Core Capability | Implementation |
| :--- | :--- | :--- |
| **Nutrition** | 餐食图片分析 + 卡路里计算 | Gemini Vision API + RAG |
| **Fitness** | 个性化运动建议 + 安全过滤 | FitnessAgent + SimpleRAG |
| **RepCount** | 视频动作计数 | CV + Agent 协作 |
| **Analytics** | 健康数据统计 | Supabase 查询 |
| **Multi-Agent** | Agent 间协作 | CoordinatorAgent + Health Memo Protocol |

---

## 2. 核心组件

### 2.1 Discord Gateway

**文件**: `src/discord_bot/bot.py`

Discord bot 主入口，处理消息、命令、按钮交互。

```python
class HealthButlerDiscordBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(intents=intents, heartbeat_timeout=120)
```

| 功能 | 实现 |
|------|------|
| 消息处理 | `on_message()` - 解析意图、分发到 Agent |
| 按钮交互 | `LogWorkoutView`, `MealLogView` 等 View 类 |
| 定时任务 | Morning Check-in, Daily Summary |
| 嵌入卡片 | `HealthButlerEmbed` 构建丰富 UI |

### 2.2 Health Swarm (Router)

**文件**: `src/swarm.py`

统一的多 Agent 接口，支持协作和主动交接。

```python
class HealthSwarm:
    def __init__(self, verbose: bool = True):
        self.router = RouterAgent()
        self.rag = SimpleRagTool()

    async def execute_async(self, user_input, image_path, user_context):
        # 1. Check explicit handoff signals
        # 2. Collaborative delegation via RouterAgent
        # 3. Synthesis multi-agent results
```

### 2.3 Coordinator Agent

**文件**: `src/coordinator/coordinator_agent.py`

扩展 RouterAgent，注入 Health Memo Protocol。

```python
def _build_fitness_task_with_memo(base_task, memo, language):
    # 将营养分析结果（visual_warnings, health_score）注入健身任务
    # 支持 EN/CN 双语
```

---

## 3. Agent 详解

### 3.1 Fitness Agent

**文件**: `src/agents/fitness/fitness_agent.py`

| 能力 | 描述 |
|------|------|
| 用户画像 | 从 Supabase 加载 profile（年龄、体重、身高、健康状况） |
| BMI/BMR 计算 | 基础代谢率和体质指数 |
| 安全过滤 | 根据健康状况过滤禁忌运动 |
| Health Memo | 根据近期饮食动态调整运动强度 |
| 卡路里预算 | 实时显示今日摄入/消耗进度 |
| 运动图片 | 从 WGER API 获取动作示范图 |
| 交互记录 | `LogWorkoutView` 记录运动到数据库 |

### 3.2 Nutrition Agent

**文件**: `src/agents/nutrition/nutrition_agent.py`

| 能力 | 描述 |
|------|------|
| 图片分析 | Gemini Vision 识别食物 |
| 卡路里计算 | USDA 数据 + RAG |
| 营养素分解 | 蛋白质、碳水、脂肪、纤维 |
| 健康评分 | 基于视觉风险的 1-10 分 |
| 恢复餐建议 | 运动后营养补充 |

### 3.3 RepCount Agent

**文件**: `src/agents/repcount/repcount_agent.py`

| 能力 | 描述 |
|------|------|
| 动作计数 | CV 识别视频中的运动次数 |
| 动作验证 | 姿势正确性检查 |
| 反馈建议 | 动作改进建议 |

### 3.4 Router Agent

**文件**: `src/agents/router_agent.py`

基于关键词分析用户意图，分发到合适的 Agent。

```python
fitness_keywords = (
    "workout", "exercise", "fitness", "gym", "run", "walk", "steps",
    "cardio", "strength", "stretch", "yoga", "bmi", "weight loss"
)
```

---

## 4. 数据层

### 4.1 Supabase 数据库

**表结构**:

| Table | 用途 |
|-------|------|
| `profiles` | 用户基本信息（年龄、身高、体重、目标） |
| `daily_logs` | 每日饮食和运动记录 |
| `meals` | 餐食记录（图片、卡路里、营养素） |
| `workouts` | 运动记录（类型、时长、消耗） |
| `user_goals` | 用户目标设置 |

**文件**: `src/discord_bot/profile_db.py`

### 4.2 Simple RAG

**文件**: `src/data_rag/simple_rag_tool.py`

基于 JSON 文件的运动知识库，支持健康状况过滤。

```python
class SimpleRagTool:
    def get_safe_recommendations(self, task, health_conditions, dynamic_risks):
        # 从 JSON 加载运动数据
        # 根据健康状况过滤
        # 根据 visual_warnings 调整强度
```

---

## 5. 外部 API

### 5.1 模型 API

| Provider | 用途 | 配置 |
|----------|------|------|
| **Google Gemini** | 主力模型（Fitness、Nutrition） | `GOOGLE_API_KEY` |
| **OpenAI兼容** | 备选模型 | `OPENAI_BASE_URL`, `OPENAI_API_KEY` |
| **xAI Grok** | 研究任务 | `XAI_API_KEY` |

### 5.2 数据 API

| API | 用途 | 配置文件 |
|-----|------|----------|
| **WGER** | 运动动作图片 | `WGER_API_BASE_URL` |
| **USDA** | 食物营养数据 | `USDA_API_KEY` |

### 5.3 部署

| 服务 | 平台 | 方式 |
|------|------|------|
| Discord Bot | GCP Cloud Run | Docker + GitHub Actions |
| Supabase | Supabase Cloud | 托管服务 |

---

## 6. 意图解析

**文件**: `src/discord_bot/intent_parser.py`

```python
def is_nutrition_intent(text: str) -> bool:
    nutrition_keywords = ("meal", "food", "eat", "breakfast", "lunch", "dinner", ...)
    return any(k in text_lower for k in nutrition_keywords)

def is_fitness_intent(text: str) -> bool:
    fitness_keywords = ("workout", "exercise", "fitness", "gym", "run", ...)
    return any(k in text_lower for k in fitness_keywords)
```

---

## 7. UI 组件

### 7.1 Embed Builder

**文件**: `src/discord_bot/embed_builder.py`

| 方法 | 用途 |
|------|------|
| `build_fitness_card()` | 健身建议卡片（含进度条） |
| `build_nutrition_card()` | 营养分析卡片 |
| `build_summary_card()` | 每日总结卡片 |
| `build_onboarding_card()` | 新用户引导卡片 |

### 7.2 Interactive Views

**文件**: `src/discord_bot/views.py`

| View | 功能 |
|------|------|
| `LogWorkoutView` | 记录运动（💪 Log Workout 按钮） |
| `MealLogView` | 记录餐食 |
| `OnboardingView` | 新用户引导流程 |
| `RouletteView` | 随机推荐 |

---

## 8. 文件结构

```
AIG200Capstone/
├── src/
│   ├── agents/
│   │   ├── base_agent.py           # LLM 调用基类
│   │   ├── router_agent.py         # 意图路由
│   │   ├── fitness/
│   │   │   └── fitness_agent.py    # 健身 Agent
│   │   ├── nutrition/
│   │   │   └── nutrition_agent.py  # 营养 Agent
│   │   ├── repcount/
│   │   │   └── repcount_agent.py   # 动作计数 Agent
│   │   └── analytics/
│   │       └── analytics_agent.py  # 数据分析 Agent
│   ├── coordinator/
│   │   └── coordinator_agent.py    # 协调 Agent (Health Memo)
│   ├── data_rag/
│   │   ├── simple_rag_tool.py      # 运动知识库 RAG
│   │   └── api_client.py           # WGER/USDA 客户端
│   ├── cv_food_rec/
│   │   ├── gemini_vision_engine.py # Gemini Vision
│   │   └── vision_tool.py          # 视觉工具
│   ├── discord_bot/
│   │   ├── bot.py                  # Discord 主入口
│   │   ├── views.py                # 交互组件
│   │   ├── embed_builder.py        # 嵌入卡片
│   │   ├── intent_parser.py        # 意图解析
│   │   ├── profile_db.py           # Supabase 交互
│   │   └── commands.py            # Slash Commands
│   ├── swarm.py                    # Health Swarm 接口
│   └── config.py                  # 配置管理
├── docs/
│   ├── architecture/              # 架构文档
│   ├── product/                   # 产品文档
│   └── management/                # 项目管理
├── scripts/
│   ├── apply_supabase_schema.py   # 数据库初始化
│   └── update_exercise_cache.py   # 运动数据更新
├── tests/                         # 测试套件
├── Dockerfile                     # Docker 构建
├── requirements_deploy.txt        # 部署依赖
└── .github/workflows/
    └── deploy-bot.yml             # GitHub Actions CI/CD
```

---

## 9. 部署架构

### 9.1 Cloud Run 部署

```
GitHub Push (manual trigger)
        │
        ▼
┌───────────────────┐
│ GitHub Actions    │
│ - QA (ruff, test) │
│ - Build Docker    │
│ - Push to AR      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ GCP Artifact      │
│ Registry          │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ GCP Cloud Run     │
│ - Discord Bot     │
│ - Health Swarm    │
│ - Supabase Client │
└───────────────────┘
```

### 9.2 环境变量

| Variable | 用途 |
|----------|------|
| `DISCORD_BOT_TOKEN` | Discord API Token |
| `DISCORD_ALLOWED_USER_IDS` | 白名单用户 |
| `GOOGLE_API_KEY` | Gemini API |
| `SUPABASE_URL` | Supabase 项目 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase 服务密钥 |
| `USDA_API_KEY` | USDA 食物数据 API |

---

## 10. 核心流程

### 10.1 消息处理流程

```
User Message
     │
     ▼
Intent Parser (is_nutrition / is_fitness)
     │
     ├──▶ Nutrition Intent ──▶ Nutrition Agent ──▶ Gemini Vision ──▶ Embed
     │
     └──▶ Fitness Intent ──▶ Fitness Agent ──▶ SimpleRAG + Profile ──▶ Embed
                                       │
                                       ▼
                                  Supabase (Log)
```

### 10.2 Health Memo 交接

```
Nutrition Agent
     │
     ▼
HealthMemo {
  visual_warnings: ["fried", "high_sugar"],
  health_score: 6,
  dish_name: "Fried Rice",
  calorie_intake: 650
}
     │
     ▼
CoordinatorAgent._build_fitness_task_with_memo()
     │
     ▼
Fitness Agent (with context)
     │
     ▼
降低运动强度 + BR-001 免责声明
```

---

## 11. 版本历史

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-25 | 初版架构文档 |

---

*Health Butler v1.0: Discord AI Health Assistant with Multi-Agent Swarm.*
*Generated 2026-03-25 — Chief AI Architect*