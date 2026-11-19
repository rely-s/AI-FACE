# Implementation Plan: AI-FACE Image-Based FACS-DASS Emotion & Distress System

## Overview
Peningkatan komprehensif arsitektur AI-FACE mengintegrasikan metodologi ilmiah dari penelitian **Gavrilescu & Vizireanu (Sensors 2019)**: *"Predicting Depression, Anxiety, and Stress Levels from Videos Using the Facial Action Coding System (FACS)"* serta studi klinis onkologi **Binz et al. (2023)**. 

Sistem beroperasi murni berbasis citra foto statis (image-based) dengan memetakan 52 blendshape MediaPipe ke dalam **31 FACS Action Units (AUs)** terstandarisasi, kemudian mengonversinya menjadi estimasi klinis **DASS (Depression, Anxiety, Stress Scale)** dengan 5 tingkat keparahan (*Normal, Mild, Moderate, Severe, Extremely Severe*).

---

## Architecture Decisions

1. **Struktur Multi-Layer Sesuai Gavrilescu (2019):**
   - **Layer 1:** Ekstraksi intensitas 31 Action Units FACS dari citra foto statis, dikuantisasi ke 6 level diskrit anatomis (Level O=0, A=0.2, B=0.4, C=0.6, D=0.8, E=0.9).
   - **Layer 2:** Pembangunan Vektor Intensitas Wajah (*Facial Matrix / Vector*) per foto berdimensi $[0, 1]^{31}$.
   - **Layer 3:** Model Pola Hubungan Bersama (*Joint Pattern Model*) untuk memprediksi sekaligus 3 dimensi DASS:
     - **Depression Score & Level** (korelasi primer: AU6, AU12, AU15, AU26)
     - **Anxiety Score & Level** (korelasi primer: AU2, AU9, AU25, AU45)
     - **Stress Score & Level** (korelasi primer: AU1, AU6, AU12, AU15)

2. **Skema Ambang Batas 5 Level Klinis DASS:**
   - `Normal`: $[0.00, 0.15)$
   - `Mild`: $[0.15, 0.30)$
   - `Moderate`: $[0.30, 0.60)$
   - `Severe`: $[0.60, 0.80)$
   - `Extremely Severe`: $[0.80, 1.00]$

3. **Format Dataset Foto Murni (Image-Based):**
   - Pelatihan dan pengujian menggunakan foto wajah pasien/subjek (JPG/PNG).
   - Menghasilkan rekap JSON/CSV berisi skor FACS AUs, DASS tri-aksial, dan foto beranotasi visual HUD SHORE.

---

## Task List

### Phase 1: FACS-DASS Mapping Engine (Gavrilescu 2019)
- [ ] **Task 1.1: FACS 31 Action Units Extractor & Quantizer**
  - Implementasi modul `src/ai_face/facs_dass.py`.
  - Pemetaan 52 ARKit blendshapes ke 31 FACS AUs (AU1, AU2, AU4, AU5, AU6, AU7, AU9, AU10, AU11, AU12, AU13, AU14, AU15, AU16, AU17, AU18, AU20, AU22, AU23, AU24, AU25, AU26, AU27, AU28, AU33, AU34, AU35, AU43, AU45).
  - Kuantisasi intensitas ke level 0, A, B, C, D, E.
- [ ] **Task 1.2: DASS-3 Multi-Output Prediction Model**
  - Implementasi formula inferensi DASS (Depression, Anxiety, Stress) berbasis korelasi empiris Gavrilescu Tabel 3 & Tabel 4.
  - Implementasi deteksi langsung level *Extremely Severe* saat AU kunci mencapai level D atau E (akurasi paper: Depression 84.51%, Anxiety 72.92%, Stress 88.41%).

### Checkpoint: Phase 1 (Mesin FACS-DASS Terverifikasi)
- [ ] Unit tests memvalidasi akurasi ekstraksi 31 AUs dan skor DASS.

---

### Phase 2: Integrasi Image Processor & Model Foto
- [ ] **Task 2.1: Image Processor Upgrade**
  - Perbarui `src/ai_face/image_processor.py` agar menyertakan data FACS AUs dan DASS multi-dimensi pada setiap foto.
  - Ekspor hasil ke `<foto>_dass_result.json`.
- [ ] **Task 2.2: Batch Dataset Processing**
  - Pemrosesan direktori dataset foto menghasilkan rekapitulasi tabular `batch_facs_dass_summary.csv`.

### Checkpoint: Phase 2 (Pemrosesan Foto Menghasilkan DASS)
- [ ] Foto uji menghasilkan prediksi DASS 3 dimensi lengkap.

---

### Phase 3: Visual Feedback HUD Upgrade (SHORE + DASS Gauge)
- [ ] **Task 3.1: Visualizer Enhancement**
  - Memperbarui `src/ai_face/visualizer.py` dengan penanda visual DASS 3 dimensi (D, A, S bar / badges) bersanding dengan radar dial emosi SHORE.
- [ ] **Task 3.2: CLI & Live Display Integration**
  - Menampilkan ringkasan DASS di terminal dan pada live webcam/foto.

### Checkpoint: Complete
- [ ] Seluruh unit tests lulus.
- [ ] CLI siap menerima foto dan menampilkan prediksi DASS akurat.
