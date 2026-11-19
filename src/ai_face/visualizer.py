"""Real-time HUD visualizer matching the clinical SHORE facial emotion/distress layout."""

import math
from typing import Any

import cv2
import numpy as np

from ai_face.single_frame_classifier import FrameEmotionResult


def draw_hud_box(
    img: np.ndarray,
    pt1: tuple[int, int],
    pt2: tuple[int, int],
    color: tuple[int, int, int] = (0, 255, 120),
    thickness: int = 1,
    bracket_len: int = 15,
) -> None:
    """Draw a semi-transparent HUD bounding bracket around face ROI."""
    x1, y1 = pt1
    x2, y2 = pt2

    # Draw corner brackets
    cv2.line(img, (x1, y1), (x1 + bracket_len, y1), color, thickness + 1)
    cv2.line(img, (x1, y1), (x1, y1 + bracket_len), color, thickness + 1)

    cv2.line(img, (x2, y1), (x2 - bracket_len, y1), color, thickness + 1)
    cv2.line(img, (x2, y1), (x2, y1 + bracket_len), color, thickness + 1)

    cv2.line(img, (x1, y2), (x1 + bracket_len, y2), color, thickness + 1)
    cv2.line(img, (x1, y2), (x1, y2 - bracket_len), color, thickness + 1)

    cv2.line(img, (x2, y2), (x2 - bracket_len, y2), color, thickness + 1)
    cv2.line(img, (x2, y2), (x2, y2 - bracket_len), color, thickness + 1)


def draw_radar_dial(
    img: np.ndarray,
    center: tuple[int, int],
    radius: int,
    emotions: FrameEmotionResult,
) -> None:
    """Draw circular radar dial matching Figure 1 left gauge."""
    cx, cy = center
    # Outer circles
    for r in [radius // 3, (2 * radius) // 3, radius]:
        cv2.circle(img, (cx, cy), r, (80, 80, 80), 1)

    # Crosshairs
    cv2.line(img, (cx - radius, cy), (cx + radius, cy), (60, 60, 60), 1)
    cv2.line(img, (cx, cy - radius), (cx, cy + radius), (60, 60, 60), 1)

    # 4 Emotion compass axes: Up=Happy, Right=Surprised, Down=Sad, Left=Angry
    values = [emotions.happy, emotions.surprised, emotions.sad, emotions.angry]
    angles = [-math.pi / 2, 0, math.pi / 2, math.pi]
    points = []
    for val, ang in zip(values, angles, strict=True):
        r_val = int(radius * min(1.0, max(0.1, val)))
        px = int(cx + r_val * math.cos(ang))
        py = int(cy + r_val * math.sin(ang))
        points.append([px, py])

    poly_pts = np.array(points, dtype=np.int32)
    overlay = img.copy()
    cv2.fillPoly(overlay, [poly_pts], (0, 220, 255))
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
    cv2.polylines(img, [poly_pts], True, (0, 255, 255), 1)


def draw_emotion_bars(
    img: np.ndarray,
    top_left: tuple[int, int],
    width: int,
    emotions: FrameEmotionResult,
) -> None:
    """Draw lower HUD panel with emotion bars and distress index."""
    x, y = top_left
    spacing = 16

    dist_color = (
        (0, 0, 255)
        if emotions.distress_level == "HIGH"
        else ((0, 165, 255) if emotions.distress_level == "MODERATE" else (0, 220, 0))
    )

    metrics = [
        ("Happy", emotions.happy, (0, 220, 0)),
        ("Sad", emotions.sad, (220, 150, 0)),
        ("Angry/Tension", emotions.angry, (0, 80, 255)),
        ("Surprised", emotions.surprised, (240, 240, 0)),
        ("Neutral", emotions.neutral, (180, 180, 180)),
        ("Distress Index", emotions.distress_score, dist_color),
    ]

    panel_h = len(metrics) * spacing + 12
    sub = img[y : y + panel_h, x : x + width]
    if sub.shape[0] > 0 and sub.shape[1] > 0:
        dark_rect = np.zeros_like(sub)
        cv2.addWeighted(dark_rect, 0.7, sub, 0.3, 0, sub)
        cv2.rectangle(img, (x, y), (x + width, y + panel_h), (0, 180, 80), 1)

    for i, (name, val, bar_color) in enumerate(metrics):
        by = y + 14 + i * spacing
        cv2.putText(img, name, (x + 6, by - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
        track_x = x + 105
        track_w = width - 150
        cv2.rectangle(img, (track_x, by - 8), (track_x + track_w, by), (50, 50, 50), -1)
        fill_w = int(track_w * min(1.0, max(0.0, val)))
        cv2.rectangle(img, (track_x, by - 8), (track_x + fill_w, by), bar_color, -1)
        pct_text = f"{val * 100:.0f}%"
        cv2.putText(
            img,
            pct_text,
            (track_x + track_w + 6, by - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.32,
            (200, 200, 200),
            1,
        )


def render_shore_style_overlay(
    frame_bgr: np.ndarray,
    detection_result: Any,
    emotions: FrameEmotionResult | None,
    subject_id: str = "Subject-01",
    uptime_s: float = 0.0,
    mirror: bool = False,
) -> np.ndarray:
    """Render full real-time SHORE-style emotion recognition visual display."""
    display = frame_bgr.copy()
    h, w = display.shape[:2]

    # Draw face box and landmarks
    if detection_result and detection_result.face_landmarks:
        face = detection_result.face_landmarks[0]
        xs = [int(p.x * w) for p in face]
        ys = [int(p.y * h) for p in face]
        min_x, max_x = max(0, min(xs) - 15), min(w - 1, max(xs) + 15)
        min_y, max_y = max(0, min(ys) - 25), min(h - 1, max(ys) + 15)

        for p in face[::6]:
            cv2.circle(display, (int(p.x * w), int(p.y * h)), 1, (200, 240, 255), -1)

        draw_hud_box(display, (min_x, min_y), (max_x, max_y), color=(0, 220, 100), thickness=2)

    if mirror:
        display = cv2.flip(display, 1)

    if emotions is not None:
        # 1. Left radar dial
        dial_center = (75, 120)
        draw_radar_dial(display, dial_center, radius=48, emotions=emotions)

        # 2. Top-center Subject Info Box
        cv2.rectangle(display, (w // 2 - 100, 10), (w // 2 + 100, 70), (20, 20, 20), -1)
        cv2.rectangle(display, (w // 2 - 100, 10), (w // 2 + 100, 70), (0, 200, 120), 1)
        cv2.putText(
            display,
            f"ID: {subject_id}",
            (w // 2 - 90, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 255, 200),
            1,
        )
        cv2.putText(
            display,
            f"Uptime: {uptime_s:4.1f}s",
            (w // 2 - 90, 46),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (200, 200, 200),
            1,
        )

        status_color = (
            (0, 240, 0)
            if emotions.distress_level == "LOW"
            else ((0, 180, 255) if emotions.distress_level == "MODERATE" else (0, 0, 255))
        )
        cv2.putText(
            display,
            f"Distress: {emotions.distress_level}",
            (w // 2 - 90, 64),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            status_color,
            1,
        )

        # 3. Bottom Emotion Progression Bar Panel
        bar_w = min(320, w - 40)
        draw_emotion_bars(display, (w // 2 - bar_w // 2, h - 120), bar_w, emotions)

    return display
