# Pipeline akuisisi dan ekstraksi fitur

## Kontrak proses

1. Buka sumber frame kamera atau video uji. Pada mode kamera, baca resolusi dan laju aktual. Gunakan jam monotonik untuk penjadwalan dan UTC untuk metadata sesi. Pada mode video uji, gunakan timestamp sumber yang meningkat.
2. Mulai dari `t0` dan jadwalkan indeks `i = 0..449` pada `t0 + i/15` detik dalam interval setengah terbuka `[t0, t0+30s)`. Untuk satu slot, gunakan maksimum satu frame baru dalam interval slot. Tolak frame lama atau yang sudah dipakai. Jika pengolahan tertinggal, tandai slot terlewat, lalu lanjut ke slot yang relevan. Hindari menumpuk antrean frame lama.
3. Untuk MVP gunakan MediaPipe Face Landmarker mode VIDEO dengan timestamp milidetik meningkat dan aktifkan keluaran blendshape serta matriks transformasi. Pakai satu hasil wajah untuk ekstraksi. Jika protokol perlu memastikan tepat satu wajah, gunakan pemeriksaan jumlah wajah yang terpisah atau konfigurasi deteksi yang bisa mengamati lebih dari satu. Pada mode LIVE_STREAM yang diuji kemudian, kaitkan callback dengan timestamp input karena frame bisa terlewat saat pemroses sibuk.
4. Bangun satu rekaman per slot. Simpan 52 blendshape dengan nama dan urutan yang dibekukan oleh versi skema. Jabarkan konvensi yaw, pitch, dan roll, urutan rotasi, satuan derajat, dan perlakuan terhadap pratinjau yang dicerminkan. Uji arah putar dengan fixture sebelum fitur pose dipakai dalam pelatihan.
5. Jalankan pemeriksaan kualitas. Simpan slot tidak valid dengan fitur kosong serta alasan. Akhiri tepat setelah 30 detik dan tampilkan statistik kualitas sesi.

## Skema rekaman

| Kunci | Bentuk |
|---|---|
| `schema_version`, `session_id`, `slot_index` | Versi skema, UUID, integer 0–449 |
| `target_ms`, `frame_ms` | Waktu relatif slot dan waktu frame, nullable untuk frame yang hilang |
| `valid`, `reasons` | Boolean dan daftar kode kesalahan |
| `blendshapes` | Objek 52 nama dengan nilai numerik hingga, atau null |
| `pose_deg` | Objek `yaw, pitch, roll` atau null |

Kode kualitas awal `NO_FACE`, `MULTIPLE_FACES`, `FRAME_MISSED`, `FACE_OUT_OF_FRAME`, `LOW_LIGHT`, `OVEREXPOSED`, `BLUR`, `POSE_OUT_OF_RANGE`, `FEATURE_INVALID`. Definisi dan ambang bernilai konfigurasi berversi, ditentukan dari pilot. Dahulukan penanganan tanpa wajah, frame terlewat, dan validitas vektor. Aktifkan pemeriksaan yang sudah dapat diuji.

Simpan data sesi penuh dalam JSONL atau Parquet dengan skema tetap. Laporkan proporsi valid sebagai `valid_slots / 450` untuk sesi lengkap dan tampilkan laju efektif `valid_slots / duration_actual_s`. Untuk sesi batal, simpan status batal secara terpisah dari sesi selesai yang tidak memenuhi kualitas. Ambang kualitas baru menjadi syarat penilaian setelah ditetapkan dari uji yang terdokumentasi.

Jika pekerja gagal atau proses restart, tandai sesi aktif gagal saat rekonsiliasi. File sementara tidak boleh dibaca sebagai artefak lengkap. Gunakan [kontrak penyimpanan](05_ERD_DAN_DATABASE.md).
