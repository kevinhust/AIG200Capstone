# 代码恢复与修改计划

**日期**: 2026-02-11
**状态**: 待执行 - 等待用户确认

---

## 📋 执行摘要

### 当前问题
1. **代码丢失**: 通过 `git reset --hard` 操作，所有未提交的修改被覆盖
2. **容器不同步**: Docker 容器使用旧代码构建，未包含最新修改
3. **恢复失败**: 尝试从容器提取代码失败（容器中也是旧版本）
4. **好消息**: `fitness` 分支包含昨天的完整代码

---

## ✅ 已恢复的资源

### fitness 分支内容
通过 `git diff` 确认，该分支包含昨天的所有修改：

- ✅ **Enhanced Coordinator**: 使用 `google.genai` API，Function Calling 智能路由
- ✅ **Fitness Agent**: 完整的 RAG 安全过滤、动态上下文构建
- ✅ **Gemini Vision**: 增强提示词（识别完整菜名、材料重量）
- ✅ **Discord Bot v3**: `/demo` 模式、双引擎架构、隐私指导
- ✅ **Onboarding v2**: 健康状况多选 Step
- ✅ **API 安全修复**: 所有硬编码密钥改为环境变量

---

## 🔧 需要修改的模块

### 1. 📦 Coordinator Agent - P0 (关键)

**文件**: `health_butler/coordinator/coordinator_agent.py`

**当前问题**:
```python
# ❌ 当前代码（旧版本）
from antigravity_core.agents.router_agent import RouterAgent

class CoordinatorAgent(RouterAgent):
    def __init__(self):
        super(RouterAgent, self).__init__(role="coordinator", system_prompt=system_prompt)
```

**需要替换为**:
```python
# ✅ 目标代码（fitness 分支）
from typing import List, Dict, Any, Optional
import os
from google import genai
from google.genai import types

from health_butler.utils.tracing import tracer
from health_butler.utils.errors import RoutingError, ConfigurationError
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.discord_bot.profile_db import UserProfileDB

class CoordinatorAgent:
    """
    Enhanced Coordinator Agent using Gemini function calling for intelligent routing.
    """

    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ConfigurationError(
                agent_name="coordinator",
                message="GOOGLE_API_KEY environment variable not set",
                context={"required_env_vars": ["GOOGLE_API_KEY"]}
            )

        # Configure Gemini (using new google.genai package)
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model

        # Initialize Database
        self.db = UserProfileDB()

        # Initialize specialist agents
        self.nutrition_agent = NutritionAgent()
        self.fitness_agent = FitnessAgent()

        # Define available agents as function declarations
        self.agent_functions = [
            types.FunctionDeclaration(
                name="nutrition_agent",
                description="Analyze food images or descriptions to calculate calories, macros...",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "task": types.Schema(type=types.Type.STRING),
                        "has_image": types.Schema(type=types.Type.BOOLEAN),
                        "calories_consumed": types.Schema(type=types.Type.NUMBER)
                    },
                    required=["task"]
                )
            ),
            types.FunctionDeclaration(
                name="fitness_agent",
                description="Provide exercise recommendations, workout plans...",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "task": types.Schema(type=types.Type.STRING),
                        "priority": types.Schema(type=types.Type.STRING)
                    },
                    required=["task"]
                )
            )
        ]

        self.tool_config = types.Tool(function_declarations=self.agent_functions)

        logger.info("✅ Coordinator Agent initialized with Gemini function calling")

    def route_request(self, user_message: str, has_image: bool, user_context: Dict = None):
        """Use Gemini to intelligently route user request."""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=self._build_routing_prompt(user_message, has_image, user_context),
            config=types.GenerateContentConfig(
                tools=[self.tool_config],
            )
        )

        return self._parse_function_calls(response, user_message)
```

**修改说明**:
1. 删除 `antigravity_core` 依赖，改用 `google.genai`
2. 使用 `types.FunctionDeclaration` 和 `types.Schema` 替代旧的 `types.Function`
3. 添加完整的智能路由逻辑

---

### 2. 💪 Fitness Agent - P0 (核心)

**文件**: `health_butler/agents/fitness/fitness_agent.py`

**当前问题**:
```python
# ❌ 当前代码可能缺少 RAG 安全过滤和动态上下文
```

