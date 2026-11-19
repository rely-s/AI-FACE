# Implementation Plan: AI-FACE Image-Based Emotion & Distress Assessment System

## Overview
Transformasi arsitektur AI-FACE menjadi sistem berbasis citra foto statis (image-based) untuk mendeteksi dan mengklasifikasikan tingkatan distress/stres penderita kanker secara instan, terinspirasi oleh studi klinis Fraunhofer IIS & RS Johanniter Bonn (Binz et al., 2023) dengan engine SHORE. Seluruh proses pelatihan, pengujian, dan inferensi menggunakan dataset foto objek (bukan time-series video 30 detik), didukung visual feedback HUD real-time (polar emotion dial, action unit bars, dan status distress level).

---

## Architecture Decisions

1. **Format Input & Dataset Foto Murni:**
   - Masukan pelatihan dan pengujian berupa file citra statis (`.jpg`, `.jpeg`, `.png`, `.bmp`) terorganisir per folder kelas (`low_distress/`, `moderate_distress/`, `high_distress/`) atau tabular manifest (`image_path, label, subject_id`).
   - Menghilangkan dependensi terhadap grid waktu/slot nominal 450 time-series pada pipeline foto, menggantikannya dengan inferensi per-foto instan.

2. **Ekstraksi Fitur Citra Statis (MediaPipe Image Mode):**
   - Menggunakan MediaPipe Face Landmarker `RunningMode.IMAGE`.
   - Vektor fitur per-foto: 52 ARKit blendshapes + 3 pose angles (yaw, pitch, roll) + turunan geometris FACS Action Units (AU1, AU4, AU6, AU9, AU12, AU15, AU20, AU24).

3. **Model Klasifikasi Foto Berbasis Algoritma XGBoost / LightGBM:**
   - Model dilatih langsung di atas matriks fitur foto yang diekstraksi dari dataset citra.
   - Menggunakan GroupKFold berdasarkan `subject_id` untuk memastikan zero-leakage antarpartisi latih dan uji.

4. **Visual Feedback HUD Ala SHORE (Fraunhofer IIS):**
   - Menghasilkan visualisasi lengkap persis seperti pada Gambar 1 makalah:
     - Radar dial kompas emosi (Happy, Sad, Angry, Surprised).
     - Bounding box klinis dan kontur wajah.
     - Header badge status (ID, Uptime, Status Distress: LOW / MODERATE / HIGH).
     - Emotion progress bar (Happy, Sad, Angry/Tension, Surprised, Neutral, Valence).

---

## Task List

### Phase 1: Image Dataset Structure & Ingestion Pipeline
- [ ] **Task 1.1: Image Dataset Specification & Folder Loader**
  - Implementasi modul dataset loader di `src/ai_face/dataset/image_dataset.py`.
  - Menerima struktur direktori foto (`data/{train,val,test}/{class}/` atau `manifest.csv`).
  - Menyaring citra corrupt, memeriksa format gambar, dan memvalidasi metadata `subject_id`.
- [ ] **Task 1.2: Image Feature Batch Extractor**
  - Implementasi ekstraktor batch foto ke matriks fitur tabular (`features.csv` / `dataset.parquet`).
  - Ekstraksi 52 blendshape + 3 pose untuk setiap foto secara deterministik.
  - Logging status foto tanpa wajah (`NO_FACE`) secara transparan.

### Checkpoint: Phase 1 (Dataset & Fitur Foto Siap)
- [ ] Validasi bahwa folder dataset foto dapat diekstrak menjadi file tabular fitur bersih.
- [ ] Unit tests lulus untuk loader dan validator foto.

---

### Phase 2: Image-Based Model Training & Evaluation Engine
- [ ] **Task 2.1: Photo Distress Model Trainer**
  - Implementasi `src/ai_face/training/train_from_photos.py`.
  - Melatih model XGBoost / Multi-Layer Perceptron langsung dari file fitur foto.
  - Pembagian dataset menggunakan `GroupKFold` berdasarkan `subject_id` foto.
  - Menghasilkan metrik evaluasi: Confusion Matrix, Balanced Accuracy, Macro F1, dan AUROC.
