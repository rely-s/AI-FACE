"""Tests for 3D head pose Euler angle decomposition and conventions."""

import math

import numpy as np
import pytest

from ai_face.models import PoseDeg
from ai_face.pose import matrix_4x4_to_pose_deg, rotation_matrix_to_euler_deg


def test_identity_rotation_produces_zero_angles():
    """Verify that identity rotation matrix produces (0.0, 0.0, 0.0) degrees."""
    r_identity = np.eye(3, dtype=np.float64)
    pose = rotation_matrix_to_euler_deg(r_identity)

    assert isinstance(pose, PoseDeg)
    assert abs(pose.yaw) < 1e-6
    assert abs(pose.pitch) < 1e-6
    assert abs(pose.roll) < 1e-6


def test_identity_4x4_matrix_produces_zero_angles():
    """Verify that identity 4x4 rigid transform produces (0.0, 0.0, 0.0) degrees."""
    m_identity = np.eye(4, dtype=np.float64)
    # Add translation to verify translation does not corrupt rotation
    m_identity[0, 3] = 15.0
    m_identity[1, 3] = -25.0
    m_identity[2, 3] = 800.0

    pose = matrix_4x4_to_pose_deg(m_identity)
    assert abs(pose.yaw) < 1e-6
    assert abs(pose.pitch) < 1e-6
    assert abs(pose.roll) < 1e-6


def test_pitch_rotation_around_x_axis():
    """Verify positive rotation around X axis corresponds to positive pitch."""
    angle_deg = 12.0
    theta = np.radians(angle_deg)
    rx = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, np.cos(theta), -np.sin(theta)],
            [0.0, np.sin(theta), np.cos(theta)],
        ],
        dtype=np.float64,
    )
    pose = rotation_matrix_to_euler_deg(rx)
    assert pytest.approx(pose.pitch, abs=1e-4) == angle_deg
    assert abs(pose.yaw) < 1e-6
    assert abs(pose.roll) < 1e-6


def test_yaw_rotation_around_y_axis():
    """Verify positive rotation around Y axis corresponds to positive yaw."""
    angle_deg = 20.0
    phi = np.radians(angle_deg)
    ry = np.array(
        [
            [np.cos(phi), 0.0, np.sin(phi)],
            [0.0, 1.0, 0.0],
            [-np.sin(phi), 0.0, np.cos(phi)],
        ],
        dtype=np.float64,
    )
    pose = rotation_matrix_to_euler_deg(ry)
    assert pytest.approx(pose.yaw, abs=1e-4) == angle_deg
    assert abs(pose.pitch) < 1e-6
    assert abs(pose.roll) < 1e-6


def test_roll_rotation_around_z_axis():
    """Verify positive rotation around Z axis corresponds to positive roll."""
    angle_deg = 15.0
    psi = np.radians(angle_deg)
    rz = np.array(
        [
            [np.cos(psi), -np.sin(psi), 0.0],
            [np.sin(psi), np.cos(psi), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    pose = rotation_matrix_to_euler_deg(rz)
    assert pytest.approx(pose.roll, abs=1e-4) == angle_deg
    assert abs(pose.pitch) < 1e-6
    assert abs(pose.yaw) < 1e-6


def test_non_finite_matrix_values_rejected():
    """Verify that NaN or inf matrix values raise ValueError."""
    bad_r = np.eye(3, dtype=np.float64)
    bad_r[0, 0] = math.nan

    with pytest.raises((ValueError, Exception)):
        rotation_matrix_to_euler_deg(bad_r)