**需要添加**:
```python
from health_butler.data_rag.enhanced_rag_tool import EnhancedRagTool

class FitnessAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role="fitness",
            system_prompt="You are an expert Fitness Coach..."
        )
        self.rag = EnhancedRagTool()

    def _build_dynamic_prompt(self, user_profile: dict, calorie_context: str, restrictions: List[str]) -> str:
        """构建包含用户健康状况、热量状态、RAG 上下文的动态提示词"""
        # 完整实现见 fitness 分支

    def _get_rag_safety_context(self, user_query: str, restrictions: List[str]) -> str:
        """使用 RAG 获取安全过滤后的运动建议"""
        result = self.rag.smart_query(
            user_query=user_query,
            user_restrictions=restrictions,  # 英文映射
            top_k=5
        )

        safe_exercises = result.get('safe_exercises', [])
        safety_warnings = result.get('safety_warnings', [])

        # 格式化返回
        return f"""
**Safe Exercises (filtered for {', '.join(restrictions or ['no conditions']}):**
{chr(10).join([f"- {ex}" for ex in safe_exercises])}

**Safety Warnings:**
{chr(10).join([f"- {w}" for w in safety_warnings])}
"""
```

**修改说明**:
1. 添加 `EnhancedRagTool` 集成
2. 实现动态上下文构建（考虑热量盈余/赤字）
3. 实现安全过滤（基于健康状况排除不安全运动）
4. 返回结构化响应（运动列表 + 安全警告）

---

### 3. 🤖 Gemini Vision - P0 (核心)

**文件**: `health_butler/cv_food_rec/gemini_vision.py`

**当前问题**:
```python
# ❌ 当前代码使用旧 API
import google.generativeai as genai
from google.generativeai import types

genai.configure(api_key=api_key)
self.model = genai.GenerativeModel(model)
```

**需要替换为**:
```python
from google import genai
from google.genai import types

class GeminiVisionAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)  # 新 API
        self.model_name = model

    def analyze_food(self, image: Image.Image, context: Optional[str] = None):
        # 增强提示词
        base_prompt = """You are an expert nutritionist and chef. Analyze this food image in extreme detail.

**CRITICAL TASKS**:
1. **Identify the exact dish name**: Be specific - "Spaghetti with Broccoli" not just "Pasta"
2. **List ALL visible ingredients**: Look carefully and list every ingredient you can see
3. **Estimate portion sizes**: Give realistic weight estimates in grams

**EXAMPLE OUTPUT FORMAT**:
{
  "items": [{
    "name": "Spaghetti with Broccoli in Cream Sauce",
    "ingredients": [
      {"name": "spaghetti", "amount_g": 150},
      {"name": "broccoli florets", "amount_g": 80}
    ],
    "portion_per_unit_g": 350,
    "total_estimated_calories": 520
}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[base_prompt, image]
        )

        return {
            "items": parsed_items,
            "success": True,
            "total_estimated_calories": total_calories
        }
```

**修改说明**:
1. 迁移到 `google.genai` 新 API
2. 使用 `genai.Client()` 替代 `genai.configure()`
3. 使用 `client.models.generate_content()` 替代 `model.generate_content()`
4. 增强提示词要求完整菜名和材料重量估算

---

### 4. 🤖 Discord Bot (bot_v3.py) - P0 (大型)

**文件**: `health_butler/discord_bot/bot_v3.py`

**需要添加的功能**:

```python
# ✅ 1. /demo 命令 - 演示模式
async def handle_demo_command(self, message: discord.Message):
    """创建临时演示用户，每日自动清理"""
    demo_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.author.id}"

    # 清理该用户的旧 demo 数据
    cursor.execute("DELETE FROM user_profiles WHERE user_id LIKE ?", (f"demo_%{message.author.id}",))
    cursor.execute("DELETE FROM daily_log WHERE user_id LIKE ?", (f"demo_%{message.author.id}",))

    # 发送 onboarding
    view = StartOnboardingView(demo_id, lang)
    await message.channel.send(demo_welcome, view=view)

# ✅ 2. 健康状况传递给 Fitness Agent
async def handle_message(self, message: discord.Message):
    user_profile = self.db.get_profile(user_id)

    # 提取健康状况并传递给 fitness agent
    if user_profile and 'health_conditions' in user_profile:
        health_conditions = user_profile['health_conditions']
        # 传递给 fitness agent 的 recommend 方法
        result = await self.fitness.recommend(
            calories=calories,
            lang=lang,
            health_conditions=health_conditions
        )

# ✅ 3. 双引擎视觉架构
async def handle_image_analysis(self, message: discord.Message):
    # 1. YOLO 边界检测
    vision_results = self.vision.detect_food(temp_path, conf_threshold=0.2)

    # 2. Gemini 语义分析
    gemini_analysis = self.gemini_vision.analyze_food(img)

    # 3. 融合结果
    if gemini_analysis.get('success') and gemini_analysis.get('items'):
        items = gemini_analysis['items']
        # 使用 Gemini 的完整分析

# ✅ 4. 扩展 Fitness 路由关键词
fitness_keywords = [
    "exercise", "workout", "fitness", "gym", "training", "train",
    "cardio", "weights", "strength", "muscle", "run", "walking",
    "yoga", "stretch", "movement", "activity",
    # 中文
    "运动", "锻炼", "健身", "训练", "跑步", "瑜伽", "走路", "活动"
]
```