- [ ] **Task 2.2: Synthetic/Public Photo Benchmark Generator & Benchmarking**
  - Menyediakan utilitas untuk mengonversi anotasi dataset publik citra statis (seperti RAF-DB / CK+ / UNBC-McMaster) ke skema AI-FACE.
  - Menyimpan model terlatih ke `models/distress_photo_classifier.joblib` berserta metadata skema di `models/distress_photo_meta.json`.

### Checkpoint: Phase 2 (Model Foto Terlatih & Terverifikasi)
- [ ] Model foto berhasil dilatih dengan cross-validation tanpa kebocoran subjek.
- [ ] Evaluasi performa tersimpan dalam metadata JSON berversi.

---

### Phase 3: Single-Photo & Batch Inference CLI
- [ ] **Task 3.1: Image Distress Predictor API**
  - Implementasi engine inferensi foto `src/ai_face/image_classifier.py`.
  - Menerima 1 foto, memvalidasi kualitas deteksi wajah, menjalankan model foto terlatih, dan mengembalikan `level`, `confidence`, `probabilities`, dan rincian emosi.
- [ ] **Task 3.2: CLI Image Mode Integration**
  - Menghubungkan argumen CLI `--image <path>` dan `--image-dir <path>` dengan model foto terlatih.
  - Mendukung opsi `--save-annotated` untuk menghasilkan foto beranotasi HUD.
  - Menghasilkan laporan rekap `summary_results.csv` untuk pemrosesan folder foto.

### Checkpoint: Phase 3 (Inferensi Foto Berjalan End-to-End)
- [ ] CLI dapat mengeksekusi foto tunggal dan menghasilkan output klasifikasi instan.
- [ ] CLI dapat memproses seluruh folder foto dataset pengujian dan menghasilkan rekap tabular.

---

### Phase 4: Interactive Real-Time SHORE-Style HUD & Visual Feedback
- [ ] **Task 4.1: Real-Time HUD Overlay Generator**
  - Memperkaya `src/ai_face/visualizer.py` dengan penanda visual emosi, polar dial, dan progress bar sesuai makalah Binz et al. (2023).
  - Skema warna adaptif: Hijau (Low Distress), Kuning (Moderate Distress), Merah (High Distress/Pain).
- [ ] **Task 4.2: Live Camera Instant Emotion & Distress Display**
  - Memperbarui mode kamera (`ai-face --camera-index 0`) agar menampilkan inferensi foto/frame instan secara langsung di layar secara real-time tanpa menunggu sesi 30 detik selesai.

### Checkpoint: Phase 4 (Sistem Visual Selesai)
- [ ] Foto hasil olahan memuat visualisasi HUD SHORE yang tajam dan akurat.
- [ ] Kamera webcam menampilkan status stres dan dial emosi seketika pada setiap frame.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Variasi Lansia & Kanker:** Kerutan wajah alami lansia disalahartikan sebagai ketegangan (*browDown*). | High | Kalibrasi baseline netral subjek (*valence evaluation*) dan normalisasi fitur pose/kontur. |
| **Foto Tanpa Deteksi Wajah:** Foto dengan pencahayaan ekstrem atau sudut menyamping gagal dideteksi MediaPipe. | Med | Kembalikan error terstruktur `NO_FACE` dan simpan foto ke folder `unprocessed/` dengan log yang jelas. |
| **Data Leakage pada Foto:** Foto dari pasien yang sama berada di data train dan test, menghasilkan akurasi palsu (*overfitting*). | High | Wajib menyertakan `subject_id` pada manifest dataset dan mengunci partisi dengan `GroupKFold`. |

---

## Open Questions
- Apakah dataset foto Anda sudah memiliki format folder tertentu (misal folder per kelas `low/moderate/high`) atau berupa file gambar lepas dengan file spreadsheet CSV (manifest)?
- Apakah output klasifikasi yang diinginkan adalah 3 kelas (`Low`, `Moderate`, `High`) atau skor numerik distress skala 0-10 (Distress Thermometer)?
