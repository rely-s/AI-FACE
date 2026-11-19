# Pelatihan dan evaluasi model

## Tahap awal

Gunakan video uji berizin untuk validasi teknis, lalu StressID bila akses dan lisensinya sesuai untuk eksperimen stres terkontrol. Dataset penelitian pediatrik berlabel independen diperlukan untuk menguji kemampuan pada target AI-FACE. Gunakan versi data dan tujuan yang jelas agar hasil StressID tidak disamakan dengan hasil skrining pediatrik.

## Pipeline offline

1. Bekukan target, unit prediksi, aturan mutu, dan definisi label sebelum pengujian. Pilih klasifikasi jika ada ambang tervalidasi untuk protokol lokal. Pelajari regresi hanya jika skor numerik menjadi luaran yang disepakati.
2. Partisi berdasarkan peserta sebelum fitting. Kelompokkan seluruh kunjungan, sesi, frame, dan turunan dari peserta yang sama. Bila peserta terbatas, gunakan validasi silang berbasis grup untuk pengembangan dan rencanakan uji independen setelah data memungkinkan. Fitting, pemilihan fitur, normalisasi, kalibrasi dan pemilihan ambang terjadi di data pengembangan saja.
3. Ringkas fitur valid setiap sesi dengan median, rentang antarkuartil dan perubahan antar-slot yang benar-benar bertetangga. Dokumentasikan perlakuan atas kehilangan data. Bandingkan hasil dengan dan tanpa fitur yang berkaitan dengan kualitas untuk mengecek jalan pintas model.
4. Gunakan baseline prevalensi, foto + HOG/SVM sebagai pembanding literatur, dan XGBoost pada statistik gerakan 30 detik. Bandingkan model konteks saja, wajah saja, dan wajah + konteks pada partisi yang sama bila variabel tersedia. Pertimbangkan TCN atau EfficientNet-B0 setelah baseline terukur.
5. Simpan prediksi uji per sesi dan laporkan sensitivitas, spesifisitas, AUROC, AUPRC dan kalibrasi untuk klasifikasi, serta proporsi sesi yang memperoleh estimasi. Untuk regresi, gunakan galat skor seperti MAE. Sertakan ketidakpastian dengan resampling pada tingkat peserta bila sesi berulang.
6. Telusuri hasil menurut kelompok usia, aktivitas, kondisi perangkat, dan pola kegagalan jika ukuran kelompok memadai. Laporkan jumlah peserta dan sesi yang masuk/ditahan. Periksa apakah gerakan bibir atau konteks perekaman menjadi proksi yang tidak diinginkan.

Registri model memuat versi model, checksum, versi data, split, skema fitur, protokol, target, ambang, metrik, dan status persetujuan. Ketidakcocokan skema atau konteks membuat keluaran ditahan. [Pembanding Chen et al.](https://doi.org/10.1188/21.ONF.81-93).
