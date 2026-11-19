"""FACS Action Units extraction and DASS (Depression, Anxiety, Stress) assessment.

Implements the multi-layer methodology from Gavrilescu & Vizireanu (Sensors 2019):
Predicting Depression, Anxiety, and Stress Levels from Videos Using the FACS.
"""

from dataclasses import dataclass
from typing import Mapping

# The 31 Action Units analyzed in Gavrilescu & Vizireanu (2019)
FACS_31_AUS: tuple[str, ...] = (
    # Upper face (8 AUs)
    "AU1",
    "AU2",
    "AU4",
    "AU5",
    "AU6",
    "AU7",
    "AU43",
    "AU45",
    # Lower face (20 AUs)
    "AU8",
    "AU9",
    "AU10",
    "AU11",
    "AU12",
    "AU13",
    "AU14",
    "AU15",
    "AU16",
    "AU17",
    "AU18",
    "AU19",
    "AU20",
    "AU22",
    "AU23",
    "AU24",
    "AU25",
    "AU26",
    "AU27",
    "AU28",
    # Cheeks (3 AUs)
    "AU33",
    "AU34",
    "AU35",
)

# 5 DASS severity levels with score intervals defined in Gavrilescu (2019) Section 2.2.3
DASS_THRESHOLDS = {
    "Normal": (0.00, 0.15),
    "Mild": (0.15, 0.30),
    "Moderate": (0.30, 0.60),
    "Severe": (0.60, 0.80),
    "Extremely Severe": (0.80, 1.00),
}


@dataclass
class DASSState:
    """Clinical DASS score and severity level for one emotional state."""

    score: float
    level: str  # "Normal", "Mild", "Moderate", "Severe", "Extremely Severe"


@dataclass
class DASSResult:
    """Complete 3-dimensional DASS assessment."""

    depression: DASSState
    anxiety: DASSState
    stress: DASSState


def quantize_au_intensity(raw_value: float) -> float:
    """Quantize continuous activation into 6 discrete FACS levels (Gavrilescu Layer 2).

    Levels:
      Level O (absence): 0.0
      Level A (trace): 0.2
      Level B (slight): 0.4
      Level C (marked): 0.6
      Level D (severe): 0.8
      Level E (maximum): 0.9
    """
    v = max(0.0, min(1.0, raw_value))
    if v < 0.10:
        return 0.0
    elif v < 0.25:
        return 0.2
    elif v < 0.45:
        return 0.4
    elif v < 0.65:
        return 0.6
    elif v < 0.85:
        return 0.8
    else:
        return 0.9


def map_blendshapes_to_facs_aus(blendshapes: Mapping[str, float]) -> dict[str, float]:
    """Map 52 ARKit blendshapes to the 31 canonical FACS Action Units."""

    # Helper getters
    def get(name: str) -> float:
        return blendshapes.get(name, 0.0)

    def avg(n1: str, n2: str) -> float:
        return 0.5 * (blendshapes.get(n1, 0.0) + blendshapes.get(n2, 0.0))

    raw_aus: dict[str, float] = {
        # Upper face
        "AU1": get("browInnerUp"),
        "AU2": avg("browOuterUpLeft", "browOuterUpRight"),
        "AU4": avg("browDownLeft", "browDownRight"),
        "AU5": avg("eyeWideLeft", "eyeWideRight"),
        "AU6": avg("cheekSquintLeft", "cheekSquintRight"),
        "AU7": avg("eyeSquintLeft", "eyeSquintRight"),
        "AU43": avg("eyeBlinkLeft", "eyeBlinkRight"),
        "AU45": max(get("eyeBlinkLeft"), get("eyeBlinkRight")),
        # Lower face
        "AU8": get("mouthClose"),
        "AU9": avg("noseSneerLeft", "noseSneerRight"),
        "AU10": avg("mouthUpperUpLeft", "mouthUpperUpRight"),
        "AU11": 0.5
        * (avg("noseSneerLeft", "noseSneerRight") + avg("mouthUpperUpLeft", "mouthUpperUpRight")),
        "AU12": avg("mouthSmileLeft", "mouthSmileRight"),
        "AU13": avg("mouthDimpleLeft", "mouthDimpleRight"),
        "AU14": avg("mouthDimpleLeft", "mouthDimpleRight"),
        "AU15": avg("mouthFrownLeft", "mouthFrownRight"),
        "AU16": avg("mouthLowerDownLeft", "mouthLowerDownRight"),
        "AU17": avg("mouthShrugLower", "mouthShrugUpper"),
        "AU18": get("mouthPucker"),
        "AU19": get("jawOpen") * 0.4,
        "AU20": avg("mouthStretchLeft", "mouthStretchRight"),
        "AU22": get("mouthFunnel"),
        "AU23": avg("mouthRollLower", "mouthRollUpper"),
        "AU24": avg("mouthPressLeft", "mouthPressRight"),
        "AU25": get("jawOpen"),
        "AU26": get("jawOpen") * 0.8,
        "AU27": max(get("jawOpen"), get("mouthFunnel")),
        "AU28": avg("mouthRollLower", "mouthRollUpper"),
        # Cheeks
        "AU33": get("cheekPuff"),
        "AU34": get("cheekPuff"),
        "AU35": get("mouthPucker") * 0.5,
    }

    # Quantize each AU to discrete FACS levels [0, 0.2, 0.4, 0.6, 0.8, 0.9]
    return {au: quantize_au_intensity(val) for au, val in raw_aus.items()}


