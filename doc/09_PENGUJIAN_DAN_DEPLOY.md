# Pengujian, tahapan build dan rilis lokal

## Urutan implementasi

| Tahap | Buat | Bukti selesai |
|---|---|---|
| A1 | Struktur repo, dependensi terkunci, sumber video dan kamera, uji webcam | Kamera atau video fixture terbaca. Landmark bergerak pada pratinjau. Tidak ada audio. |
| A2 | Jadwal 30 detik, ekstraksi 52+3, pemeriksaan kualitas awal, ekspor | Sesi lengkap punya 450 indeks unik. Data rusak dan slot hilang tercatat. Ringkasan tervalidasi. |
| B1 | PostgreSQL, migrasi, FastAPI, UI operator | Sesi dapat dimulai, ditutup, disimpan dan ditampilkan setelah browser dibuka ulang. |
| B2 | Asesmen independen, izin, audit, ekspor | Label dapat dikaitkan hanya ke kunjungan yang sesuai. Akses diuji per peran. |
| C | Dataset berizin, skrip pelatihan, laporan evaluasi | Split bebas kebocoran, baseline dapat diulang, hasil disajikan dengan ketidakpastian. |
| D | Integrasi penelitian | Registri, pemeriksaan kompatibilitas skema, hasil per sesi yang diotorisasi. |

## Skenario penerimaan

- **Input stabil.** Gunakan video fixture 30 detik. Verifikasi 450 slot terurut, satu frame maksimum per slot, schema/dimensi benar, serta ringkasan konsisten. Uji hitungan 420/450 pada fixture validitas yang disengaja.
- **Frame hilang atau timestamp berulang.** Pastikan fitur tidak disalin dari frame sebelumnya. Uji tanpa wajah, lebih dari satu wajah bila pemeriksaan diaktifkan, kamera putus, dan input berhenti sebelum 30 detik.
- **Status sesi.** Dua start bersamaan hanya menghasilkan satu pemilik kamera. Uji pembatalan saat perekaman, retry, browser reload dan pemulihan setelah restart. Hasil lengkap baru tersedia setelah artefak dapat dibaca.
- **Kegagalan simpan.** Uji disk penuh, DB tidak tersedia, dan proses berhenti setelah penggantian nama file. Pastikan rekonsiliasi aman dan sesi parsial tidak masuk ekspor sebagai data lengkap.
- **Akses dan kebocoran.** Penilai independen tidak melihat prediksi. Akun tanpa hak tidak dapat memperoleh pratinjau, label atau ekspor. Split dieksekusi dengan uji himpunan ID peserta antarpartisi.
- **Benchmark hardware.** Jalankan sesi dengan C922 pada perangkat target. Catat FPS pratinjau, laju fitur upaya/valid, persentil latensi pemrosesan setelah buffer siap, CPU, RAM dan persentase sesi sukses. Target ekstraksi 15 Hz dan target komputasi kurang dari satu detik setelah buffer siap perlu diukur. Ambang kualitas ditetapkan setelah pilot.

## Rilis lokal

Gunakan Ubuntu 24.04 LTS sebagai target rancangan. Kunci versi Python, paket, model landmarker, dan Node saat versi kompatibel telah diuji. Catat hash model dan fixture. Jalankan PostgreSQL dengan volume persisten, FastAPI satu pekerja kamera, dan sajikan hasil build React di origin lokal yang sama. Batasi listener ke lokal pada MVP. Simpan rahasia di variabel lingkungan atau penyimpanan rahasia milik unit. Uji restart, pencadangan, dan pemulihan pada data sintetis sebelum memakai data penelitian. Dokumentasikan perintah aktual di README repo saat implementasi.
