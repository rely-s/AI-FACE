# Task List: AI-FACE Image-Based Emotion & Distress System

## Phase 1: Image Dataset Structure & Ingestion Pipeline

### Task 1.1: Image Dataset Specification & Folder Loader
- [ ] Implementasi `src/ai_face/dataset/image_dataset.py` untuk membaca direktori dataset foto (struktur `root/{class_name}/*.jpg` dan manifest CSV).
- [ ] Pemeriksaan integritas gambar (file corrupt, ukuran 0, decoding OpenCV).
- [ ] Ekstraksi metadata subjek dari nama file atau kolom manifest.

**Acceptance criteria:**
- Loader membaca format folder class dan manifest CSV dengan benar.
- File corrupt disaring dan dilaporkan tanpa membuat proses crash.
- Unit test lulus memvalidasi loading folder foto.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_image_dataset.py -v`

---

### Task 1.2: Image Feature Batch Extractor
- [ ] Implementasi modul ekstraksi batch untuk foto di `src/ai_face/dataset/batch_extractor.py`.
- [ ] Ekstraksi 52 blendshape + 3 pose untuk setiap foto menggunakan MediaPipe Image mode.
- [ ] Penyimpanan hasil ekstraksi ke file tabular `extracted_features.csv`.

**Acceptance criteria:**
- Setiap foto menghasilkan 1 baris fitur (55 kolom fitur + metadata label & subject_id).
- Foto tanpa wajah dicatat sebagai `NO_FACE` dan dipisahkan.
- Format CSV tervalidasi dan siap untuk training model.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_batch_extractor.py -v`

---

## Checkpoint: Phase 1
- [ ] Loader dan ekstraktor batch tervalidasi dengan pengujian otomatis.
- [ ] Foto dataset dapat diekstrak menjadi matriks fitur tabular.

---

## Phase 2: Image-Based Model Training & Evaluation Engine

### Task 2.1: Photo Distress Model Trainer
- [ ] Implementasi `src/ai_face/training/train_from_photos.py`.
- [ ] Training classifier XGBoost pada matriks fitur foto.
- [ ] Implementasi 5-Fold GroupKFold berdasarkan `subject_id`.
- [ ] Penyimpanan model terkompilasi ke `models/distress_photo_classifier.joblib` dan registri `models/distress_photo_meta.json`.

**Acceptance criteria:**
- Zero-leakage: Partisipan di fold training dan validation saling disjoint.
- Metrik log-loss, balanced accuracy, dan classification report tercatat rapi di JSON.
- Model berhasil disimpan dan dapat dimuat ulang.

**Verification:**
- Run command: `.venv\Scripts\python.exe -m ai_face.training.train_from_photos`

---

### Task 2.2: Photo Dataset Benchmark Generator
- [ ] Utilitas pembuatan dataset benchmark foto untuk pengujian offline dan verifikasi otomatis.
- [ ] Mendukung pemetaan dataset publik ekspresi/nyeri (UNBC-McMaster, RAF-DB, CK+) ke format AI-FACE.

**Acceptance criteria:**
- Benchmark generator menghasilkan dataset foto sintetis/calibrated berlabel untuk CI/CD.
- Evaluasi baseline performa model tercatat.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_train_from_photos.py -v`

---

## Checkpoint: Phase 2
- [ ] Model foto terlatih siap pakai di folder `models/`.
- [ ] Cross-validation GroupKFold terbukti valid.

---

## Phase 3: Single-Photo & Batch Inference CLI

### Task 3.1: Image Distress Predictor API
- [ ] Implementasi `src/ai_face/image_classifier.py` untuk inferensi foto instan.
- [ ] Menerima path foto atau numpy array, menjalankan ekstraksi, dan memprediksi tingkatan stres (`LOW`, `MODERATE`, `HIGH`) beserta confidence.

**Acceptance criteria:**
- Eksekusi inferensi foto < 100 ms per citra.
- Output berupa struktur data lengkap (distress level, probabilities, emotion breakdown).
- Penanganan foto tanpa wajah mengembalikan error `NO_FACE` yang jelas.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_image_classifier.py -v`

---

### Task 3.2: CLI Image Mode Integration
- [ ] Hubungkan opsi `--image` dan `--image-dir` pada `ai-face` CLI.
- [ ] Dukungan penyimpanan visual beranotasi HUD dengan opsi `--save-annotated`.
- [ ] Ekspor rekap batch foto ke `batch_summary.csv` dan JSON.

**Acceptance criteria:**
- Perintah `ai-face --image foto.jpg` menampilkan hasil klasifikasi seketika di konsol.
- Perintah `ai-face --image-dir folder_foto` memproses seluruh foto dan menghasilkan rekap tabular.

**Verification:**
- Command: `.venv\Scripts\ai-face.exe --image tests/fixtures/sample_face.jpg --output-dir output/test_cli`

---

## Checkpoint: Phase 3
- [ ] CLI foto tunggal dan batch berjalan mulus.
- [ ] Output prediksi dan rekap data tervalidasi.

---

## Phase 4: Interactive Real-Time SHORE-Style HUD & Visual Feedback

### Task 4.1: Real-Time HUD Overlay Generator
- [ ] Penyempurnaan `src/ai_face/visualizer.py` untuk merender tampilan persis seperti pada Gambar 1 makalah Binz et al. (2023):
  - Radar polar dial emosi di sisi kiri (Happy, Surprised, Sad, Angry).
  - Bounding box klinis dan landmark kontur wajah.
  - Header box (ID, Uptime, Status Distress: LOW / MODERATE / HIGH).
  - Bottom bar panel (Happy, Sad, Angry, Surprised, Neutral, Distress Index).

**Acceptance criteria:**
- Citra hasil anotasi memuat seluruh elemen visual SHORE secara proporsional.
- Skema warna adaptif: Hijau (Low), Oranye (Moderate), Merah (High).

**Verification:**
- Test visualisasi: cek file hasil `annotated_*.jpg` di folder output.

---

### Task 4.2: Live Camera Instant Emotion & Distress Display
- [ ] Integrasikan `render_shore_style_overlay` ke jendela kamera langsung (`ai-face --camera-index 0`).
- [ ] Menampilkan dial dan status stres secara instan setiap frame real-time.

**Acceptance criteria:**
- Kamera menampilkan HUD dinamis yang merespons perubahan mimik wajah seketika.
- Frame rate tampilan preview stabil tanpa lag.

**Verification:**
- Jalankan: `.venv\Scripts\ai-face.exe --camera-index 0`

---

## Checkpoint: Complete
- [ ] Semua unit test lulus: `.venv\Scripts\pytest.exe -v`
- [ ] Linter & Formatter bersih: `.venv\Scripts\ruff.exe check .` dan `ruff.exe format --check .`
- [ ] Sistem siap digunakan untuk dataset foto maupun kamera live.
