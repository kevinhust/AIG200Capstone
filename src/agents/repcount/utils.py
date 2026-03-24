"""Utility functions for joint angle calculation."""

import numpy as np


def calculate_angle(a, b, c):
    """Calculate the angle at joint b given three points a, b, c.

    Each point is a list or array of [x, y] coordinates.
    Returns the angle in degrees (0–180).
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    # Vectors from b to a and b to c
    ba = a - b
    bc = c - b

    # Compute angle using arctan2 for each vector, then take the difference
    radians = np.arctan2(bc[1], bc[0]) - np.arctan2(ba[1], ba[0])
    angle = np.abs(radians * 180.0 / np.pi)

    # Normalize to 0–180
    if angle > 180.0:
        angle = 360.0 - angle

    return angle


def calculate_angle_3d(a, b, c):
    """Calculate the angle at joint b given three 3D points a, b, c.

    Each point is a list or array of [x, y, z] coordinates.
    Uses the dot-product method for true 3D angle calculation.
    Returns the angle in degrees (0–180).
    """
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    c = np.array(c, dtype=np.float64)

    ba = a - b
    bc = c - b

    # Dot product / magnitude formula
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    cosine = np.clip(cosine, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine))

    return angle
