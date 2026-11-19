# AI-FACE: Facial Feature Acquisition & Clinical FACS-DASS Assessment

Sistem akuisisi dan klasifikasi fitur wajah berbasis **Facial Action Coding System (FACS)**, asesmen klinis **DASS-3 (Depression, Anxiety, Stress)**, dan visualisasi emosi **Fraunhofer SHORE** untuk penelitian tingkat stres pada penderita kanker dan pediatrik.

Panduan mendalam mengenai teks, metrik, dan teori klinis tersedia di:  
👉 **[`doc/PANDUAN_INDIKATOR_KLINIS_DAN_FACS.md`](doc/PANDUAN_INDIKATOR_KLINIS_DAN_FACS.md)**

---

## 1. Fitur Utama

- **Akuisisi Sesi Standar**: Perekaman 30 detik pada target 15 Hz (450 slot waktu nominal) dari webcam atau video file lokal dengan ekspor atomik (`features.jsonl` dan `session_summary.json`).
- **31 Action Units FACS**: Mengekstrak dan menguantisasi 31 AUs (AU1 s.d. AU35) ke dalam 6 tingkatan intensitas diskrit ($0, A, B, C, D, E$) sesuai standar Ekman & Friesen (Gavrilescu 2019).
- **Asesmen Klinis DASS-3**: Menghitung skor kontinu $[0, 1]$ dan 5 interval keparahan (*Normal, Mild, Moderate, Severe, Extremely Severe*) untuk Depresi, Kecemasan, dan Stres.
- **Dukungan Dataset Foto Statis**: Menganalisis foto tunggal (`.jpg`, `.png`), memproses satu direktori foto pasien sekaligus, dan mengekspor rekapitulasi tabular `batch_dass_summary.csv` untuk analisis statistik di Excel / SPSS.
- **Pelatihan Model dari Foto**: Melatih model klasifikasi XGBoost langsung dari direktori kelas foto pasien (`ai-face --train-from-photos`).
- **Antarmuka Interaktif Cerdas**: Dilengkapi tombol clickable pada layar (klik mouse) dan shortcut keyboard (`'E'`) untuk memisahkan mode klinis murni dari visualisasi emosi dasar.

---

## 2. Instalasi dan Setup

Persyaratan:
- Python 3.10 – 3.12 (disarankan Python 3.12)
- Virtual environment disarankan (`uv` atau `python -m venv`)

```powershell
# Buat dan aktifkan virtual environment
uv venv --python 3.12 .venv
.venv\Scripts\activate

# Install paket lokal dan dependensi
uv pip install -e ".[dev]"

# Unduh model resmi Google MediaPipe Face Landmarker
ai-face --download-model
```

Model resmi tersimpan di `models/face_landmarker.task` dengan checksum SHA-256:  
`64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`

---

## 3. Cara Pemakaian

### A. Platform Web Interaktif (Dashboard Browser)
```powershell
# Jalankan server web lokal dan buka otomatis di browser (http://127.0.0.1:8000)
ai-face --web

# Pilihan port kustom
ai-face --web --port 8080 --no-browser
```
Platform Web AI-FACE menyediakan antarmuka terpadu:
- **Live Camera Monitor:** Streaming kamera browser dengan HUD real-time dan toggle ekspresi.
- **Diagnostik Foto Pasien:** Unggah foto wajah $\to$ inspeksi visual HUD, skor DASS-3, dan tabel 31 FACS Action Units dengan pencarian & filter.
- **Batch Dataset Evaluation:** Unggah banyak foto pasien sekaligus $\to$ rekapitulasi tabel dan tombol unduh CSV untuk Excel/SPSS.
- **Glosarium Klinis:** Penjelasan interaktif mengenai otot anatomi, arti klinis, dan panduan 5 level keparahan DASS-3.

### B. Mode Webcam Desktop (Live Stream & Pratinjau GUI)
```powershell
# Jalankan sesi webcam default (Mode Klinis Murni: DASS-3 & FACS AUs)
ai-face --camera-index 0

# Jalankan dengan mode emosi (Radar dial & bar emosi aktif sejak awal)
ai-face --camera-index 0 --show-emotions

# Menjalankan sesi dengan durasi kustom
ai-face --camera-index 0 --duration 30.0 --fps 15.0 --output-dir ./output
```
- **Interaksi Tombol Preview:**
  - **Klik Mouse:** Klik kotak `[ EKSPRESI: NONAKTIF (E) ]` di pojok kiri atas layar untuk mengaktifkan/menonaktifkan bar emosi dan radar dial.
  - **Hotkey Keyboard:** Tekan tombol **`'E'`** untuk beralih mode secara instan.
  - **Keluar/Selesai:** Tekan **`'q'`** atau **`ESC`** pada jendela preview, atau **`Ctrl+C`** di terminal.

### C. Mode Foto Statis (Single Image & Batch Directory)
```powershell
# 1. Analisis satu foto pasien
ai-face --image path/to/patient.jpg --output-dir output/patient_result

# 2. Analisis satu folder foto pasien (otomatis membuat rekap CSV)
ai-face --image-dir path/to/photos_folder/ --output-dir output/batch_results

# 3. Analisis foto dengan overlay emosi aktif
ai-face --image path/to/patient.jpg --output-dir output/patient_result --show-emotions
```
Output pemrosesan foto menghasilkan:
- `*_result.json`: Data lengkap 52 blendshapes, 31 FACS AUs, skor DASS-3, dan emosi.
- `annotated_*.jpg`: Gambar wajah beranotasi HUD dengan visual feedback.
- `batch_dass_summary.csv`: Rekapitulasi evaluasi klinis seluruh subjek dalam folder.

