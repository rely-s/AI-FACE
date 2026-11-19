"""Unit tests for visualizer, toggle button, and FACS action units display."""

import numpy as np

from ai_face.facs_dass import FACS_31_AUS, DASSResult, DASSState
from ai_face.single_frame_classifier import FrameEmotionResult
from ai_face.visualizer import (
    TOGGLE_BUTTON_RECT,
    _au_score_to_letter,
    draw_facs_action_units_panel,
    draw_toggle_button,
    render_shore_style_overlay,
)


def test_au_score_to_letter_conversion() -> None:
    assert _au_score_to_letter(0.0) == "0"
    assert _au_score_to_letter(0.05) == "0"
    assert _au_score_to_letter(0.15) == "A"
    assert _au_score_to_letter(0.35) == "B"
    assert _au_score_to_letter(0.55) == "C"
    assert _au_score_to_letter(0.75) == "D"
    assert _au_score_to_letter(0.92) == "E"


def test_draw_toggle_button() -> None:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    draw_toggle_button(img, TOGGLE_BUTTON_RECT, active=False)
    draw_toggle_button(img, TOGGLE_BUTTON_RECT, active=True)
    # Ensure drawing produced non-zero pixel modifications
    assert np.any(img > 0)


def test_draw_facs_action_units_panel() -> None:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    aus = {au: 0.4 for au in FACS_31_AUS}
    aus["AU1"] = 0.8
    aus["AU4"] = 0.6
    draw_facs_action_units_panel(img, (20, 300), 400, aus)
    assert np.any(img > 0)


def test_render_shore_style_overlay_clinical_mode() -> None:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    emotions = FrameEmotionResult(
        happy=0.0,
        sad=0.1,
        angry=0.05,
        surprised=0.1,
        neutral=0.85,
        valence=0.0,
        distress_score=0.1,
        distress_level="LOW",
    )
    dass = DASSResult(
        depression=DASSState(score=0.05, level="Normal"),
        anxiety=DASSState(score=0.10, level="Normal"),
        stress=DASSState(score=0.08, level="Normal"),
    )
    aus = {au: 0.2 for au in FACS_31_AUS}

    # Clinical mode (show_emotions=False)
    out_img = render_shore_style_overlay(
        frame_bgr=img,
        detection_result=None,
        emotions=emotions,
        dass=dass,
        facs_aus=aus,
        show_emotions=False,
    )
    assert out_img.shape == (480, 640, 3)
    assert np.any(out_img > 0)


def test_render_shore_style_overlay_emotion_mode() -> None:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    emotions = FrameEmotionResult(
        happy=0.2,
        sad=0.0,
        angry=0.0,
        surprised=0.1,
        neutral=0.7,
        valence=0.2,
        distress_score=0.05,
        distress_level="LOW",
    )
    dass = DASSResult(
        depression=DASSState(score=0.05, level="Normal"),
        anxiety=DASSState(score=0.05, level="Normal"),
        stress=DASSState(score=0.05, level="Normal"),
    )
    aus = {au: 0.2 for au in FACS_31_AUS}

    # Full emotion mode (show_emotions=True)
    out_img = render_shore_style_overlay(
        frame_bgr=img,
        detection_result=None,
        emotions=emotions,
        dass=dass,
        facs_aus=aus,
        show_emotions=True,
    )
    assert out_img.shape == (480, 640, 3)
    assert np.any(out_img > 0)
