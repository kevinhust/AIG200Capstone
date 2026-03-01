"""
Coordinator Agent for Health Butler AI system.

Routes user requests to appropriate specialist agents (Nutrition/Fitness)
based on keyword analysis and health context. Extends RouterAgent
with health-specific delegation logic.

Module 3: Health Memo Protocol
- Extracts visual_warnings and health_score from nutrition results
- Injects contextual safety guidance into fitness agent tasks
- Supports multilingual intent detection (EN/CN)
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, TypedDict
from src.agents.router_agent import RouterAgent
from src.config import settings
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)


class HealthMemo(TypedDict):
    """Structured health context passed between agents."""
    visual_warnings: List[str]  # e.g., ["fried", "high_oil", "high_sugar"]
    health_score: int  # 1-10 scale
    dish_name: str
    calorie_intake: float


def _build_fitness_task_with_memo(base_task: str, memo: Optional[HealthMemo], language: str = "en") -> str:
    """
    Inject health memo context into fitness task description.

    Args:
        base_task: The original fitness task
        memo: Health context from nutrition analysis
        language: "en" for English, "cn" for Chinese
    """
    if not memo:
        return base_task

    warnings = memo.get("visual_warnings", [])
    score = memo.get("health_score", 10)
    dish = memo.get("dish_name", "meal")
    calories = memo.get("calorie_intake", 0)

    if not warnings:
        return base_task

    # Build warning description based on language
    if language == "cn":
        warning_desc = []
        if "fried" in warnings:
            warning_desc.append("油炸食物 (deep-fried)")
        if "high_oil" in warnings:
            warning_desc.append("高油 (high oil content)")
        if "high_sugar" in warnings:
            warning_desc.append("高糖 (high sugar)")
        if "processed" in warnings:
            warning_desc.append("加工食品 (processed)")

        warning_str = "、".join(warning_desc) if warning_desc else "普通饮食"

        injected_context = f"""[健康备忘录 / Health Memo]
用户刚刚摄入了: {dish}
热量: ~{calories:.0f} kcal
风险标签: {warning_str}
健康评分: {score}/10

考虑到用户刚刚摄入了{warning_str}食物，请提供针对性的安全运动建议：
1. 评估当前是否适合高强度运动
2. 建议合适的运动时机（如饭后30分钟再运动）
3. 推荐适合的运动类型和强度
4. 如有需要，提醒补充水分

原始任务: {base_task}"""
    else:
        # English mode
        warning_desc = []
        if "fried" in warnings:
            warning_desc.append("deep-fried")
        if "high_oil" in warnings:
            warning_desc.append("high-fat")
        if "high_sugar" in warnings:
            warning_desc.append("high-sugar")
        if "processed" in warnings:
            warning_desc.append("processed")

        warning_str = ", ".join(warning_desc) if warning_desc else "regular diet"

        injected_context = f"""[Health Memo - Nutrition Context]
The user has just consumed: {dish}
Calories: ~{calories:.0f} kcal
Health warnings: {warning_str}
Health score: {score}/10

The user has just consumed {warning_str} food (Warnings: {', '.join(warnings)}).
Please provide exercise recommendations with appropriate intensity adjustments and safety precautions:
1. Assess whether high-intensity exercise is appropriate at this time
2. Suggest optimal timing for exercise (e.g., wait 30-60 minutes after eating)
3. Recommend suitable exercise types and intensity levels
4. Include hydration reminders if needed

Original task: {base_task}"""

    return injected_context

_PROFILE_QUERY_PATTERNS = [
    r"\bwho\s*am\s*i\b",
    r"\bwhoami\b",
    r"\bmy\s+profile\b",
    r"\bshow\s+(me\s+)?(my\s+)?profile\b",
    r"\b(profile|stats|metrics)\b\s*\??$",
    r"\bwhat('?s| is)\s+my\s+(name|age|height|weight|goal|diet|conditions|activity|preferences)\b",
    r"\bmy\s+(name|age|height|weight|goal|goals|diet|conditions|activity|preferences)\b\s*\??$",
    r"\b(daily\s+)?calorie\s+target\b",
    r"\btarget\s+calories\b",
    r"\bdaily\s+target\b",
]


def _matches_any_pattern(text_lower: str, patterns: List[str]) -> bool:
    return any(re.search(p, text_lower) for p in patterns)


class CoordinatorAgent(RouterAgent):
    """
    Health-specific Router Agent with enhanced context management.

    Responsibilities:
    - Route requests to Nutrition or Fitness agents
    - Load and pass user profiles to agents
    - Chain Nutrition output to Fitness input (meal → exercise advice)
    - Maintain conversation context for goal tracking
    - Module 3: Health Memo Protocol for cross-agent safety context
    """

    def __init__(self):
        system_prompt = """You are the Coordinator Agent for the Personal Health Butler AI.