def score_to_dass_level(score: float) -> str:
    """Map a continuous score in [0, 1] to one of 5 DASS levels."""
    if score < 0.15:
        return "Normal"
    elif score < 0.30:
        return "Mild"
    elif score < 0.60:
        return "Moderate"
    elif score < 0.80:
        return "Severe"
    else:
        return "Extremely Severe"


def predict_dass_from_aus(aus: Mapping[str, float]) -> DASSResult:
    """Predict Depression, Anxiety, and Stress scores from the 31 FACS Action Units.

    Incorporates empirical correlations and rule overrides from Gavrilescu (2019) Table 3:
    - Depression: AU6, AU12, AU15, AU26
    - Anxiety: AU2, AU9, AU25, AU45
    - Stress: AU1, AU6, AU12, AU15
    """
    # 1. Depression Score
    # Primary: AU15 (frown), AU26 (jaw drop), AU6 (squint/withdrawal), AU12 (suppressed/masked pull)
    au15 = aus.get("AU15", 0.0)
    au26 = aus.get("AU26", 0.0)
    au6 = aus.get("AU6", 0.0)
    au12 = aus.get("AU12", 0.0)
    au4 = aus.get("AU4", 0.0)

    # Gavrilescu rule override: If key AUs reach Level D/E (>= 0.8), assign Extremely Severe
    dep_high_count = sum(1 for val in [au6, au12, au15, au26] if val >= 0.8)
    if dep_high_count >= 3:
        dep_score = 0.88
    else:
        dep_raw = 0.35 * au15 + 0.25 * au26 + 0.20 * au4 + 0.15 * au6 + 0.05 * au12
        dep_score = min(1.0, max(0.0, dep_raw * 1.4))

    # 2. Anxiety Score
    # Primary: AU2 (outer brow raise), AU9 (nose wrinkle), AU25 (lips part), AU45 (blink frequency)
    au2 = aus.get("AU2", 0.0)
    au9 = aus.get("AU9", 0.0)
    au25 = aus.get("AU25", 0.0)
    au45 = aus.get("AU45", 0.0)
    au5 = aus.get("AU5", 0.0)
    au20 = aus.get("AU20", 0.0)

    anx_high_count = sum(1 for val in [au2, au9, au25, au45] if val >= 0.8)
    if anx_high_count >= 3:
        anx_score = 0.86
    else:
        anx_raw = 0.30 * au2 + 0.25 * au9 + 0.20 * au25 + 0.15 * au45 + 0.10 * au5 + 0.10 * au20
        anx_score = min(1.0, max(0.0, anx_raw * 1.4))

    # 3. Stress Score (AU1, AU6, AU12, AU15 + AU4, AU24)
    au1 = aus.get("AU1", 0.0)
    au24 = aus.get("AU24", 0.0)

    stress_high_count = sum(1 for val in [au1, au6, au12, au15] if val >= 0.8)
    if stress_high_count >= 3:
        stress_score = 0.90
    else:
        stress_raw = 0.30 * au1 + 0.25 * au4 + 0.15 * au6 + 0.15 * au15 + 0.15 * au24 + 0.10 * au12
        stress_score = min(1.0, max(0.0, stress_raw * 1.4))

    dep_score = round(dep_score, 4)
    anx_score = round(anx_score, 4)
    stress_score = round(stress_score, 4)

    return DASSResult(
        depression=DASSState(score=dep_score, level=score_to_dass_level(dep_score)),
        anxiety=DASSState(score=anx_score, level=score_to_dass_level(anx_score)),
        stress=DASSState(score=stress_score, level=score_to_dass_level(stress_score)),
    )
