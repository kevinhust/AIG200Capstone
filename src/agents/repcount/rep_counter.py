"""Rep counting state machine for exercise tracking."""

from collections import deque


class RepCounter:
    """Tracks exercise reps using an UP/DOWN state machine based on joint angle.

    Args:
        down_threshold: Angle (degrees) below which the exercise is in the
                        "down" position.
        up_threshold:   Angle (degrees) above which the exercise is in the
                        "up" position.
        smooth_window:  Number of frames to average for angle smoothing.
    """

    def __init__(self, down_threshold=90, up_threshold=160, smooth_window=5):
        self.down_threshold = down_threshold
        self.up_threshold = up_threshold
        self.count = 0
        self.stage = None  # None -> "down" -> "up" (one rep)
        self._buffer = deque(maxlen=smooth_window)

    def update(self, angle):
        """Update the state machine with a smoothed angle reading.

        Applies a moving-average filter over the last *smooth_window* frames
        to reduce jitter before evaluating thresholds.

        Returns:
            tuple: (count, stage) — current rep count and stage string.
        """
        self._buffer.append(angle)
        smoothed = sum(self._buffer) / len(self._buffer)

        if smoothed < self.down_threshold:
            self.stage = "down"
        if smoothed > self.up_threshold and self.stage == "down":
            self.stage = "up"
            self.count += 1

        return self.count, self.stage

    def reset(self):
        """Reset the rep counter to its initial state."""
        self.count = 0
        self.stage = None
        self._buffer.clear()
