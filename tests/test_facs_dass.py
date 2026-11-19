"""Tests for FACS 31 Action Units mapping and DASS-3 assessment."""

from ai_face.constants import FROZEN_BLENDSHAPE_NAMES
from ai_face.facs_dass import (
    FACS_31_AUS,
    map_blendshapes_to_facs_aus,
    predict_dass_from_aus,
    quantize_au_intensity,
    score_to_dass_level,
)


def test_quantize_au_intensity():
    """Verify quantization to discrete levels O, A, B, C, D, E."""
    assert quantize_au_intensity(0.02) == 0.0  # Level O
    assert quantize_au_intensity(0.18) == 0.2  # Level A
    assert quantize_au_intensity(0.35) == 0.4  # Level B
    assert quantize_au_intensity(0.55) == 0.6  # Level C
    assert quantize_au_intensity(0.75) == 0.8  # Level D
    assert quantize_au_intensity(0.95) == 0.9  # Level E


def test_map_blendshapes_to_31_facs_aus():
    """Verify that all 31 FACS Action Units are extracted."""
    neutral_blendshapes = {name: 0.05 for name in FROZEN_BLENDSHAPE_NAMES}
    aus = map_blendshapes_to_facs_aus(neutral_blendshapes)

    assert len(aus) == 31
    for au in FACS_31_AUS:
        assert au in aus
        assert aus[au] in (0.0, 0.2, 0.4, 0.6, 0.8, 0.9)


def test_score_to_dass_level_boundaries():
    """Verify 5-level DASS clinical boundary mapping."""
    assert score_to_dass_level(0.05) == "Normal"
    assert score_to_dass_level(0.20) == "Mild"
    assert score_to_dass_level(0.45) == "Moderate"
    assert score_to_dass_level(0.70) == "Severe"
    assert score_to_dass_level(0.90) == "Extremely Severe"


def test_dass_prediction_normal():
    """Verify low AU activations yield Normal DASS scores."""
    low_aus = {au: 0.0 for au in FACS_31_AUS}
    dass = predict_dass_from_aus(low_aus)

    assert dass.depression.level == "Normal"
    assert dass.anxiety.level == "Normal"
    assert dass.stress.level == "Normal"
    assert dass.depression.score < 0.15
    assert dass.anxiety.score < 0.15
    assert dass.stress.score < 0.15


def test_dass_prediction_depression_override():
    """Verify that key depression AUs (AU6, 12, 15, 26 at Level D/E) trigger Extremely Severe."""
    dep_aus = {au: 0.0 for au in FACS_31_AUS}
    dep_aus["AU6"] = 0.8
    dep_aus["AU12"] = 0.8
    dep_aus["AU15"] = 0.9
    dep_aus["AU26"] = 0.8

    dass = predict_dass_from_aus(dep_aus)
    assert dass.depression.level == "Extremely Severe"
    assert dass.depression.score >= 0.80


def test_dass_prediction_stress_elevation():
    """Verify that key stress AUs elevate stress level significantly."""
    stress_aus = {au: 0.0 for au in FACS_31_AUS}
    stress_aus["AU1"] = 0.8
    stress_aus["AU4"] = 0.8
    stress_aus["AU15"] = 0.6
    stress_aus["AU24"] = 0.6

    dass = predict_dass_from_aus(stress_aus)
    assert dass.stress.level in ("Severe", "Extremely Severe")
    assert dass.stress.score >= 0.60
