# Dataset dan prosedur pengambilan sampel

## Unit data

- **Peserta** adalah unit independen utama. Semua sesi peserta mengikuti satu partisi penelitian.
- **Kunjungan** mengelompokkan sesi pada konteks pelayanan yang sama.
- **Sesi** adalah unit video 30 detik dan keluaran model. Satu sesi lengkap memiliki 450 posisi fitur nominal.
- **Asesmen** memberi skor rujukan. Jika satu asesmen berlaku bagi beberapa sesi pada kunjungan yang sama, kaitkan secara eksplisit sesuai protokol dan tangani ketergantungan saat analisis.

Contoh ilustratif. 30 anak × 2 sesi = 60 sesi dan 27.000 posisi waktu nominal. Pada satu sesi, 420 posisi valid dari 450 setara 93,3% validitas teknis. Itu tetap satu sesi berlabel, bukan 420 peserta atau label distress independen. Angka 30 bukan target rekrutmen.

## SOP pengumpulan

1. Setelah protokol disetujui, untuk populasi anak dan remaja 7–18 tahun yang menjalani terapi kanker, dokumentasikan kelayakan dan alur rekrutmen. Usulan awal adalah rekrutmen berurutan atas peserta yang memenuhi kriteria.
2. Catat izin sesuai protokol serta kesediaan anak. Buat kode peserta dan kunjungan. Anak bisa meminta sesi berhenti. Sesi yang ditunda, berhenti, gagal, atau tidak dapat dinilai perlu tercatat secara berkode sesuai protokol.
3. Standarkan kegiatan sesi awal. Tetapkan instruksi yang sama, cek pratinjau dan catat setup aktual. Jika ada sesi konsultasi, bicara, atau bermain, bedakan kode aktivitasnya. Simpan konteks yang disetujui seperti nyeri, kelelahan, dan waktu relatif terhadap terapi.
4. Rekam sesuai [pipeline](03_PIPELINE_AKUISISI.md). Pertahankan rekaman gagal pada rekap kepatuhan atau kualitas sesuai izin. Simpan video mentah hanya dalam alur berizin terpisah. Catat alasan pengulangan serta kaitannya ke sesi sebelumnya.
5. Penilai mencatat skor independen tanpa melihat prediksi. Catat versi instrumen, pihak yang mengisi, timestamp, rentang waktu yang dinilai, dan konteks label. Laporan anak dan wali merupakan entri terpisah.

## Label dan kebutuhan sampel

Tim klinis menetapkan instrumen, versi bahasa, rentang usia, interval antara rekaman dan asesmen, pihak penilai utama, dan ambang bila memakai klasifikasi. Bila instrumen merujuk beberapa hari terakhir, targetnya adalah skor atau status skrining pada kunjungan. Tetapkan aturan yang terdokumentasi untuk label kosong, asesmen ganda dan sesi di luar interval. Jangan menurunkan label dari prediksi AI atau menyebarkannya seolah tiap frame berlabel independen.

Pilot teknis mengukur kelayakan dan kegagalan. Ukuran pengembangan mempertimbangkan prevalensi target, jumlah fitur/predictor efektif dan data tak layak. Ukuran evaluasi ditentukan dari presisi yang dibutuhkan pada sensitivitas dan spesifisitas. Laporkan jumlah peserta, kunjungan, sesi, kelas, dan kegagalan berdasarkan kondisi. [Distress Thermometer pediatrik](https://pubmed.ncbi.nlm.nih.gov/34981598/) · [Riley et al. tentang ukuran sampel model](https://pubmed.ncbi.nlm.nih.gov/32188600/) · [Pedoman CIOMS](https://www.who.int/docs/default-source/ethics/web-cioms-ethicalguidelines.pdf).

Ekspor penelitian berisi manifest berkode dengan versi dataset, versi protokol, sesi, label rujukan, validitas, ID artefak dan partisi. Simpan manifest split terpisah serta laporkan perubahan dari versi terdahulu.
