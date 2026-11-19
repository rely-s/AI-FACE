# Prompt implementasi awal untuk AI agent

Salin instruksi ini ke coding agent setelah mengekstrak paket dan menaruh dokumen di folder proyek. Sertakan diagram atau tautan lokal paket agar agent bisa membaca spesifikasi fisik.

```text
Bangun AI-FACE dari repo baru. Baca README.md serta 01 sampai 11.
Pertahankan dokumen sebagai spesifikasi dan catat setiap penyimpangan.

Untuk pekerjaan pertama, tuntaskan tahap A1 dan A2 dari dokumen 09.
Gunakan Python, OpenCV, dan paket resmi MediaPipe Face Landmarker.
Gunakan MediaPipe sebagai ekstraktor utama. Perlakukan StressID,
OpenFace dan Py-Feat sebagai referensi sesuai dokumen 10.
Jalankan tanpa bergantung pada dataset klinis atau UI web.

Implementasikan CLI dengan input kamera dan file video uji.
Tampilkan pratinjau kamera serta status kualitas tanpa audio.
Untuk sesi lengkap, jadwalkan 30 detik pada target 15 Hz dan hasilkan
450 slot unik. Simpan 52 blendshape dan 3 sudut pose dengan skema
berversi. Untuk slot yang tidak sah, simpan alasan dan fitur null.
Simpan ringkasan validitas dan satu artefak fitur per sesi.
Gunakan protokol uji seperti pada dokumen 02 dan diagram lampiran.
Untuk tahap awal, keluarkan estimation.status = not_available.

Buat fixture sintetis untuk penjadwalan dan ringkasan. Uji input
video lokal yang pengguna berikan atau gunakan kamera secara lokal.
Prioritaskan kasus frame terlewat, input gagal dan pembatalan.
Jangan mengasumsikan API atau angka performa perangkat.
Periksa dokumentasi resmi sebelum memasang versi pustaka.
Laporkan perintah setup dan run yang benar-benar digunakan,
hasil pengujian, file yang berubah, serta bagian yang masih
memerlukan verifikasi pada webcam atau perangkat target.

Lanjutkan FastAPI, PostgreSQL dan React setelah akuisisi stabil.
Jaga satu pemilik kamera saat tahap itu dimulai. Tunda label klinis,
pelatihan XGBoost pediatrik dan inferensi sampai data berizin dan
protokol labelnya tersedia. Jangan menghasilkan skor distress dummy.
```
