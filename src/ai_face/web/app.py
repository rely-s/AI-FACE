"""FastAPI backend application for the AI-FACE Clinical Platform."""

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai_face.constants import DEFAULT_MODEL_PATH
from ai_face.facs_dass import DASS_THRESHOLDS, FACS_31_AUS
from ai_face.image_processor import ImageDistressProcessor
from ai_face.visualizer import render_shore_style_overlay

STATIC_DIR = Path(__file__).parent / "static"

FACS_METADATA: dict[str, dict[str, str]] = {
    "AU1": {
        "name": "Inner Brow Raiser",
        "muscle": "Frontalis, pars medialis",
        "region": "Upper Face",
        "clinical_meaning": "Indikator kesedihan, duka cita, atau rasa cemas mendalam.",
    },
    "AU2": {
        "name": "Outer Brow Raiser",
        "muscle": "Frontalis, pars lateralis",
        "region": "Upper Face",
        "clinical_meaning": "Mengindikasikan atensi visual, waspada, atau kecemasan antisipatif.",
    },
    "AU4": {
        "name": "Brow Lowerer",
        "muscle": "Corrugator supercilii, Depressor supercilii",
        "region": "Upper Face",
        "clinical_meaning": "Penanda utama stres, nyeri (pain), amarah, atau konsentrasi tinggi.",
    },
    "AU5": {
        "name": "Upper Lid Raiser",
        "muscle": "Levator palpebrae superioris",
        "region": "Upper Face",
        "clinical_meaning": "Mata membelalak karena rasa terkejut, takut, atau kewaspadaan tinggi.",
    },
    "AU6": {
        "name": "Cheek Raiser",
        "muscle": "Orbicularis oculi, pars orbitalis",
        "region": "Upper Face",
        "clinical_meaning": "Pipi terangkat pada senyum tulus Duchenne atau ketegangan pipi.",
    },
    "AU7": {
        "name": "Lid Tightener",
        "muscle": "Orbicularis oculi, pars palpebralis",
        "region": "Upper Face",
        "clinical_meaning": "Kelopak mata menyempit karena menahan nyeri fisik atau silau.",
    },
    "AU8": {
        "name": "Lips Toward Each Other",
        "muscle": "Orbicularis oris",
        "region": "Lower Face",
        "clinical_meaning": "Penutupan bibir pasif.",
    },
    "AU9": {
        "name": "Nose Wrinkler",
        "muscle": "Levator labii superioris alaeque nasi",
        "region": "Lower Face",
        "clinical_meaning": "Pangkal hidung berkerut saat rasa sakit menusuk atau rasa jijik.",
    },
    "AU10": {
        "name": "Upper Lip Raiser",
        "muscle": "Levator labii superioris",
        "region": "Lower Face",
        "clinical_meaning": "Pengangkatan bibir atas pada ketidaksenangan atau rasa sakit.",
    },
    "AU11": {
        "name": "Nasolabial Deepener",
        "muscle": "Zygomaticus minor",
        "region": "Lower Face",
        "clinical_meaning": "Pendalaman lipatan nasolabial (garis senyum/sedih).",
    },
    "AU12": {
        "name": "Lip Corner Puller",
        "muscle": "Zygomaticus major",
        "region": "Lower Face",
        "clinical_meaning": "Otot utama senyum dan ekspresi afektif positif.",
    },
    "AU13": {
        "name": "Sharp Lip Puller",
        "muscle": "Levator anguli oris",
        "region": "Lower Face",
        "clinical_meaning": "Peninggian sudut bibir secara tajam.",
    },
    "AU14": {
        "name": "Dimpler",
        "muscle": "Buccinator",
        "region": "Lower Face",
        "clinical_meaning": "Pengetatan sudut mulut (lesung pipi / keraguan).",
    },
    "AU15": {
        "name": "Lip Corner Depressor",
        "muscle": "Depressor anguli oris",
        "region": "Lower Face",
        "clinical_meaning": "Penanda kunci depresi, murung, rasa kecewa, dan putus asa.",
    },
    "AU16": {
        "name": "Lower Lip Depressor",
        "muscle": "Depressor labii inferioris",
        "region": "Lower Face",
        "clinical_meaning": "Penarikan bibir bawah ke arah dagu.",
    },
    "AU17": {
        "name": "Chin Raiser",
        "muscle": "Mentalis",
        "region": "Lower Face",
        "clinical_meaning": "Pengangkatan dagu dan bibir bawah cemberut.",
    },
    "AU18": {
        "name": "Lip Puckerer",
        "muscle": "Incisivii labii superioris / inferioris",
        "region": "Lower Face",
        "clinical_meaning": "Pengerutan bibir ke depan.",
    },
    "AU19": {
        "name": "Tongue Show",
        "muscle": "Genioglossus",
        "region": "Lower Face",
        "clinical_meaning": "Lidah tampak di antara bibir.",
    },
    "AU20": {
        "name": "Lip Stretcher",
        "muscle": "Risorius, Platysma",
        "region": "Lower Face",
        "clinical_meaning": "Peregangan bibir ke samping mendatar pada kepanikan atau rasa takut.",
    },
    "AU22": {
        "name": "Lip Funneler",
        "muscle": "Orbicularis oris",
        "region": "Lower Face",
        "clinical_meaning": "Bibir membentuk corong saat bersuara atau terkejut.",
    },
    "AU23": {
        "name": "Lip Tightener",
        "muscle": "Orbicularis oris",
        "region": "Lower Face",
        "clinical_meaning": "Pengetatan tepi merah bibir saat menahan amarah/stres.",
    },
    "AU24": {
        "name": "Lip Pressor",
        "muscle": "Orbicularis oris",
        "region": "Lower Face",
        "clinical_meaning": "Kedua bibir ditekan rapat menahan rasa sakit atau stres fisik.",
    },
    "AU25": {
        "name": "Lips Part",
        "muscle": "Depressor labii inferioris",
        "region": "Lower Face",
        "clinical_meaning": "Pemisahan bibir santai saat istirahat atau bicara.",
    },
    "AU26": {
        "name": "Jaw Drop",
        "muscle": "Masseter relaksasi, Digastricus",
        "region": "Lower Face",
        "clinical_meaning": "Mulut mengendur pasif karena kelelahan mental atau kelesuan tonus.",
    },
    "AU27": {
        "name": "Mouth Stretch",
        "muscle": "Pterygoideus lateralis",
        "region": "Lower Face",
        "clinical_meaning": "Mulut terbuka lebar saat berteriak atau menguap.",
    },
    "AU28": {
        "name": "Lip Suck",
        "muscle": "Orbicularis oris",
        "region": "Lower Face",
        "clinical_meaning": "Bibir terhisap ke dalam mulut.",
    },
    "AU33": {
        "name": "Cheek Blow",
        "muscle": "Buccinator",
        "region": "Cheeks",
        "clinical_meaning": "Pipi mengembang ditiup.",
    },
    "AU34": {
        "name": "Cheek Puff",
        "muscle": "Buccinator",
        "region": "Cheeks",
        "clinical_meaning": "Penggelembungan pipi sebagian.",
    },
    "AU35": {
        "name": "Cheek Suck",
        "muscle": "Buccinator",
        "region": "Cheeks",
        "clinical_meaning": "Pipi terhisap ke dalam gigi.",
    },
    "AU43": {
        "name": "Eyes Closed",
        "muscle": "Orbicularis oculi",
        "region": "Upper Face",
        "clinical_meaning": "Kedua mata terpejam istirahat atau menahan nyeri.",
    },
    "AU45": {
        "name": "Blink",
        "muscle": "Orbicularis oculi",
        "region": "Upper Face",
        "clinical_meaning": "Kedipan mata (frekuensi naik pada ansietas/kelelahan).",
    },
}