Your ONLY job is to analyze the user's message and decide which specialist agent(s) should handle it.

## 多语言支持 / Multilingual Support
You MUST understand BOTH English and Chinese (中文) messages.
- "我吃了炸鸡" = "I ate fried chicken" → nutrition
- "想去运动" = "want to exercise" → fitness
- "我刚吃了炸鸡，想去游泳" = "I just ate fried chicken, want to go swimming" → BOTH nutrition + fitness

## Available Specialist Agents

### nutrition (营养)
Handles: Food analysis, calorie counting, meal logging, dietary advice, macro tracking.
处理: 食物分析、卡路里计算、饮食记录、营养建议
Route here when: User mentions food, eating, meals, calories, macros, recipes, ingredients, diet plans, nutritional info, or uploads a food image.
Keywords: 食物、吃、饭、卡路里、营养、热量、膳食
Example queries: "I ate a burger", "我吃了汉堡", "How many calories in rice?", "Analyze this meal", "I just ate a donut"

### fitness (健身)
Handles: Exercise recommendations, workout plans, activity tracking, step counting, weight goals, body measurements, physical health metrics.
处理: 运动建议、健身计划、活动追踪、体重目标
Route here when: User asks about exercise, workouts, weight loss/gain goals, BMI, body stats, height, weight, steps, running, gym, yoga, stretching, or any physical activity.
Keywords: 运动、健身、跑步、游泳、锻炼、减肥、增肌
Example queries: "Suggest an exercise", "想去游泳", "What workout should I do?", "我想减肥", "can I go for a run?"

### profile/identity (route to fitness)
Handles: Requests about the user's own onboarding/profile details.
Example queries: "Who am I?", "我是谁", "Show my profile", "我的资料"

## Routing Rules
1. If the message is about FOOD or EATING → route to "nutrition"
2. If the message is about EXERCISE, BODY STATS, or FITNESS → route to "fitness"
3. If the message mentions EATING + wants exercise advice → route to BOTH: first "nutrition", then "fitness"
   Examples: "I ate pizza and want to exercise", "我吃了炸鸡想去运动", "刚吃完饭去跑步"
   "I just ate a donut, can I go for a run?" → BOTH nutrition + fitness
   "I had fried chicken, is it okay to swim now?" → BOTH nutrition + fitness
