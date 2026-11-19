"""Single-frame emotion and distress evaluation from facial Action Units and blendshapes."""

from dataclasses import dataclass
from typing import Mapping


@dataclass
class FrameEmotionResult:
    """Emotion scores and distress classification for a single face image/frame."""

    happy: float
    sad: float
    angry: float
    surprised: float
    neutral: float
    valence: float  # -1.0 (unpleasant/negative) to +1.0 (pleasant/positive)
    distress_score: float  # 0.0 (no distress) to 1.0 (severe distress)
    distress_level: str  # "LOW", "MODERATE", "HIGH"


def evaluate_frame_emotions(blendshapes: Mapping[str, float]) -> FrameEmotionResult:
    """Compute basic emotions and distress index directly from 52 ARKit blendshapes.

    Follows Facial Action Coding System (FACS) mappings:
    - Happy: AU6 (Cheek Squint) + AU12 (Lip Corner Puller)
    - Sad: AU1 (Inner Brow Raiser) + AU4 (Brow Lowerer) + AU15 (Lip Corner Depressor)
    - Angry: AU4 (Brow Lowerer) + AU9 (Nose Wrinkler) + AU24 (Lip Pressor) + Jaw Clenching
    - Surprised: AU1+2 (Brow Raiser) + AU5 (Upper Lid Raiser) + AU26 (Jaw Drop)
    - Distress: Composite tension index from negative valence, brow contraction, and mouth clench.
    """
    # 1. Happiness / Positive Valence
    smile = 0.5 * (blendshapes.get("mouthSmileLeft", 0.0) + blendshapes.get("mouthSmileRight", 0.0))
    cheek = 0.5 * (
        blendshapes.get("cheekSquintLeft", 0.0) + blendshapes.get("cheekSquintRight", 0.0)
    )
    happy = min(1.0, max(0.0, 0.7 * smile + 0.3 * cheek))

    # 2. Sadness / Dejection
    brow_inner = blendshapes.get("browInnerUp", 0.0)
    mouth_frown = 0.5 * (
        blendshapes.get("mouthFrownLeft", 0.0) + blendshapes.get("mouthFrownRight", 0.0)
    )
    mouth_lower = 0.5 * (
        blendshapes.get("mouthLowerDownLeft", 0.0) + blendshapes.get("mouthLowerDownRight", 0.0)
    )
    sad = min(1.0, max(0.0, 0.4 * mouth_frown + 0.3 * brow_inner + 0.3 * mouth_lower))

    # 3. Anger / Pain / Muscle Tension
    brow_down = 0.5 * (blendshapes.get("browDownLeft", 0.0) + blendshapes.get("browDownRight", 0.0))
    nose_sneer = 0.5 * (
        blendshapes.get("noseSneerLeft", 0.0) + blendshapes.get("noseSneerRight", 0.0)
    )
    mouth_press = 0.5 * (
        blendshapes.get("mouthPressLeft", 0.0) + blendshapes.get("mouthPressRight", 0.0)
    )
    jaw_clench = max(blendshapes.get("jawForward", 0.0), blendshapes.get("mouthClose", 0.0))
    angry = min(
        1.0,
        max(0.0, 0.4 * brow_down + 0.25 * nose_sneer + 0.2 * mouth_press + 0.15 * jaw_clench),
    )

    # 4. Surprise
    brow_outer = 0.5 * (
        blendshapes.get("browOuterUpLeft", 0.0) + blendshapes.get("browOuterUpRight", 0.0)
    )
    eye_wide = 0.5 * (blendshapes.get("eyeWideLeft", 0.0) + blendshapes.get("eyeWideRight", 0.0))
    jaw_open = blendshapes.get("jawOpen", 0.0)
    surprised = min(1.0, max(0.0, 0.35 * brow_outer + 0.35 * eye_wide + 0.3 * jaw_open))

    # 5. Neutral
    raw_neutral = blendshapes.get("_neutral", 0.0)
    max_active = max(happy, sad, angry, surprised)
    neutral = min(1.0, max(0.0, max(raw_neutral, 1.0 - max_active * 1.5)))

    # Normalize emotion spectrum
    total = happy + sad + angry + surprised + neutral
    if total > 0:
        happy /= total
        sad /= total
        angry /= total
        surprised /= total
        neutral /= total

    # 6. Valence (-1.0 negative to +1.0 positive)
    valence = happy - (sad * 0.8 + angry * 0.9)
    valence = min(1.0, max(-1.0, valence))

    # 7. Distress Score (0.0 - 1.0)
    raw_distress = (
        0.40 * brow_down
        + 0.25 * mouth_frown
        + 0.20 * mouth_press
        + 0.15 * jaw_clench
        + 0.10 * nose_sneer
        - 0.35 * smile
    )
    distress_score = min(1.0, max(0.0, raw_distress * 1.8))
    distress_score = round(distress_score, 4)

    if distress_score < 0.30:
        distress_level = "LOW"
    elif distress_score < 0.65:
        distress_level = "MODERATE"
    else:
        distress_level = "HIGH"

    return FrameEmotionResult(
        happy=round(happy, 3),
        sad=round(sad, 3),
        angry=round(angry, 3),
        surprised=round(surprised, 3),
        neutral=round(neutral, 3),
        valence=round(valence, 3),
        distress_score=distress_score,
        distress_level=distress_level,
    )
