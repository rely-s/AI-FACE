# AI-FACE

Spesifikasi implementasi dari nol untuk prototipe penelitian yang merekam fitur wajah per sesi dan mengujinya terhadap asesmen distress independen pada anak dan remaja yang menjalani terapi kanker. Acuan keputusan adalah Transkrip_Lengkap_AI-FACE.pdf versi 21 halaman, khususnya bagian 03, 04, dan 08, serta dokumen teknis yang dilampirkannya.

**Definisi prototipe pertama.** Aplikasi lokal menampilkan kamera secara langsung, menjalankan sesi 30 detik dengan target 15 sampel fitur per detik, lalu menampilkan ringkasan kualitas dan menyimpan data yang diizinkan. Tanpa model klinis yang telah dievaluasi, status estimasinya `not_available`. Target penelitian adalah satu hasil per sesi sesuai acuan asesmen independen.

| Baca | Isi |
|---|---|
| [01_BLUEPRINT.md](01_BLUEPRINT.md) | Ruang lingkup, arsitektur, peran, status, dan struktur repo |
| [02_HARDWARE_DAN_POSISI.md](02_HARDWARE_DAN_POSISI.md) | Diagram pemasangan, jarak, pencahayaan, kalibrasi |
| [03_PIPELINE_AKUISISI.md](03_PIPELINE_AKUISISI.md) | Penjadwalan 450 posisi waktu, fitur, kualitas, ekspor |
| [04_DATASET_DAN_PELABELAN.md](04_DATASET_DAN_PELABELAN.md) | Partisipan, SOP sesi, label, dan kebutuhan sampel |
| [05_ERD_DAN_DATABASE.md](05_ERD_DAN_DATABASE.md) | ERD Mermaid, relasi, integritas, penyimpanan |
| [06_DESAIN_UI_UX.md](06_DESAIN_UI_UX.md) | Layar, wireframe, status, perilaku dan aksesibilitas |
| [07_KONTRAK_API.md](07_KONTRAK_API.md) | Endpoint, contoh JSON, idempotensi, dan kegagalan |
| [08_PELATIHAN_DAN_EVALUASI.md](08_PELATIHAN_DAN_EVALUASI.md) | XGBoost, pembanding, split peserta, validasi |
| [09_PENGUJIAN_DAN_DEPLOY.md](09_PENGUJIAN_DAN_DEPLOY.md) | Uji penerimaan, rilis lokal, pemulihan |
| [10_REFERENSI_GITHUB_DAN_DATASET.md](10_REFERENSI_GITHUB_DAN_DATASET.md) | Pemetaan referensi dan batas pemakaiannya |
| [11_PRIVASI_DAN_TATA_KELOLA.md](11_PRIVASI_DAN_TATA_KELOLA.md) | Akses, data yang disimpan, retensi dan audit |
| [12_PROMPT_AI_AGENT.md](12_PROMPT_AI_AGENT.md) | Prompt siap salin untuk memulai implementasi |

Mulai dari 01–03, lalu jalankan fase A di dokumen 09. Pakai video uji berizin atau kamera pengembang untuk membuktikan alur teknis. Dokumen ini menetapkan rancangan. Performa pada perangkat dan peserta harus diukur pada implementasi.
