"""Tests for YOLO hint reconciliation + fallback in NutritionAgent.

These tests are fully mocked/stubbed: no real Gemini calls and no real YOLO weights.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import pytest
from unittest.mock import patch

from health_butler.agents.nutrition.nutrition_agent import NutritionAgent


class _StubVisionTool:
    def __init__(self, detections: List[Dict[str, Any]]):
        self._detections = detections

    def detect_food(self, _image_path: str) -> List[Dict[str, Any]]:
        return list(self._detections)


class _StubGeminiEngine:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.last_object_detections: Optional[List[Dict[str, Any]]] = None

    def analyze_food(
        self,
        _image_path: str,
        _user_context: Optional[str] = None,
        *,
        object_detections: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.last_object_detections = object_detections
        return dict(self.payload)


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"})
def test_yolo_fallback_builds_banana_items_when_gemini_is_generic() -> None:
    """YOLO detects banana x5; Gemini returns generic/empty -> agent reconstructs banana x5."""
    detections = [
        {"label": "banana", "confidence": 0.9, "bbox": [i * 10, i * 10, i * 10 + 5, i * 10 + 5]}
        for i in range(5)
    ]
    agent = NutritionAgent(vision_tool=_StubVisionTool(detections))
    agent.gemini_engine = _StubGeminiEngine(
        {
            "dish_name": "Meal",
            "items": [],
            "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
            "total_confidence": 0.2,
            "composition_analysis": "",
            "notes": "",
        }
    )

    # Provide a deterministic RAG match for banana so calorie_breakdown can compute quantity.
    agent.rag.search_food = lambda q: (
        {"name": "Banana", "calories": 89, "protein": 1.1, "carbs": 23, "fat": 0.3}
        if "banana" in (q or "").lower()
        else None
    )

    out = json.loads(agent.execute("Analyze this meal", context=[{"type": "image_path", "content": "/tmp/fake.jpg"}]))
    rows = out.get("calorie_breakdown") or []
    assert any(r.get("item", "").lower() == "banana" and int(r.get("quantity", 0)) == 5 for r in rows)


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"})
def test_yolo_reconcile_fills_missing_portion_for_existing_banana_item() -> None:
    """Gemini returns banana item without portion; YOLO detects x5 -> portion gets filled to x5."""
    detections = [
        {"label": "banana", "confidence": 0.86, "bbox": [i * 10, i * 10, i * 10 + 5, i * 10 + 5]}
        for i in range(5)
    ]
    agent = NutritionAgent(vision_tool=_StubVisionTool(detections))
    stub_engine = _StubGeminiEngine(
        {
            "dish_name": "Banana",
            "items": [
                {
                    "name": "banana",
                    "estimated_weight_grams": 118,
                    "macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                    "confidence_score": 0.7,
                }
            ],
            "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
            "total_confidence": 0.7,
            "composition_analysis": "",
            "notes": "",
        }
    )
    agent.gemini_engine = stub_engine
    agent.rag.search_food = lambda q: (
        {"name": "Banana", "calories": 89, "protein": 1.1, "carbs": 23, "fat": 0.3}
        if "banana" in (q or "").lower()
        else None
    )

    out = json.loads(agent.execute("Analyze this meal", context=[{"type": "image_path", "content": "/tmp/fake.jpg"}]))
    rows = out.get("calorie_breakdown") or []
    assert any(r.get("item", "").lower() == "banana" and int(r.get("quantity", 0)) == 5 for r in rows)
    # Ensure object detections were passed through to Gemini engine.
    assert stub_engine.last_object_detections is not None
    assert any(d.get("label") == "banana" and d.get("count") == 5 for d in stub_engine.last_object_detections)


@patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"})
def test_orange_not_misread_as_donut_when_citrus_like(tmp_path) -> None:
    """If YOLO mislabels a citrus-colored solid object as donut, it should be relabeled to orange."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (200, 200), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.ellipse((40, 40, 160, 160), fill=(255, 140, 0))  # orange-ish circle
    p = tmp_path / "citrus.png"
    img.save(p)

    # Model claims "donut", but the region is solid + citrus-colored.
    detections = [{"label": "donut", "confidence": 0.99, "bbox": [40, 40, 160, 160]}]
    agent = NutritionAgent(vision_tool=_StubVisionTool(detections))
    agent.gemini_engine = _StubGeminiEngine(
        {
            "dish_name": "Meal",
            "items": [],
            "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
            "total_confidence": 0.2,
            "composition_analysis": "",
            "notes": "",
        }
    )
    agent.rag.search_food = lambda q: (
        {"name": "Orange", "calories": 47.0, "protein": 0.94, "carbs": 11.75, "fat": 0.12}
        if "orange" in (q or "").lower()
        else None
    )

    out = json.loads(agent.execute("Analyze this meal", context=[{"type": "image_path", "content": str(p)}]))
    rows = out.get("calorie_breakdown") or []
    assert any(r.get("item", "").lower() == "orange" for r in rows)
    assert not any(r.get("item", "").lower() == "donut" for r in rows)