**修改说明**:
1. 实现 `/demo` 演示模式（创建临时用户、自动清理）
2. 修改图像处理流程使用 Gemini-first 架构
3. 传递健康状况给 Fitness Agent
4. 扩展 fallback 路由关键词

---

### 5. 🔒 Onboarding v2 (onboarding_v2.py) - P1

**文件**: `health_butler/discord_bot/onboarding_v2.py`

**需要添加**:

```python
# ✅ 隐私指导（已在本次会话中添加）
embed.add_field(
    name="🔒 Privacy Tip",
    value="**To keep your data private:**\n"
          f"1. Create a private channel: `#nutrition-{interaction.user.name}`\n"
          f"2. Set it to **private** (only you can see it)\n"
          f"3. Add me to that channel for private tracking!\n\n"
          f"_Your food records and fitness advice will only be visible in channels you control._",
    inline=False
)
```

**修改说明**:
1. 已在本次会话添加隐私指导
2. 确认其他字段（健康条件、BMI、目标等）完整

---

### 6. 🔧 其他文件

| 文件 | 状态 | 修改内容 |
|------|------|----------|
| `vision_tool.py` | ⚠️ 检查 | 确认使用 `yolov8n.pt` |
| `requirements.docker.txt` | ⚠️ 检查 | 确认依赖完整 |
| `.gitignore` | ✅ 已更新 | 添加 `.env.*` `*.env` 保护 |

---

## 📊 修改统计

| 模块 | 优先级 | 文件数 | 估计代码量 | 估计时间 |
|------|--------|--------|-------------|----------|
| Coordinator Agent | P0 | 1 | ~200 行 | 30-45 分钟 |
| Fitness Agent | P0 | 1 | ~300 行 | 45-60 分钟 |
| Gemini Vision | P0 | 1 | ~150 行 | 20-30 分钟 |
| Discord Bot v3 | P0 | 1 | ~500 行 | 60-90 分钟 |
| Onboarding v2 | P1 | 1 | ~30 行 | 10-15 分钟 |
| 其他文件 | P2 | 3 | 小修改 | 10-15 分钟 |
| **总计** | - | **7 个主要文件** | **~3-4 小时** |

---

## 🎯 执行计划

### 方案 A: 合并 fitness 分支（推荐）

```bash
# 1. 合并 fitness 分支到当前分支
git checkout main
git merge origin/fitness -m "Restore fitness branch code"

# 2. 逐个解决合并冲突（如果有）
# 3. 测试所有功能
# 4. 重新构建并启动容器
```

**优点**:
- ✅ 最快恢复所有功能
- ✅ 代码已经在 fitness 分支上测试过
- ✅ 一次性完成所有修改

**缺点**:
- ⚠️ 可能有合并冲突需要手动解决
- ⚠️ fitness 分支可能有一些与当前环境不兼容的代码

---

### 方案 B: 手动逐个实现（保守）

如果合并有冲突，按以下顺序逐个手动复制代码：

1. **Coordinator Agent** (P0) - 最关键
2. **Gemini Vision** (P0) - 核心功能
3. **Fitness Agent** (P0) - 核心功能
4. **Discord Bot v3** (P0) - 主入口
5. **Onboarding v2** (P1) - 较简单

---

## ⚠️ 重要注意事项

1. **API 密钥**: 确保 `.env` 文件包含所有必需的密钥
2. **容器重建**: 代码修改后需要 `docker-compose build && docker-compose up -d`
3. **测试顺序**: 按 P0 → P1 → P2 顺序测试
4. **备份习惯**: 每次重大修改前创建备份分支

---

**准备好执行后请告诉我，我将按照你选择的方案进行操作。**
