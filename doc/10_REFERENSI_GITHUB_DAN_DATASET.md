# Referensi GitHub, dataset dan literatur

| Sumber | Cara digunakan dalam AI-FACE | Validasi sebelum mengambil kode atau data |
|---|---|---|
| [MediaPipe](https://github.com/google-ai-edge/mediapipe) · [Face Landmarker Python](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker?tab=Python) | Ekstraktor utama landmark, blendshape dan matriks untuk pose. Gunakan paket resmi. | Catat versi paket, checksum model dan kondisi uji. Uji kompatibilitas perangkat dan timing. |
| [StressID](https://github.com/robustml-eurecom/stressID) | Referensi metode pengembangan pipeline video dan benchmark stres eksperimen. | Telaah [lisensi dataset](https://project.inria.fr/stressid/files/2025/02/License_StressID_Academic_final.pdf), akses, label dan protokol. Catat commit jika menggunakan kode. |
| [OpenFace 2.0](https://github.com/TadasBaltrusaitis/OpenFace) | Pembanding offline untuk Facial Action Units dan pose. | Tinjau [lisensi OpenFace](https://github.com/TadasBaltrusaitis/OpenFace/blob/master/model_training/OpenFace-license.txt) dan izin bobot. |
| [Py-Feat](https://github.com/cosanlab/py-feat) | Alternatif pembanding offline untuk AU dan ekspresi. | Periksa lisensi kode, model, dan performa pada perangkat. Gunakan salah satu pembanding dulu. |
| [MAS Dataset](https://github.com/ScazLab/MAS_dataset) | Referensi desain multimodal apabila fase riset memerlukannya. | Review relevansi audio, teks dan gerakan tubuh. MVP mengikuti rancangan wajah dengan audio mati. |
| [Geek-ubaid Stress-Detection](https://github.com/Geek-ubaid/Stress-Detection) | Referensi alur pratinjau saja. | Skor berbasis posisi alis pada demo tidak menjadi acuan klinis atau fitur penilaian produk. |
| [UBFC-Phys](https://imvia.ube.fr/ubfc-phys/) | Pembanding eksperimen aktivitas dan pergeseran domain. | Periksa apakah model menangkap aktivitas, seperti gerakan berbicara. |
| [CAFE](https://databrary.org/volume/30) | Pemeriksaan teknis deteksi wajah pada foto ekspresi anak jika akses diizinkan. | Periksa izin akses dan penggunaan. Foto ekspresi diperagakan berbeda dari label distress. |

Buat repo AI-FACE sendiri. Pada setiap komponen pihak ketiga yang dipakai, catat sumber, rilis atau commit, lisensi kode, lisensi bobot atau data, dan perubahan lokal. Dataset lokal yang berizin dengan asesmen rujukan independen menjadi dasar evaluasi target pediatrik.

Literatur inti. [Chen et al.](https://doi.org/10.1188/21.ONF.81-93) · [Distress Thermometer pediatrik](https://pubmed.ncbi.nlm.nih.gov/34981598/) · [Riley et al.](https://pubmed.ncbi.nlm.nih.gov/32188600/).
