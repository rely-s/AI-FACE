"""Head pose estimation and Euler angle extraction from transformation matrices.

CONVENTION SPECIFICATION:
=========================
1. Coordinate System:
   Camera coordinate system is right-handed:
   - X-axis points to the right (screen right).
   - Y-axis points downwards.
   - Z-axis points into the scene away from the optical center.

2. Euler Angles and Axes:
   Decomposition uses cv2.RQDecomp3x3 which decomposes a 3x3 rotation matrix
   into elementary rotations: R = Qz * Qy * Qx
   - Pitch (degrees): Rotation around the X-axis (nodding up/down).
   - Yaw (degrees): Rotation around the Y-axis (turning left/right).
   - Roll (degrees): Rotation around the Z-axis (lateral tilt toward shoulder).

3. Units and Range:
   - All angles are returned in degrees.
   - All angles must be finite floating-point numbers.

4. Decoupling from Preview Mirroring:
   - Pose is always extracted from the raw, un-mirrored camera/video frame.
   - Any mirroring applied for user convenience in the GUI preview operates strictly
     on a visual display buffer and never mutates the transformation matrix or pose values.
"""

import math
from typing import Sequence

import cv2
import numpy as np

from ai_face.models import PoseDeg


def rotation_matrix_to_euler_deg(r_mat: np.ndarray) -> PoseDeg:
    """Decompose a 3x3 rotation matrix into Euler angles (yaw, pitch, roll in degrees).

    Uses RQ decomposition (cv2.RQDecomp3x3) to compute exact Euler angles.
    """
    if r_mat.shape != (3, 3):
        raise ValueError(f"Expected 3x3 rotation matrix, got shape {r_mat.shape}")

    if not np.all(np.isfinite(r_mat)):
        raise ValueError("Rotation matrix contains non-finite values (NaN or Inf)")

    # OpenCV RQDecomp3x3 returns: (pitch, yaw, roll), mtxR, mtxQ, Qx, Qy, Qz
    # where pitch is rotation around X, yaw around Y, and roll around Z in degrees.
    angles, *_ = cv2.RQDecomp3x3(r_mat.astype(np.float64))
    pitch = float(angles[0])
    yaw = float(angles[1])
    roll = float(angles[2])

    if not (math.isfinite(pitch) and math.isfinite(yaw) and math.isfinite(roll)):
        raise ValueError(f"Non-finite angle detected: pitch={pitch}, yaw={yaw}, roll={roll}")

    return PoseDeg(yaw=yaw, pitch=pitch, roll=roll)


def matrix_4x4_to_pose_deg(matrix: Sequence[Sequence[float]] | np.ndarray) -> PoseDeg:
    """Extract rotation matrix from 4x4 rigid transformation matrix and convert to PoseDeg."""
    mat_np = np.asarray(matrix, dtype=np.float64)
    if mat_np.shape != (4, 4):
        raise ValueError(f"Expected 4x4 matrix, got shape {mat_np.shape}")

    r_mat = mat_np[:3, :3]
    return rotation_matrix_to_euler_deg(r_mat)
