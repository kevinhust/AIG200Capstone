from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from health_butler.agents.fitness.fitness_agent import FitnessAgent
from health_butler.agents.nutrition.nutrition_agent import NutritionAgent
from health_butler.coordinator.coordinator_agent import CoordinatorAgent
from health_butler.data.user_profiles import UserProfile


@dataclass(frozen=True)
class Delegation:
    agent: str  # "nutrition" | "fitness"
    task: str


def _looks_like_meal_task(text: str) -> bool:
    t = (text or "").lower()
    return any(
        w in t
        for w in (
            "eat",
            "ate",
            "meal",
            "breakfast",
            "lunch",
            "dinner",
            "calorie",
            "calories",
            "macro",
            "macros",
            "nutrition",
            "protein",
            "carbs",
            "fat",
            "burger",
            "pizza",
            "salad",
        )
    )


def _looks_like_fitness_task(text: str) -> bool:
    t = (text or "").lower()
    return any(
        w in t
        for w in (
            "fitness",
            "workout",
            "exercise",
            "run",
            "walk",
            "gym",
            "train",
            "cardio",
            "strength",
            "hiit",
            "stretch",
            "burn",
            "offset",
            "steps",
        )
    )


def build_delegations(
    coordinator: CoordinatorAgent,
    user_text: str,
    *,
    has_image: bool,
) -> List[Delegation]:
    """
    Decide which agents to call.

    We keep this deterministic for Discord demos:
    - image => nutrition
    - meal-ish + (fitness-ish or "what should I do"/"what now") => nutrition then fitness
    - otherwise fall back to CoordinatorAgent._simple_delegate
    """
    text = (user_text or "").strip()

    if has_image:
        delegations: List[Delegation] = [Delegation(agent="nutrition", task=text)]
        if _looks_like_fitness_task(text) or re.search(r"\bwhat should i do\b|\bwhat now\b", text.lower()):
            delegations.append(Delegation(agent="fitness", task="Suggest exercises to balance this meal."))
        return delegations

    mealish = _looks_like_meal_task(text)
    fitnessish = _looks_like_fitness_task(text)
    if mealish and (fitnessish or re.search(r"\bwhat should i do\b|\bwhat now\b", text.lower())):
        return [
            Delegation(agent="nutrition", task=text),
            Delegation(agent="fitness", task="Suggest exercises to balance this meal."),
        ]

    # Use coordinator's keyword routing (no LLM call)
    raw = coordinator._simple_delegate(text)
    return [Delegation(agent=d["agent"], task=d["task"]) for d in raw]


def run_delegations(
    *,
    nutrition_agent: NutritionAgent,
    fitness_agent: FitnessAgent,
    delegations: Sequence[Delegation],
    user_profile: Optional[UserProfile],
    image_path: Optional[Path],
) -> Tuple[str, Dict[str, str]]:
    """
    Execute delegations and return:
    - final combined response string
    - a dict of per-agent raw responses
    """
    responses: Dict[str, str] = {}
    nutrition_response: Optional[str] = None

    for delegation in delegations:
        if delegation.agent == "nutrition":
            ctx: List[Dict] = []
            if image_path:
                ctx.append({"type": "image_path", "content": str(image_path)})
            nutrition_response = nutrition_agent.execute(delegation.task, context=ctx)
            responses["nutrition"] = nutrition_response
            continue

        if delegation.agent == "fitness":
            # Require onboarding for fitness personalization
            if user_profile is None:
                responses["fitness"] = (
                    "I can help with fitness advice, but you need to onboard first.\n"
                    "Run `/onboard` to set up your profile (age/weight/limitations/equipment)."
                )
                continue

            ctx2: List[Dict] = [{"type": "user_profile", "content": user_profile.to_dict()}]
            if nutrition_response:
                # Explicit nutrition -> fitness handoff (critical for your demo)
                ctx2.append(
                    {
                        "from": "nutrition",
                        "type": "nutrition_summary",
                        "content": nutrition_response,
                    }
                )
            fitness_response = fitness_agent.execute(delegation.task, context=ctx2)
            responses["fitness"] = fitness_response
            continue

        responses[delegation.agent] = f"Unknown agent: {delegation.agent}"

    # Combine output
    parts: List[str] = []
    if "nutrition" in responses:
        parts.append("**Nutrition**\n" + responses["nutrition"])
    if "fitness" in responses:
        parts.append("**Fitness**\n" + responses["fitness"])
    if not parts:
        parts.append("No response generated.")

    return "\n\n".join(parts), responses