### C. Melatih Model Classifier dari Folder Foto
```powershell
# Melatih model XGBoost langsung dari folder berstruktur kelas:
# data/train/{normal, mild, moderate, severe, extremely_severe}/*.jpg
ai-face --train-from-photos path/to/dataset_folder/ --photo-model-out models/custom_model.joblib
```

### D. Mode File Video (Headless / Automated Test)
```powershell
# Ekstraksi tanpa GUI dari file video
ai-face --video path/to/sample.mp4 --headless --output-dir ./output
```

---

## 4. Antarmuka Visual & Indikator Klinis

```
+-------------------------------------------------------------------------------+
| [ EKSPRESI: NONAKTIF (E) ]      ID: e665537b             DASS-3 CLINICAL (FACS) |
| (Klik Mouse / Tombol 'E')      Uptime: 14.6s             DEP: Norm   0% [     ] |
|                                Distress: LOW             ANX: Mild  21% [==   ] |
|                                                          STR: Norm   0% [     ] |
|                                                                               |
|                                [ Tracking Wajah ]                             |
|                               [ 478 Mesh & Bracket ]                          |
|                                                                               |
|       +---------------------------------------------------------------+       |
|       |         FACS ACTION UNITS (MUSCULAR ACTIVITY LEVEL: 0-E)      |       |
|       | AU1  Inner Bro: [0] [    ]     | AU9  Nose Wrin: [0] [    ]   |       |
|       | AU2  Outer Bro: [B] [=== ]     | AU12 Lip Corne: [0] [    ]   |       |
|       | AU4  Brow Lowe: [0] [    ]     | AU15 Lip Depre: [0] [    ]   |       |
|       | AU5  Upper Lid: [0] [    ]     | AU20 Lip Stret: [0] [    ]   |       |
|       | AU6  Cheek Rai: [0] [    ]     | AU24 Lip Press: [0] [    ]   |       |
|       | AU7  Lid Tight: [A] [==  ]     | AU25 Lips Part: [0] [    ]   |       |
|       | AU45 Blink    : [A] [==  ]     | AU26 Jaw Drop : [0] [    ]   |       |
|       +---------------------------------------------------------------+       |
+-------------------------------------------------------------------------------+
```

1. **Kotak Info Subjek**: Menampilkan ID unik pseudonim (privasi medis), waktu sesi (*Uptime*), dan status distres global (`LOW`, `MODERATE`, `HIGH`).
2. **Panel DASS-3**: Menampilkan skor dan tingkat keparahan untuk **Depresi** (`DEP`), **Kecemasan** (`ANX`), dan **Stres** (`STR`).
3. **Panel FACS Action Units**: Rincian aktivasi 14 otot wajah kunci dengan 6 tingkat intensitas:
   - `[0]`: Netral / Tidak aktif.
   - `[A]`: *Trace* (Jejak sangat halus).
   - `[B]`: *Slight* (Kontraksi ringan).
   - `[C]`: *Marked* (Kontraksi sedang / tegas).
   - `[D]`: *Severe* (Kontraksi kuat).
   - `[E]`: *Maximum* (Kontraksi maksimal).

---

## 5. Struktur Ekspor Sesi

Setiap sesi webcam/video menghasilkan folder di `<output_dir>/<session_id>/`:
```
output/<session_id>/
├── features.jsonl        # 450 slot rekaman fitur wajah (skema versi 1.0.0)
└── session_summary.json  # Ringkasan sesi, rasio validitas, laju efektif, dan status estimasi
```

### Format Kontrak Slot (`features.jsonl`):
```json
{
  "schema_version": "1.0.0",
  "session_id": "e665537b-1234-5678-9abc-def012345678",
  "slot_index": 0,
  "target_ms": 0,
  "frame_ms": 12,
  "valid": true,
  "reasons": [],
  "blendshapes": { "_neutral": 0.001, "browDownLeft": 0.012, "...": 0.0 },
  "pose_deg": { "yaw": 0.25, "pitch": 4.12, "roll": -1.05 }
}
```

---

## 6. Pengujian & Standar Kualitas Kode

Proyek ini dilengkapi 50 unit & integration test otomatis dengan cakupan penuh:

```powershell
# Jalankan seluruh unit test suite
pytest -v

# Jalankan linter dan formatter Ruff
ruff check .
ruff format --check .
```

---

## 7. Referensi Riset & Landasan Teori

1. **Gavrilescu & Vizireanu (2019)**: *"Predicting Depression, Anxiety, and Stress Levels from Videos Using the Facial Action Coding System"*, Sensors, 19(17), 3693.
2. **Binz et al. (2023)**: *"Machine-based emotion-assessment in waiting rooms – a feasibility and acceptance study"*, Current Directions in Biomedical Engineering, 9(1), 115–118.
3. **Ekman & Friesen (1978)**: *"Facial Action Coding System: A Technique for the Measurement of Facial Movement"*, Consulting Psychologists Press.