4. If the message is about the USER'S PROFILE / IDENTITY → route to "fitness"
5. If the message is a general health question → route to the MOST relevant agent
6. If truly ambiguous → route to "nutrition" (the app's primary focus)

## Complex English Patterns to Recognize
- "I just ate X, can I Y?" → BOTH nutrition + fitness
- "I had X, is it okay to exercise?" → BOTH nutrition + fitness
- "After eating X, should I workout?" → BOTH nutrition + fitness
- "Can I run/jog/swim/lift after having X?" → BOTH nutrition + fitness

## IMPORTANT
- Detect Chinese (中文) text and process it correctly
- "我吃了X，想去运动" patterns should ALWAYS trigger BOTH agents
- Questions about body measurements (height, weight, BMI) → fitness
- Questions about food, meals, diet → nutrition

You MUST respond with a valid JSON planning object.
"""
        # Initialize BaseAgent directly to override Router's role
        super(CoordinatorAgent, self).__init__(role="coordinator", system_prompt=system_prompt, use_openai_api=False)

    async def route_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Alias for analyze_and_delegate to maintain compatibility with legacy callers.
        """
        return await self.analyze_and_delegate(query)

    async def analyze_and_delegate(self, user_task: str) -> List[Dict[str, Any]]:
        """
        Analyze task using Gemini Structured Output for 100% reliable JSON.
        """
        task_lower = (user_task or "").strip().lower()
        if task_lower and _matches_any_pattern(task_lower, _PROFILE_QUERY_PATTERNS):
            # Avoid routing profile/identity queries to nutrition.
            return [
                {
                    "agent": "fitness",
                    "task": "Show the user's saved profile details and current goals/preferences.",
                }
            ]

        if not self.client:
            logger.warning("Coordinator client is None, using keyword fallback")
            return self._simple_delegate(user_task)

        prompt = f"""Analyze the following user message and decide which agent(s) should handle it.

USER MESSAGE: "{user_task}"

Decide: should this go to "nutrition", "fitness", or both?
Return a JSON object with a "delegations" array."""

        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=settings.GEMINI_MODEL_NAME,
                contents=self.system_prompt + "\n\n" + prompt,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "delegations": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "agent": {"type": "STRING"},
                                        "task": {"type": "STRING"}
                                    },
                                    "required": ["agent", "task"]
                                }
                            }
                        },
                        "required": ["delegations"]
                    }
                )
            )
            
            data = response.parsed
            if isinstance(data, dict) and "delegations" in data:
                # Validate agent names — only allow known agents
                valid_delegations = []
                for d in data["delegations"]:
                    agent = d.get("agent", "").lower().strip()
                    if agent in ("nutrition", "fitness"):
                        valid_delegations.append({"agent": agent, "task": d.get("task", user_task)})
                
                if valid_delegations:
                    return valid_delegations
            
            return self._simple_delegate(user_task)
            
        except Exception as e:
            logger.error(f"CoordinatorAgent delegation failed: {e}")
            return self._simple_delegate(user_task)

    def _simple_delegate(self, task: str) -> List[Dict[str, Any]]:
        """
        Enhanced health-specific fallback delegation with chaining support.
        Uses comprehensive keyword matching when LLM routing is unavailable.
        Module 3: Added Chinese (中文) keyword support.
        """
        task_lower = task.lower()
        delegations = []

        # ── Profile / identity queries should not go to nutrition ──
        if task_lower and _matches_any_pattern(task_lower, _PROFILE_QUERY_PATTERNS):
            delegations.append({"agent": "fitness", "task": task})
            return delegations

        # ── Fitness-first keywords (body stats, exercise, goals) ──
        fitness_keywords = [
            # Exercise & workout (EN)
            'exercise', 'workout', 'work out', 'gym', 'fitness', 'training',
            'stretch', 'yoga', 'cardio', 'hiit', 'plank', 'squat', 'pushup',
            'push-up', 'pull-up', 'pullup', 'deadlift', 'bench press',
            # Activity tracking (EN)
            'walk', 'run', 'jog', 'swim', 'bike', 'cycling', 'steps',
            'activity', 'active', 'sedentary',
            # Body stats & measurement (EN)
            'tall', 'height', 'weight', 'bmi', 'body', 'muscle', 'fat percentage',
            # Goals (EN)
            'goal', 'progress', 'track', 'lose weight', 'gain muscle',
            'weight loss', 'weight gain', 'bulk', 'cut',
            # Recommendations (EN)
            'suggest exercise', 'recommend exercise', 'what exercise',
            'what workout', 'how to burn',
            # Completion tracking (EN)
            'completed', 'finished', 'done with',
            # === CHINESE KEYWORDS ===
            # Exercise & workout (CN)
            '运动', '健身', '锻炼', '跑步', '游泳', '骑车', '瑜伽', '举重',
            '游泳', '跑步', '走路', '散步', '爬山', '打球',
            # Body stats (CN)
            '身高', '体重', ' bmi ', '肌肉', '减脂',
            # Goals (CN)
            '减肥', '增肌', '瘦身', '塑形', '减重', '增重',
            # Activity verbs (CN)
            '想去', '要做', '打算', '准备去',
        ]

        # ── Nutrition-first keywords (food, meals, calories) ──
        nutrition_keywords = [
            # Food & eating (EN)
            'food', 'eat', 'ate', 'eating', 'eaten',
            'calorie', 'calories', 'kcal',
            'meal', 'meals', 'dish',
            'nutrition', 'nutrient', 'nutritional',
            'diet', 'dietary',
            # Meals of the day (EN)
            'lunch', 'dinner', 'breakfast', 'brunch', 'snack', 'supper',
            # Food items (EN)
            'recipe', 'ingredient', 'cook', 'cooking',
            'protein', 'carb', 'carbs', 'fat', 'fiber', 'sugar', 'sodium',
            # Macro tracking (EN)
            'macro', 'macros', 'intake', 'portion',
            # Analysis (EN)
            'analyze this meal', 'what did i eat', 'how many calories',
            # === CHINESE KEYWORDS ===
            # Food & eating (CN)
            '吃', '食物', '饭', '餐', '菜', '肉', '蔬菜', '水果',
            '热量', '卡路里', '营养', '膳食', '饮食',
            # Meals of the day (CN)
            '早餐', '午餐', '晚餐', '宵夜', '加餐', '点心',
            # Common foods (CN)
            '炸鸡', '汉堡', '披萨', '面条', '米饭', '饺子', '包子',
            '沙拉', '牛排', '寿司', '火锅', '烧烤',
            # Eating verbs (CN)
            '刚吃', '吃了', '吃完', '正在吃',
        ]

        has_fitness = any(word in task_lower for word in fitness_keywords)
        has_nutrition = any(word in task_lower for word in nutrition_keywords)

        # ── Both detected: check for chaining (ate → exercise) ──
        if has_nutrition and has_fitness:
            delegations.append({'agent': 'nutrition', 'task': task})
            delegations.append({'agent': 'fitness', 'task': 'Based on the previous nutrition analysis, suggest appropriate exercises.'})
            return delegations

        # ── Meal + "ate" pattern (EN/CN) → chain both ──
        ate_patterns = ['ate', 'just ate', 'i ate', '刚吃', '吃了', '吃完']
        if has_nutrition and any(p in task_lower for p in ate_patterns):
            delegations.append({'agent': 'nutrition', 'task': task})
            delegations.append({'agent': 'fitness', 'task': 'Suggest exercises to balance this meal intake'})
            return delegations

        # ── Fitness only ──
        if has_fitness:
            delegations.append({'agent': 'fitness', 'task': task})
            return delegations

        # ── Nutrition only ──
        if has_nutrition:
            delegations.append({'agent': 'nutrition', 'task': task})
            return delegations

        # ── Default to nutrition if truly ambiguous ──
        delegations.append({'agent': 'nutrition', 'task': task})
        return delegations
    
    def supports_chaining(self) -> bool:
        """Indicate that this coordinator supports agent chaining."""
        return True

    def extract_health_memo(self, nutrition_result: Dict[str, Any]) -> Optional[HealthMemo]:
        """
        Extract health context from nutrition agent result.

        Module 3: Health Memo Protocol
        Parses nutrition analysis to build structured context for fitness agent.
        """
        if not nutrition_result:
            return None

        try:
            # Handle string JSON
            if isinstance(nutrition_result, str):
                nutrition_result = json.loads(nutrition_result)

            visual_warnings = nutrition_result.get("visual_warnings", [])
            health_score = nutrition_result.get("health_score", 10)
            dish_name = nutrition_result.get("dish_name", "meal")

            # Extract calories
            total_macros = nutrition_result.get("total_macros", {})
            calorie_intake = float(total_macros.get("calories", 0) or 0)

            # Only return memo if there are actual warnings
            if visual_warnings or health_score < 7:
                memo: HealthMemo = {
                    "visual_warnings": visual_warnings,
                    "health_score": health_score,
                    "dish_name": dish_name,
                    "calorie_intake": calorie_intake,
                }
                logger.info(f"[HealthMemo] Extracted: {memo}")
                return memo

        except Exception as e:
            logger.warning(f"[HealthMemo] Extraction failed: {e}")

        return None

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect if text is primarily Chinese or English."""
        # Count Chinese characters
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # If any Chinese characters present, treat as Chinese for mixed content
        if chinese_chars > 0:
            return "cn"
        return "en"

    def build_fitness_task_with_context(
        self,
        base_task: str,
        nutrition_result: Dict[str, Any],
        user_input: str = ""
    ) -> str:
        """
        Build fitness task with injected health memo context.

        Module 3: Dynamic task injection based on nutrition analysis.

        Args:
            base_task: The original fitness task
            nutrition_result: Result from nutrition agent
            user_input: Original user input for language detection
        """
        memo = self.extract_health_memo(nutrition_result)

        if not memo:
            return base_task

        # Detect language from user input
        language = self._detect_language(user_input) if user_input else "en"
        enhanced_task = _build_fitness_task_with_memo(base_task, memo, language)

        logger.info(f"[HealthMemo] Task enhanced with nutrition context (language={language})")

        return enhanced_task
