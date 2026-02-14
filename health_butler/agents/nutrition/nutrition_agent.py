import logging
import json
import re
import colorsys
from typing import Optional, List, Dict, Any
from src.agents.base_agent import BaseAgent
from src.config import settings
from google.genai.types import GenerateContentConfig
from PIL import Image, ImageStat
from health_butler.cv_food_rec.vision_tool import VisionTool
from health_butler.cv_food_rec.gemini_vision_engine import GeminiVisionEngine
from health_butler.data_rag.simple_rag_tool import SimpleRagTool

logger = logging.getLogger(__name__)

# Backwards-compatible alias for older tests and modules that referenced RagTool.
RagTool = SimpleRagTool

class NutritionAgent(BaseAgent):
    """
    Specialist agent for food analysis.
    
    Phase 11: RAG Nutritional Integration.
    - Uses SimpleRagTool.search_food to anchor vision estimates in ground truth.
    """
    
    def __init__(self, vision_tool: Optional[VisionTool] = None):
        super().__init__(
            role="nutrition",
            system_prompt="""You are an expert Nutritionist AI.
Your goal is to synthesize food analysis into a structured format.

OUTPUT FORMAT:
You MUST return a valid JSON object:
{
  "dish_name": "Main dish identified",
  "total_macros": {
    "calories": 0,
    "protein": 0,
    "carbs": 0,
    "fat": 0
  },
  "confidence_score": 0.0,
  "composition_analysis": "Detailed breakdown of ingredients and portions.",
  "health_tip": "A brief actionable tip.",
    "items_detected": [],
    "calorie_breakdown": [
        {
            "item": "Avocado",
            "quantity": 1,
            "calories_each": 160,
            "calories_total": 160
        }
    ]
}

CRITICAL RULES:
- Use 'RAG_MATCHES' to ground your 'total_macros' calculation.
- If a high-confidence RAG match exists, prioritize its per-100g data calibrated by the estimated portion size.
- DO NOT return 0 for macros if food is detected.
""",
            use_openai_api=False
        )
        self.vision_tool = vision_tool or VisionTool()
        self.gemini_engine = GeminiVisionEngine()
        self.rag = SimpleRagTool()
        # Backwards-compatible attribute name used by earlier phases/tests.
        self.rag_tool = self.rag

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Robustly extract JSON from a string."""
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1:
                return json.loads(text[first_brace:last_brace+1])
            return None
        except Exception as e:
            logger.error(f"[NutritionAgent] JSON extraction failed: {e}")
            return None

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        """Convert arbitrary values to float safely."""
        try:
            return float(value)
        except Exception:
            return default

    def _parse_quantity(self, portion_text: str) -> int:
        """Infer quantity from portion text like 'x3', '3 pieces', or '2x'."""
        if not portion_text:
            return 1

        text = str(portion_text).lower()
        patterns = [
            r"x\s*(\d+)",
            r"(\d+)\s*x",
            r"(\d+)\s*(?:pieces?|items?|slices?|servings?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return max(1, int(match.group(1)))
                except Exception:
                    continue
        return 1

    def _normalize_food_query(self, name: str) -> str:
        """Normalize a food name for RAG lookups (handles common aliases)."""
        text = str(name or "").strip().lower()
        if not text:
            return ""

        # Remove punctuation and collapse whitespace.
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Citrus aliases → orange (USDA dataset doesn't include separate entries).
        citrus_aliases = ("tangerine", "mandarin", "clementine", "satsuma")
        if any(alias in text for alias in citrus_aliases):
            return "orange"

        # Simple plural handling for common fruits.
        if text.endswith("s") and text[:-1] in {"orange", "banana", "apple"}:
            return text[:-1]

        return text

    def _build_calorie_breakdown(
        self,
        items: List[Dict[str, Any]],
        rag_matches: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build per-item calorie estimates plus subtotal using vision + RAG data."""
        breakdown: List[Dict[str, Any]] = []

        def aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            grouped: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                item_name = str(row.get("item") or "Unknown").strip()
                qty = max(1, int(self._to_float(row.get("quantity"), 1)))
                total = self._to_float(row.get("calories_total"), 0.0)
                if total <= 0:
                    continue

                if item_name not in grouped:
                    grouped[item_name] = {
                        "item": item_name,
                        "quantity": 0,
                        "calories_total": 0.0,
                    }
                grouped[item_name]["quantity"] += qty
                grouped[item_name]["calories_total"] += total

            output: List[Dict[str, Any]] = []
            for item_name, row in grouped.items():
                qty = row["quantity"]
                c_total = round(row["calories_total"], 1)
                output.append(
                    {
                        "item": item_name,
                        "quantity": qty,
                        "calories_each": round(c_total / qty, 1),
                        "calories_total": c_total,
                    }
                )
            return output

        rag_by_original: Dict[str, Dict[str, Any]] = {}
        for match in rag_matches or []:
            original_name = str(match.get("original_item") or "").strip().lower()
            if original_name and original_name not in rag_by_original:
                rag_by_original[original_name] = match

        for item in items or []:
            if not isinstance(item, dict):
                continue

            item_name = str(item.get("name") or "Unknown").strip()
            item_key = item_name.lower()
            portion_text = str(item.get("portion") or "")
            quantity = self._parse_quantity(portion_text)
            estimated_grams = self._to_float(item.get("estimated_weight_grams"), 0.0)

            rag_match = rag_by_original.get(item_key)
            calories_per_100g = self._to_float((rag_match or {}).get("calories"), 0.0)
            vision_calories = self._to_float((item.get("macros") or {}).get("calories"), 0.0)

            calories_each = 0.0
            calories_total = 0.0

            if calories_per_100g > 0 and estimated_grams > 0:
                calories_each = round((calories_per_100g * estimated_grams) / 100.0, 1)
                calories_total = round(calories_each * quantity, 1)
            elif vision_calories > 0:
                calories_total = round(vision_calories, 1)
                calories_each = round(calories_total / quantity, 1)
            elif calories_per_100g > 0:
                calories_each = round(calories_per_100g, 1)
                calories_total = round(calories_each * quantity, 1)

            if calories_total <= 0:
                continue

            breakdown.append(
                {
                    "item": item_name,
                    "quantity": int(quantity),
                    "calories_each": calories_each,
                    "calories_total": calories_total,
                }
            )

        if breakdown:
            return aggregate_rows(breakdown)

        for match in rag_matches[:6]:
            name = str(match.get("original_item") or match.get("name") or "Unknown")
            calories = round(self._to_float(match.get("calories"), 0.0), 1)
            if calories <= 0:
                continue
            breakdown.append(
                {
                    "item": name,
                    "quantity": 1,
                    "calories_each": calories,
                    "calories_total": calories,
                }
            )

        return aggregate_rows(breakdown)

    def _sum_macros_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate macro totals from vision-detected items when available."""
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for item in items or []:
            macros = item.get("macros", {}) if isinstance(item, dict) else {}
            for key in totals:
                try:
                    totals[key] += float(macros.get(key, 0) or 0)
                except Exception:
                    continue
        return totals

    def _sum_macros_from_rag(self, rag_matches: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate macro totals from RAG matches."""
        totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for match in rag_matches or []:
            for key in totals:
                try:
                    totals[key] += float(match.get(key, 0) or 0)
                except Exception:
                    continue
        return totals

    def _build_fallback_payload(
        self,
        vision_info: Dict[str, Any],
        rag_matches: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a non-zero nutrition payload when synthesis fails."""
        rag_totals = self._sum_macros_from_rag(rag_matches)
        item_totals = self._sum_macros_from_items(items)

        totals = rag_totals if rag_totals.get("calories", 0) > 0 else item_totals

        dish_name = vision_info.get("dish_name")
        if not dish_name and items:
            first_name = items[0].get("name") if isinstance(items[0], dict) else None
            dish_name = first_name or "Meal"

        if totals.get("calories", 0) <= 0:
            return {
                "dish_name": dish_name or "Meal",
                "total_macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                "detailed_nutrients": {
                    "sodium_mg": 0,
                    "fiber_g": 0,
                    "sugar_g": 0,
                    "saturated_fat_g": 0,
                },
                "confidence_score": vision_info.get("total_confidence", vision_info.get("confidence_score", 0.6)),
                "composition_analysis": "Nutrition data is limited for this item. Try another image angle for better analysis.",
                "health_tip": "Keep portions balanced and pair fruit with a protein source for better satiety.",
                "ingredients_with_portions": [m.get("name", "Unknown") for m in rag_matches[:5]] if rag_matches else [],
                "items_detected": [item.get("name", "Unknown") if isinstance(item, dict) else str(item) for item in items[:5]],
                "calorie_breakdown": self._build_calorie_breakdown(items, rag_matches),
            }

        ingredients = [
            f"{m.get('original_item', m.get('name', 'Unknown'))} (~{m.get('estimated_portion', '1 serving')})"
            for m in rag_matches[:6]
        ]
        if not ingredients:
            ingredients = [
                item.get("name", "Unknown") if isinstance(item, dict) else str(item)
                for item in items[:6]
            ]

        return {
            "dish_name": dish_name or "Meal",
            "total_macros": {k: round(v, 1) for k, v in totals.items()},
            "detailed_nutrients": {
                "sodium_mg": 0,
                "fiber_g": 0,
                "sugar_g": 0,
                "saturated_fat_g": 0,
            },
            "confidence_score": vision_info.get("total_confidence", vision_info.get("confidence_score", 0.85)),
            "composition_analysis": "Estimated from visual food recognition anchored with USDA/RAG nutritional references.",
            "health_tip": "Meal analyzed successfully. Balance remaining meals today with fiber-rich vegetables and hydration.",
            "ingredients_with_portions": ingredients,
            "items_detected": [item.get("name", "Unknown") if isinstance(item, dict) else str(item) for item in items[:6]],
            "calorie_breakdown": self._build_calorie_breakdown(items, rag_matches),
        }

    def execute(self, task: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute nutrition analysis with RAG grounding.
        """
        logger.info("[NutritionAgent] Executing nutrition synthesis with RAG grounding...")
        
        image_path = None
        user_context_str = "{}"
        if context:
            for msg in context:
                if msg.get("type") == "image_path":
                    image_path = msg.get("content")
                elif msg.get("type") == "user_context":
                    user_context_str = msg.get("content", "{}")
        
        yolo_hints: List[Dict[str, Any]] = []
        vision_info = {}
        if image_path:
            # Fast local detection hints (YOLO) to help Gemini and provide deterministic fallback.
            try:
                detections = self.vision_tool.detect_food(image_path)
                allow_labels = {
                    "banana",
                    "apple",
                    "orange",
                    "broccoli",
                    "carrot",
                    "pizza",
                    "donut",
                    "cake",
                    "sandwich",
                    "hot dog",
                }
                img: Optional[Image.Image] = None
                try:
                    img = Image.open(image_path).convert("RGB")
                except Exception:
                    img = None

                def clamp_bbox(bbox: List[float]) -> List[float]:
                    if not img:
                        return [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
                    x1, y1, x2, y2 = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
                    x1 = max(0.0, min(x1, float(img.width - 1)))
                    y1 = max(0.0, min(y1, float(img.height - 1)))
                    x2 = max(0.0, min(x2, float(img.width)))
                    y2 = max(0.0, min(y2, float(img.height)))
                    if x2 <= x1:
                        x2 = min(float(img.width), x1 + 1.0)
                    if y2 <= y1:
                        y2 = min(float(img.height), y1 + 1.0)
                    return [x1, y1, x2, y2]

                def mean_rgb(box: List[float]) -> List[float]:
                    if not img:
                        return [0.0, 0.0, 0.0]
                    x1, y1, x2, y2 = map(int, [box[0], box[1], box[2], box[3]])
                    x1 = max(0, min(x1, img.width - 1))
                    y1 = max(0, min(y1, img.height - 1))
                    x2 = max(0, min(x2, img.width))
                    y2 = max(0, min(y2, img.height))
                    if x2 <= x1 + 1 or y2 <= y1 + 1:
                        return [0.0, 0.0, 0.0]
                    region = img.crop((x1, y1, x2, y2))
                    stat = ImageStat.Stat(region)
                    return [float(stat.mean[0]), float(stat.mean[1]), float(stat.mean[2])]

                def rgb_dist(a: List[float], b: List[float]) -> float:
                    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5

                def bbox_iou(a: List[float], b: List[float]) -> float:
                    ax1, ay1, ax2, ay2 = a
                    bx1, by1, bx2, by2 = b
                    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
                    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
                    inter = inter_w * inter_h
                    if inter <= 0:
                        return 0.0
                    area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
                    area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
                    union = area_a + area_b - inter
                    return float(inter / union) if union > 0 else 0.0

                def citrus_like(bbox: List[float]) -> bool:
                    """Detect orange-like color in inner region."""
                    if not img:
                        return False
                    x1, y1, x2, y2 = bbox
                    w = max(1.0, x2 - x1)
                    h = max(1.0, y2 - y1)
                    inner = [x1 + 0.2 * w, y1 + 0.2 * h, x1 + 0.8 * w, y1 + 0.8 * h]
                    r, g, b = mean_rgb(inner)
                    hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                    return (ss >= 0.25) and (vv >= 0.25) and (0.03 <= hh <= 0.17)

                def donut_like(bbox: List[float]) -> bool:
                    """Heuristic: donut center resembles background more than ring."""
                    if not img:
                        return False
                    x1, y1, x2, y2 = bbox
                    w = x2 - x1
                    h = y2 - y1
                    if w < 30 or h < 30:
                        return False

                    th = max(2.0, 0.22 * min(w, h))
                    ring_boxes = [
                        [x1, y1, x2, y1 + th],  # top
                        [x1, y2 - th, x2, y2],  # bottom
                        [x1, y1 + th, x1 + th, y2 - th],  # left
                        [x2 - th, y1 + th, x2, y2 - th],  # right
                    ]
                    ring_means = [mean_rgb(rb) for rb in ring_boxes]
                    ring = [sum(m[i] for m in ring_means) / max(1, len(ring_means)) for i in range(3)]

                    center = mean_rgb([x1 + 0.35 * w, y1 + 0.35 * h, x1 + 0.65 * w, y1 + 0.65 * h])

                    pad = max(2.0, 0.15 * min(w, h))
                    bg_box = [x1, max(0.0, y1 - 2 * pad), x2, max(0.0, y1 - pad)]
                    if bg_box[3] - bg_box[1] < 5:
                        bg_box = [x1, min(float(img.height), y2 + pad), x2, min(float(img.height), y2 + 2 * pad)]
                    bg = mean_rgb(bg_box) if (bg_box[3] - bg_box[1] >= 5) else [255.0, 255.0, 255.0]

                    d_center_bg = rgb_dist(center, bg)
                    d_center_ring = rgb_dist(center, ring)
                    d_bg_ring = rgb_dist(bg, ring)
                    return (d_center_bg < d_center_ring * 0.75) and (d_bg_ring > 12.0)

                processed: List[Dict[str, Any]] = []
                for det in detections or []:
                    if not isinstance(det, dict):
                        continue
                    label = str(det.get("label") or "").lower().strip()
                    conf = self._to_float(det.get("confidence"), 0.0)
                    bbox = det.get("bbox")
                    if not label or label not in allow_labels or not isinstance(bbox, list) or len(bbox) != 4:
                        continue
                    bbox = clamp_bbox(bbox)

                    min_conf = 0.25
                    if label == "orange":
                        min_conf = 0.15
                    if label == "donut":
                        min_conf = 0.35

                    # Known COCO confusion: oranges/tangerines can be mis-detected as donuts.
                    if label == "donut" and img is not None:
                        if not donut_like(bbox) and citrus_like(bbox):
                            label = "orange"
                            min_conf = 0.15

                    if conf < min_conf:
                        # Allow lower confidence for citrus when color strongly matches.
                        if not (label == "orange" and img is not None and conf >= 0.10 and citrus_like(bbox)):
                            continue

                    processed.append({"label": label, "confidence": conf, "bbox": bbox})

                # Simple NMS per label to prevent double counting.
                kept: List[Dict[str, Any]] = []
                for label in sorted({d["label"] for d in processed}):
                    dets = [d for d in processed if d["label"] == label]
                    dets.sort(key=lambda d: float(d.get("confidence") or 0.0), reverse=True)
                    label_kept: List[Dict[str, Any]] = []
                    for d in dets:
                        if all(bbox_iou(d["bbox"], k["bbox"]) < 0.5 for k in label_kept):
                            label_kept.append(d)
                    kept.extend(label_kept)

                counts: Dict[str, Dict[str, Any]] = {}
                for det in kept:
                    label = str(det.get("label") or "").lower().strip()
                    conf = self._to_float(det.get("confidence"), 0.0)
                    if label not in counts:
                        counts[label] = {"count": 0, "max_confidence": 0.0}
                    counts[label]["count"] += 1
                    counts[label]["max_confidence"] = max(counts[label]["max_confidence"], conf)

                yolo_hints = [
                    {
                        "label": label,
                        "count": info["count"],
                        "max_confidence": round(float(info["max_confidence"]), 3),
                    }
                    for label, info in sorted(counts.items())
                ]
                if yolo_hints:
                    logger.info("[NutritionAgent] YOLO food hints: %s", yolo_hints)
            except Exception as exc:
                logger.warning("[NutritionAgent] YOLO hint extraction failed: %s", exc)

            vision_result = self.gemini_engine.analyze_food(
                image_path,
                user_context_str,
                object_detections=yolo_hints or None,
            )
            if "error" not in vision_result:
                vision_info = vision_result
            else:
                logger.error(f"[NutritionAgent] Vision analysis failed: {vision_result.get('error')}")

            # Reconcile Gemini output with YOLO hints.
            # If Gemini is generic/low-confidence, synthesize items from YOLO so common foods
            # (e.g. bananas) are always named + counted.
            if yolo_hints:
                try:
                    generic_dish_names = {
                        "meal",
                        "food",
                        "unknown meal",
                        "unknown",
                        "unknown food",
                    }
                    dish_lower = str(vision_info.get("dish_name") or "").strip().lower()
                    conf = self._to_float(
                        vision_info.get("confidence_score", vision_info.get("total_confidence", 0.0)),
                        0.0,
                    )
                    items_raw = vision_info.get("items") or []
                    items_list: List[Dict[str, Any]] = (
                        [i for i in items_raw if isinstance(i, dict)] if isinstance(items_raw, list) else []
                    )

                    hint_by_label = {
                        str(h.get("label") or "").lower().strip(): h for h in yolo_hints if isinstance(h, dict)
                    }

                    # Fill missing portions/weights for existing items when YOLO knows the count.
                    default_grams_by_label = {
                        "banana": 118,
                        "apple": 182,
                        "orange": 131,
                        "broccoli": 91,
                        "carrot": 61,
                        "pizza": 285,
                        "donut": 76,
                        "cake": 80,
                        "sandwich": 240,
                        "hot dog": 100,
                    }

                    for item in items_list:
                        raw_name = str(item.get("name") or "")
                        name_norm = self._normalize_food_query(raw_name)
                        # Allow substring match: "banana ripe", "orange seedless", etc.
                        matched_label = next(
                            (lbl for lbl in hint_by_label.keys() if lbl and (lbl in name_norm or name_norm in lbl)),
                            None,
                        )
                        if not matched_label:
                            continue
                        yolo_count = max(1, int(self._to_float(hint_by_label[matched_label].get("count"), 1)))

                        portion_text = str(item.get("portion") or "")
                        portion_qty = self._parse_quantity(portion_text)
                        if yolo_count > 1 and portion_qty <= 1:
                            item["portion"] = f"x{yolo_count}"
                            portion_qty = yolo_count

                        default_g = float(default_grams_by_label.get(matched_label, 100))
                        est_g = self._to_float(item.get("estimated_weight_grams"), 0.0)
                        if est_g <= 0:
                            item["estimated_weight_grams"] = default_g
                        else:
                            # If `portion` is xN, but model provided total grams, convert to per-item.
                            if portion_qty > 1:
                                lower = default_g * (portion_qty * 0.8)
                                upper = default_g * (portion_qty * 1.7)
                                if lower <= est_g <= upper:
                                    est_g = est_g / float(portion_qty)

                            # Clamp extreme / implausible per-item weights (common failure: 1310g orange).
                            max_reasonable = max(600.0, default_g * 3.5)
                            min_reasonable = default_g * 0.25
                            if est_g > max_reasonable or est_g < min_reasonable:
                                est_g = default_g

                            item["estimated_weight_grams"] = round(float(est_g), 1)

                    # Ensure YOLO hint labels are represented in items (helps citrus vs donut confusion).
                    present_norms = {
                        self._normalize_food_query(i.get("name", "")) for i in items_list if isinstance(i, dict)
                    }
                    for lbl, hint in hint_by_label.items():
                        if not lbl or lbl in present_norms:
                            continue
                        count = max(1, int(self._to_float(hint.get("count"), 1)))
                        items_list.append(
                            {
                                "name": lbl.title(),
                                "portion": f"x{count}" if count > 1 else "1 item",
                                "estimated_weight_grams": float(default_grams_by_label.get(lbl, 100)),
                                "confidence_score": float(self._to_float(hint.get("max_confidence"), 0.6)),
                                "macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                            }
                        )
                        present_norms.add(lbl)

                    # If Gemini picked a label-like dish name that's not supported by YOLO hints, prefer hints.
                    label_like_dish = dish_lower in set(default_grams_by_label.keys())
                    if label_like_dish and dish_lower not in hint_by_label and hint_by_label:
                        best_hint = max(
                            (h for h in yolo_hints if isinstance(h, dict)),
                            key=lambda h: float(h.get("max_confidence") or 0.0),
                        )
                        best_label = str(best_hint.get("label") or "").strip()
                        if best_label:
                            vision_info["dish_name"] = best_label.title()

                    # Persist any appended items back onto vision_info.
                    vision_info["items"] = items_list

                    # Decide if we should fall back to YOLO-built items.
                    is_generic = (not items_list) or (dish_lower in generic_dish_names)
                    is_low_conf = conf > 0 and conf < 0.55
                    should_fallback = is_generic and (is_low_conf or not items_list)

                    if should_fallback:
                        fallback_items: List[Dict[str, Any]] = []
                        for hint in yolo_hints:
                            label = str(hint.get("label") or "").lower().strip()
                            if not label:
                                continue
                            count = max(1, int(self._to_float(hint.get("count"), 1)))
                            fallback_items.append(
                                {
                                    "name": label.title(),
                                    "portion": f"x{count}" if count > 1 else "1 item",
                                    "estimated_weight_grams": float(default_grams_by_label.get(label, 100)),
                                    "confidence_score": float(self._to_float(hint.get("max_confidence"), 0.6)),
                                    "macros": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                                }
                            )

                        if fallback_items:
                            vision_info["items"] = fallback_items
                            if dish_lower in generic_dish_names or not dish_lower:
                                vision_info["dish_name"] = fallback_items[0].get("name", "Meal")
                            vision_info["notes"] = (
                                (str(vision_info.get("notes") or "") + " | " if vision_info.get("notes") else "")
                                + "Gemini vision was generic/low-confidence; items reconstructed from YOLO hints."
                            )
                except Exception as exc:
                    logger.warning("[NutritionAgent] YOLO reconciliation failed: %s", exc)
        
        # Phase 11: RAG Grounding
        rag_matches = []
        items = vision_info.get("items", [])
        if not items and vision_info.get("dish_name"):
            items = [{"name": vision_info["dish_name"], "portion": "1 serving"}]
            
        for item in items:
            raw_name = item.get("name", "")
            query_name = self._normalize_food_query(raw_name)
            match = self.rag.search_food(query_name)
            if match:
                match["original_item"] = raw_name
                match["estimated_portion"] = item.get("portion", "unknown")
                rag_matches.append(match)
                logger.info(f"[NutritionAgent] RAG Match Found: {match['name']} for {raw_name}")

        # Final Synthesis Prompt
        synthesis_input = f"""
TASK: {task}
VISION_RESULT: {json.dumps(vision_info)}
RAG_MATCHES (Ground Truth Data): {json.dumps(rag_matches)}

Synthesize the final nutritional analysis. 
IMPORTANT: 
- If RAG_MATCHES or VISION_RESULT contains calorie/macro data, 'total_macros' MUST reflect this. NEVER return 0 if food is visible.
- Use the RAG_MATCHES as the most reliable source for 'per 100g' data, scaling by the portion size estimated in VISION_RESULT.
- Ensure the 'composition_analysis' explains exactly why these specific numbers were chosen.
- For 'ingredients_with_portions', estimate weight/quantity (e.g., '135g x3', '270g total').
- For 'detailed_nutrients', provide estimates for Sodium (mg), Fiber (g), Sugar (g), and Saturated Fat (g) based on common nutritional data.
"""
        
        data = None
        model_candidates = [settings.GEMINI_MODEL_NAME, "gemini-2.5-flash"]
        for model_name in model_candidates:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=self.system_prompt + "\n\n" + synthesis_input,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={
                            "type": "OBJECT",
                            "properties": {
                                "dish_name": {"type": "STRING"},
                                "total_macros": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "calories": {"type": "NUMBER"},
                                        "protein": {"type": "NUMBER"},
                                        "carbs": {"type": "NUMBER"},
                                        "fat": {"type": "NUMBER"}
                                    },
                                    "required": ["calories", "protein", "carbs", "fat"]
                                },
                                "detailed_nutrients": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "sodium_mg": {"type": "NUMBER"},
                                        "fiber_g": {"type": "NUMBER"},
                                        "sugar_g": {"type": "NUMBER"},
                                        "saturated_fat_g": {"type": "NUMBER"}
                                    }
                                },
                                "confidence_score": {"type": "NUMBER"},
                                "composition_analysis": {"type": "STRING"},
                                "health_tip": {"type": "STRING"},
                                "ingredients_with_portions": {
                                    "type": "ARRAY", 
                                    "items": {"type": "STRING"}
                                },
                                "items_detected": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "calorie_breakdown": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "item": {"type": "STRING"},
                                            "quantity": {"type": "NUMBER"},
                                            "calories_each": {"type": "NUMBER"},
                                            "calories_total": {"type": "NUMBER"}
                                        }
                                    }
                                }
                            },
                            "required": ["dish_name", "total_macros", "composition_analysis", "ingredients_with_portions"]
                        }
                    )
                )
                data = response.parsed
                if model_name != settings.GEMINI_MODEL_NAME:
                    logger.info(f"[NutritionAgent] Structured synthesis recovered with fallback model: {model_name}")
                break
            except Exception as e:
                logger.error(f"[NutritionAgent] Structured synthesis failed on {model_name}: {e}")

        if data is None:
            # Text fallback
            result_str = super().execute(synthesis_input, context)
            data = self._extract_json(result_str)
        
        if data:
            # Numeric safety
            if "total_macros" in data:
                for target in ["calories", "protein", "carbs", "fat"]:
                    val = data["total_macros"].get(target, 0)
                    try: data["total_macros"][target] = float(val) if val is not None else 0
                    except: data["total_macros"][target] = 0

            calorie_breakdown = self._build_calorie_breakdown(items, rag_matches)
            if calorie_breakdown:
                data["calorie_breakdown"] = calorie_breakdown
                breakdown_total = sum(self._to_float(row.get("calories_total"), 0.0) for row in calorie_breakdown)
                current_total = self._to_float(data.get("total_macros", {}).get("calories"), 0.0)
                if current_total <= 0:
                    data["total_macros"]["calories"] = round(breakdown_total, 1)

            # Fallback to RAG sum if synthesis is weak
            if data.get("total_macros", {}).get("calories", 0) == 0 and rag_matches:
                logger.info("[NutritionAgent] Synthesis failed macro grounding. calculating from RAG...")
                data["total_macros"]["calories"] = sum(m.get("calories", 0) for m in rag_matches)
                data["total_macros"]["protein"] = sum(m.get("protein", 0) for m in rag_matches)
                data["total_macros"]["carbs"] = sum(m.get("carbs", 0) for m in rag_matches)
                data["total_macros"]["fat"] = sum(m.get("fat", 0) for m in rag_matches)

            return json.dumps(data)

        fallback_payload = self._build_fallback_payload(vision_info, rag_matches, items)
        return json.dumps(fallback_payload)
