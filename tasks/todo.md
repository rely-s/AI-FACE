# Task List: AI-FACE FACS-DASS Implementation

## Phase 1: FACS-DASS Mapping Engine (Gavrilescu 2019)

### Task 1.1: FACS 31 Action Units Extractor & Quantizer
- [x] Implementasi `src/ai_face/facs_dass.py`.
- [x] Pemetaan 52 ARKit blendshapes ke 31 FACS AUs.
- [x] Kuantisasi intensitas ke level 0, A (0.2), B (0.4), C (0.6), D (0.8), E (0.9).

**Acceptance criteria:**
- 31 AUs terhitung dengan nilai $[0, 1]$ yang terkuantisasi sesuai level FACS.
- Fungsi dapat dipanggil dari foto tunggal maupun frame streaming.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_facs_dass.py -v`

---

### Task 1.2: DASS-3 Multi-Output Prediction Model
- [x] Implementasi fungsi `predict_dass_levels(au_dict)` di `src/ai_face/facs_dass.py`.
- [x] Menghitung skor kontinu $[0, 1]$ dan 5 level keparahan (*Normal, Mild, Moderate, Severe, Extremely Severe*) untuk Depression, Anxiety, dan Stress.
- [x] Terapkan aturan bypass *Extremely Severe* jika kombinasi AU kunci (Depression: AU6,12,15,26; Anxiety: AU2,9,25,45; Stress: AU1,6,12,15) mencapai level D/E.

**Acceptance criteria:**
- Skor dan level untuk ketiga dimensi (D, A, S) terhitung akurat.
- Ambang batas 5 level sesuai spesifikasi $[0.15, 0.30, 0.60, 0.80]$.

**Verification:**
- Test command: `.venv\Scripts\pytest.exe tests/test_facs_dass.py -v`

---

## Checkpoint: Phase 1
- [x] Modul `facs_dass.py` selesai dengan unit tests passing 100%.

---

## Phase 2: Integrasi Image Processor & Model Foto

### Task 2.1: Image Processor Upgrade
- [x] Perbarui `src/ai_face/image_processor.py` agar menyertakan data FACS AUs dan DASS tri-aksial pada output JSON.
- [x] Pastikan kompatibilitas penuh dengan input file foto tunggal.

**Acceptance criteria:**
- Output JSON memuat field `facs_action_units` dan `dass_assessment`.

**Verification:**
- Jalankan: `.venv\Scripts\ai-face.exe --image .venv/Lib/site-packages/matplotlib/mpl-data/sample_data/grace_hopper.jpg --output-dir output/dass_test`

---

### Task 2.2: Batch Dataset Processing & Training
- [x] Perbarui batch processing direktori foto agar menghasilkan `batch_image_summary.json` dan `batch_dass_summary.csv`.
- [x] Implementasikan `src/ai_face/training/train_photo_classifier.py` untuk melatih model XGBoost langsung dari folder foto berkelas (`data/{class_name}/*.jpg`).

**Acceptance criteria:**
- Folder berisi foto pasien dapat diproses sekaligus dan menghasilkan rekapitulasi DASS per subjek.

---

## Phase 3: Visual Feedback HUD Upgrade (SHORE + DASS Gauge)

### Task 3.1: Visualizer Enhancement
- [x] Perbarui `src/ai_face/visualizer.py` untuk menambahkan visual gauge tri-aksial DASS (Depression, Anxiety, Stress) pada overlay HUD.

**Acceptance criteria:**
- Foto `annotated_*.jpg` memuat status DASS dan 3 bar progres klinis (D, A, S).

**Verification:**
- Cek hasil visualisasi pada foto output.

---

## Checkpoint: Complete
- [x] Semua 45 unit tests lulus: `.venv\Scripts\pytest.exe -v`
- [x] Linter & Formatter bersih: `.venv\Scripts\ruff.exe check .` dan `ruff format --check .`
- [ ] Commit dan push pembaruan ke repositori GitHub.
