# Privasi dan tata kelola data penelitian

Data video wajah dan fitur turunan dikelola sebagai materi penelitian yang terlindungi. Pengembangan awal memakai data sintetis atau sumber uji berizin. Pengambilan data peserta mengikuti protokol, persetujuan etik, persetujuan/assent yang sesuai, cakupan izin dan kewenangan institusi. Rincian retensi dan hak akses ditetapkan tim sebelum rekrutmen.

| Area | Rancangan |
|---|---|
| Identitas | Gunakan kode samaran. Jika perlu ada tabel reidentifikasi, pisahkan dari data pipeline dengan akses terbatas. |
| Akuisisi | Audio mati. Pratinjau lokal dan sementara. Penyimpanan video mentah hanya jika diperlukan dan diizinkan secara khusus. |
| Akses | Operator, penilai, peneliti dan admin memiliki hak sesuai tugas. Uji akses pada sumber daya dan ekspor, termasuk setelah hak dicabut. |
| Penyimpanan | Gunakan penyimpanan lokal yang dikendalikan institusi dengan kontrol akses dan pencadangan terlindungi. Hindari foto, URL video, kode autentikasi dan identitas langsung di log. |
| Ekspor | Manifest mencatat versi, cakupan, aktor, waktu dan alasan. Ekspor riset mengikuti tujuan yang diizinkan. Data pasien tidak dijadikan fixture, disimpan di GitHub, atau dikirim ke layanan AI eksternal tanpa otorisasi yang sesuai. |
| Retensi dan pencabutan | Tetapkan waktu retensi per jenis data dan penanganan penghapusan, cadangan, ekspor sebelumnya dan model yang sudah dilatih sesuai protokol. Hentikan pengumpulan baru ketika izin tidak lagi berlaku. |
| Audit | Rekam tindakan mulai/batal, perubahan label atau izin, ekspor, akses administratif dan versi model. |

Alur pengembangan dan alur data peserta gunakan lingkungan terpisah. Selama pilot teknis, aplikasi menampilkan kualitas. Hasil penelitian model disimpan dengan konteksnya dan ditampilkan sesuai peran. [Pedoman etik CIOMS](https://www.who.int/docs/default-source/ethics/web-cioms-ethicalguidelines.pdf).
