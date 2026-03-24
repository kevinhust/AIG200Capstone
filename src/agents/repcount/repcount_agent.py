import json
import logging
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from typing import Optional, List, Dict, Any

from src.agents.base_agent import BaseAgent
from src.agents.repcount.rep_counter import RepCounter
from src.agents.repcount.utils import calculate_angle_3d
from src.agents.repcount.validator import check_visibility

logger = logging.getLogger(__name__)

EXERCISE_CONFIG = {
    "squat":          {"landmarks": (23, 25, 27), "down": 90,  "up": 160},
    "pushup":         {"landmarks": (11, 13, 15), "down": 90,  "up": 160},
    "bicep_curl":     {"landmarks": (11, 13, 15), "down": 40,  "up": 140},
    "shoulder_press": {"landmarks": (13, 11, 23), "down": 90,  "up": 160},
    "deadlift":       {"landmarks": (11, 23, 25), "down": 90,  "up": 160},
    "lunge":          {"landmarks": (23, 25, 27), "down": 90,  "up": 160},
    "lateral_raise":  {"landmarks": (23, 11, 13), "down": 30,  "up": 80},
}


class RepCountAgent(BaseAgent):
    """Counts exercise reps from uploaded video using MediaPipe Pose."""

    def __init__(self):
        super().__init__(
            role="repcount",
            system_prompt="You are a rep counting agent that analyzes exercise videos.",
            use_openai_api=False,
        )

    def count_reps_from_video(
        self, video_path: str, exercise: str = "squat"
    ) -> Dict[str, Any]:
        """Process a video file and return rep count + metadata."""
        config = EXERCISE_CONFIG.get(exercise)
        if not config:
            return {"error": f"Unknown exercise: {exercise}", "total_reps": 0}

        lm_a, lm_b, lm_c = config["landmarks"]
        counter = RepCounter(config["down"], config["up"])
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {"error": "Could not open video file", "total_reps": 0}

        landmarker = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(
                    model_asset_path="models/pose_landmarker.task"
                ),
                running_mode=vision.RunningMode.VIDEO,
                num_poses=1,
            )
        )

        frame_idx = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 1
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            timestamp_ms = int((frame_idx / fps) * 1000)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                lms = results.pose_landmarks[0]
                low_vis = check_visibility(lms, exercise)
                if not low_vis:
                    a = [lms[lm_a].x, lms[lm_a].y, lms[lm_a].z]
                    b = [lms[lm_b].x, lms[lm_b].y, lms[lm_b].z]
                    c = [lms[lm_c].x, lms[lm_c].y, lms[lm_c].z]
                    angle = calculate_angle_3d(a, b, c)
                    counter.update(angle)

        landmarker.close()
        cap.release()

        return {
            "exercise": exercise,
            "rep_count": counter.count,
            "total_frames": total_frames,
            "video_duration_sec": round(frame_idx / fps, 1),
        }

    async def execute_async(
        self, task: str, context=None, **kwargs
    ) -> str:
        """Called by HealthSwarm to process a rep-counting task."""
        import asyncio
        exercise = "squat"  # default
        video_path = None

        if context:
            for item in context:
                if item.get("type") == "video_path":
                    video_path = item["content"]
                if item.get("type") == "exercise":
                    exercise = item["content"].lower().strip()

        if not video_path:
            return json.dumps({"error": "No video provided for rep counting"})

        result = await asyncio.to_thread(
            self.count_reps_from_video, video_path, exercise
        )
        return json.dumps(result)
