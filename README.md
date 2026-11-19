# AI-FACE: Facial Feature Acquisition CLI

Prototipe penelitian akuisisi fitur wajah per sesi (30 detik, target 15 Hz / 450 slot nominal) untuk studi asesmen distress pediatrik.

Dokumentasi spesifikasi lengkap tersedia di folder [`doc/`](doc/README.md).

---

## 1. Instalasi dan Setup

Persyaratan:
- Python 3.10 – 3.12 (direkomendasikan Python 3.12)
- Virtual environment disarankan (`uv` atau `python -m venv`)

```powershell
# Buat dan aktifkan virtual environment
uv venv --python 3.12 .venv
.venv\Scripts\activate

# Install paket lokal dan dependensi
uv pip install -e ".[dev]"

# Unduh model resmi Google MediaPipe Face Landmarker (jika belum ada)
python -m ai_face.cli --download-model
```

Model resmi diunduh ke `models/face_landmarker.task` dengan checksum SHA-256:
`64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`

---

## 2. Cara Pemakaian CLI

CLI menyediakan dua opsi input yang saling eksklusif: `--camera-index` (webcam) atau `--video` (file video lokal).

### Mode Webcam (Live Acquisition & Preview)
```powershell
# Jalankan sesi 30 detik dari webcam default (index 0)
ai-face --camera-index 0

# Opsi kustom durasi dan output
ai-face --camera-index 0 --duration 30.0 --fps 15.0 --output-dir ./output
```
- **Pratinjau visual:** Jendela GUI menampilkan status validitas slot, elapsed time, deteksi landmark, dan FPS.
- **Berhenti:** Tekan tombol `q` atau `ESC` pada jendela pratinjau, atau `Ctrl+C` di terminal. Sesi akan ditutup dengan status `cancelled` dan diekspor dengan rapi.

### Mode File Video (Headless / Automated Test)
```powershell
# Ekstraksi tanpa GUI dari file video
ai-face --video path/to/sample.mp4 --headless --output-dir ./output
```

---

## 3. Struktur Hasil Ekspor Per Sesi

Setiap sesi menghasilkan satu folder atomik di dalam direktori output: `<output_dir>/<session_id>/`:
```
output/<session_id>/
├── features.jsonl        # 450 slot rekaman fitur wajah (atau sesuai durasi jika dibatalkan)
└── session_summary.json  # Ringkasan sesi, rasio validitas, laju efektif, dan status estimasi
```

### Kontrak Slot (`features.jsonl`)
Setiap baris merupakan objek JSON:
```json
{
  "schema_version": "1.0.0",
  "session_id": "c1f7b9e0-1234-5678-9abc-def012345678",
  "slot_index": 0,
  "target_ms": 0,
  "frame_ms": 12,
  "valid": true,
  "reasons": [],
  "blendshapes": {
    "_neutral": 0.0001,
    "browDownLeft": 0.012,
    "... 52 kategori ARKit ...": 0.0
  },
  "pose_deg": {
    "yaw": 0.25,
    "pitch": 4.12,
    "roll": -1.05
  }
}
```
Untuk slot tidak valid (misal wajah tidak terdeteksi atau frame hilang):
- `valid: false`
- `reasons: ["NO_FACE"]` atau `["FRAME_MISSED"]`
- `blendshapes: null`
- `pose_deg: null`

### Ringkasan Sesi (`session_summary.json`)
Menampilkan status sesi (`completed`, `cancelled`, `failed`), rasio validitas `valid_slots / 450`, laju efektif `valid_slots / actual_duration_s`, rincian kegagalan per alasan, metadata perangkat dan model, serta `estimation.status = "not_available"`.

---

## 4. Konvensi Pose (Yaw, Pitch, Roll)

- **Sistem Koordinat:** Kamera optik standar tangan kanan (Right-Handed):
  - Sumbu X: Mengarah horizontal ke kanan.
  - Sumbu Y: Mengarah vertikal ke bawah.
  - Sumbu Z: Mengarah ke kedalaman optik (menjauhi kamera).
- **Dekomposisi Rotasi:** Menggunakan dekomposisi ortogonal RQ (`cv2.RQDecomp3x3`) atas submatriks rotasi $3 \times 3$ dari transformasi kaku MediaPipe:
  - **Pitch** (derajat, sumbu X): Gerakan menunduk (positif) / menengadah (negatif).
  - **Yaw** (derajat, sumbu Y): Gerakan menoleh ke kanan subjek (positif) / kiri (negatif).
  - **Roll** (derajat, sumbu Z): Kemiringan kepala ke pundak kanan (positif) / kiri (negatif).
- **Pratinjau Visual:** Pencerminan horizontal (mirror) pada tampilan jendela GUI pengguna tidak mengubah nilai koordinat asli pada ekstraksi fitur.

---

## 5. Pengujian & Linting

```powershell
# Jalankan unit test
pytest -v

# Jalankan ruff linter
ruff check .
```