def create_app(model_path: str | Path = DEFAULT_MODEL_PATH) -> FastAPI:
    """Build and configure the FastAPI web service."""
    app = FastAPI(
        title="AI-FACE Clinical Platform",
        description="Clinical Facial Action Coding System (FACS) and DASS-3 Assessment Engine.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    processor: ImageDistressProcessor | None = None
    if Path(model_path).is_file():
        processor = ImageDistressProcessor(model_path=model_path)

    @app.get("/api/v1/health")
    def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "model_loaded": processor is not None,
            "facs_aus_count": len(FACS_31_AUS),
            "dass_dimensions": ["depression", "anxiety", "stress"],
        }

    @app.get("/api/v1/clinical/info")
    def get_clinical_info() -> dict[str, Any]:
        return {
            "facs_metadata": FACS_METADATA,
            "dass_thresholds": DASS_THRESHOLDS,
            "intensity_levels": {
                "0": "Absence (Netral / Tidak aktif)",
                "A": "Trace (Jejak kontraksi sangat halus)",
                "B": "Slight (Kontraksi ringan tampak jelas)",
                "C": "Marked (Kontraksi sedang / deformasi tegas)",
                "D": "Severe (Kontraksi kuat dan nyata)",
                "E": "Maximum (Kontraksi maksimal / ekstrem)",
            },
            "research_references": [
                {
                    "authors": "Gavrilescu & Vizireanu (2019)",
                    "title": "Predicting Depression, Anxiety, and Stress from Videos",
                    "journal": "Sensors (MDPI)",
                },
                {
                    "authors": "Binz et al. (2023)",
                    "title": "Machine-based emotion-assessment in waiting rooms",
                    "journal": "CDBME (Johanniter Hospital Bonn)",
                },
            ],
        }

    @app.post("/api/v1/analyze/photo")
    async def analyze_photo(
        file: UploadFile = File(...),
        show_emotions: bool = Form(False),
    ) -> dict[str, Any]:
        if processor is None:
            raise HTTPException(status_code=503, detail="Face Landmarker model is not loaded.")

        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode uploaded image.")

        blendshapes, emotions, dass, facs_aus, result = processor.process_image(
            img_bgr=img,
            subject_id=Path(file.filename or "patient").stem,
        )

        annotated_bgr = render_shore_style_overlay(
            frame_bgr=img,
            detection_result=result,
            emotions=emotions,
            dass=dass,
            facs_aus=facs_aus,
            show_emotions=show_emotions,
            subject_id=Path(file.filename or "patient").stem[:8],
        )

        # Encode annotated image to JPEG base64
        _, buffer = cv2.imencode(".jpg", annotated_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64_img = base64.b64encode(buffer).decode("utf-8")

        return {
            "image_name": file.filename,
            "face_detected": emotions is not None,
            "distress_level": emotions.distress_level if emotions else "NO_FACE",
            "distress_score": emotions.distress_score if emotions else None,
            "dass_clinical_assessment": {
                "depression": {"score": dass.depression.score, "level": dass.depression.level},
                "anxiety": {"score": dass.anxiety.score, "level": dass.anxiety.level},
                "stress": {"score": dass.stress.score, "level": dass.stress.level},
            }
            if dass
            else None,
            "emotions": {
                "happy": emotions.happy,
                "sad": emotions.sad,
                "angry": emotions.angry,
                "surprised": emotions.surprised,
                "neutral": emotions.neutral,
                "valence": emotions.valence,
            }
            if emotions
            else None,
            "facs_action_units": facs_aus,
            "annotated_image_base64": f"data:image/jpeg;base64,{b64_img}",
        }

    @app.post("/api/v1/analyze/frame")
    async def analyze_frame(
        file: UploadFile = File(...),
        show_emotions: bool = Form(False),
    ) -> dict[str, Any]:
        """Real-time webcam frame snapshot evaluation from the web browser."""
        return await analyze_photo(file=file, show_emotions=show_emotions)

    # Mount static assets
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        def serve_index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app
