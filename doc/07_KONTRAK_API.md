# Kontrak API dan integrasi

Prefiks `/api/v1`. FastAPI memvalidasi skema, peran, dan akses tingkat sumber daya. Gunakan UTC ISO 8601 untuk timestamp tercatat serta durasi relatif dalam milidetik. Respons error memiliki `error.code`, `error.message`, dan `request_id`.

| Metode dan rute | Peran | Tujuan |
|---|---|---|
| GET `/health` | Lokal | Kesehatan layanan tanpa data penelitian |
| GET `/devices/{id}/status` | Operator | Status perangkat, mode aktual, ketersediaan kamera |
| GET `/devices/{id}/preview` | Operator | Stream MJPEG lokal dari pekerja yang sama, hanya pada konteks operator yang sah |
| POST `/sessions` | Operator | Buat sesi `ready` dari kunjungan, perangkat, versi protokol, izin, dan setup |
| POST `/sessions/{id}/start` | Operator | Mulai akuisisi jika status `ready` dan perangkat bebas |
| POST `/sessions/{id}/cancel` | Operator | Hentikan akuisisi, tandai `cancelled` jika masih dapat dihentikan |
| GET `/sessions/{id}` | Peran terkait | Status, progres, ringkasan kualitas, status estimasi sesuai hak akses |
| POST `/visits/{id}/assessments` | Penilai | Buat label independen dengan cakupan kunjungan |
| PUT `/sessions/{id}/assessments/{assessment_id}` | Penilai | Kaitkan asesmen yang sah sesuai protokol |
| POST `/exports` | Peneliti | Buat ekspor terotorisasi berdasarkan versi dataset dan filter |

Gunakan polling status sekitar satu kali per detik untuk MVP. Kamera melanjutkan sesi secara lokal bila koneksi UI terputus. UI memuat ulang status sebelum memulai sesi baru. Sesi perekaman menjadi `processing` setelah 30 detik dan otomatis difinalisasi setelah artefak berhasil disimpan. Pratinjau tidak ditulis ke log atau cache bersama.

Contoh hasil teknis fiktif dari GET sesi.

```json
{
  "session_id": "2c9be646-3c28-4acb-8a87-2a9f632c40c2",
  "status": "completed",
  "protocol_version": "pilot-v1",
  "duration_target_ms": 30000,
  "quality": {"status": "pass", "expected_slots": 450, "valid_slots": 420, "valid_ratio": 0.9333},
  "estimation": {"status": "not_available"}
}
```

`pass` di contoh mengasumsikan ambang sudah dikonfigurasi. Catat penolakan dan gunakan `409` untuk perangkat sibuk/transisi tidak sah, `422` untuk payload atau aturan data tidak valid, `403` untuk akses ditolak, dan `503` untuk perangkat atau penyimpanan tidak tersedia. POST pembuatan sesi, start, cancel, asesmen dan ekspor menerima idempotency key. Kunci yang sama dengan payload sama mengembalikan hasil sebelumnya. Payload yang berbeda untuk kunci yang sama ditolak. Untuk ekspor asinkron, kembalikan ID pekerjaan dan otorisasi ulang unduh. Jangan menerima path lokal mentah dari klien.
