# Panduan Indikator Klinis FACS dan Antarmuka AI-FACE

Dokumen ini menjelaskan secara rinci setiap teks, metrik, panel visual, serta landasan ilmiah di balik antarmuka **AI-FACE**, yang mengintegrasikan **Facial Action Coding System (FACS)**, skala klinis **DASS-3 (Depression, Anxiety, Stress)**, dan arsitektur pengenalan emosi **Fraunhofer SHORE** pada pasien onkologi.

---

## 1. Anatomi Antarmuka Visual (GUI Preview)

Antarmuka AI-FACE dirancang memiliki dua mode tampilan yang dapat dialihkan secara interaktif:
1. **Mode Klinis Murni (Default)**: Memfokuskan pengamatan pada parameter objektif medis (DASS-3 dan 31 FACS Action Units).
2. **Mode Ekspresi Lengkap**: Mengaktifkan visualisasi emosi dasar (*Happy, Sad, Angry, Surprised, Neutral*) dan *Radar Dial* polar emosi.

```
+-------------------------------------------------------------------------------+
| [ EKSPRESI: NONAKTIF (E) ]      ID: e665537b             DASS-3 CLINICAL (FACS) |
| (Tombol Interaktif Mode)       Uptime: 14.6s             DEP: Norm   0% [     ] |
|                                Distress: LOW             ANX: Mild  21% [==   ] |
|                                                          STR: Norm   0% [     ] |
|                                                                               |
|                                [ Tracking Wajah ]                             |
|                               [ Bounding Bracket ]                            |
|                                                                               |
|                                                                               |
|       +---------------------------------------------------------------+       |
|       |         FACS ACTION UNITS (MUSCULAR ACTIVITY LEVEL: 0-E)      |       |
|       | AU1  Inner Bro: [0] [    ]     | AU9  Nose Wrin: [0] [    ]   |       |
|       | AU2  Outer Bro: [B] [=== ]     | AU12 Lip Corne: [0] [    ]   |       |
|       | AU4  Brow Lowe: [0] [    ]     | AU15 Lip Depre: [0] [    ]   |       |
|       | AU5  Upper Lid: [0] [    ]     | AU20 Lip Stret: [0] [    ]   |       |
|       | AU6  Cheek Rai: [0] [    ]     | AU24 Lip Press: [0] [    ]   |       |
|       | AU7  Lid Tight: [A] [==  ]     | AU25 Lips Part: [0] [    ]   |       |
|       | AU45 Blink    : [A] [==  ]     | AU26 Jaw Drop : [0] [    ]   |       |
|       +---------------------------------------------------------------+       |
+-------------------------------------------------------------------------------+
```

---

## 2. Penjelasan Elemen dan Teks Antarmuka

### 2.1. Tombol Interaktif Mode (Pojok Kiri Atas)
* **`[ EKSPRESI: NONAKTIF (E) ]`** / **`[ EKSPRESI: AKTIF (E) ]`**
  * **Fungsi**: Memisahkan visualisasi emosi dasar dari panel klinis FACS.
  * **Cara Interaksi**:
    * **Klik Mouse**: Arahkan kursor dan klik langsung pada area tombol di jendela preview OpenCV.
    * **Hotkey Keyboard**: Tekan tombol **`'E'`** atau **`'e'`** pada keyboard.
  * **Perubahan Tampilan**:
    * Saat **NONAKTIF**: Menampilkan tabel FACS Action Units di bagian bawah layar. Radar dial dan bar emosi disembunyikan.
    * Saat **AKTIF**: Menampilkan *Radar Dial* di kiri atas dan panel grafik batang emosi (*Happy, Sad, Angry, Surprised, Neutral, Distress Index*) di bagian bawah.

---

### 2.2. Kotak Status Sesi & Subjek (Bagian Tengah Atas)
* **`ID: <8-karakter-uuid>`** (Contoh: `ID: e665537b`)
  * **Arti**: 8 karakter pertama dari *Session UUIDv4* unik.
  * **Prinsip Privasi Medis**: Digunakan untuk mencatat data sesi secara pseudonim (anonim) tanpa menyimpan identitas langsung pasien (Nama, NIK, Rekam Medis) pada file komputasi wajah.
* **`Uptime: <detik>s`** (Contoh: `Uptime: 14.6s`)
  * **Arti**: Durasi akuisisi data yang sedang berjalan dari target sesi nominal 30.0 detik.
* **`Distress: LOW / MODERATE / HIGH`**
  * **Arti**: Indikator tingkat stres emosional global pasien saat ini.
  * **Kategori**:
    * `LOW` (Hijau): Kondisi tenang, stabil, dan rileks.
    * `MODERATE` (Kuning/Oranye): Terindikasi adanya ketegangan psikologis atau beban kognitif sedang.
    * `HIGH` (Merah): Indikasi stres tinggi atau ketidaknyamanan akut.

---

### 2.3. Panel Penilaian Klinis DASS-3 (Pojok Kanan Atas)
Mengadopsi metodologi riset **Gavrilescu & Vizireanu (Sensors 2019)**: *"Predicting Depression, Anxiety, and Stress Levels from Videos Using the Facial Action Coding System"*.

* **`DASS-3 CLINICAL (FACS)`**:
  Modul asesmen klinis yang mengonversi aktivasi 31 Action Units FACS ke skala psikometri **DASS (Depression Anxiety Stress Scales)**.

* **`DEP` (Depression / Depresi)**:
  * **Definisi Klinis**: Mengukur hilangnya inisiatif, disforia, keputusasaan, dan kelesuan tonus motorik wajah.
  * **Korelasi Otot FACS**:
    * **AU15** (*Lip Corner Depressor* / Otot *Depressor anguli oris*): Sudut bibir tertarik ke bawah.
    * **AU6** (*Cheek Raiser*): Kehilangan tonus pipi.
    * **AU26** (*Jaw Drop*): Mulut mengendur pasif.
    * **AU12** (*Lip Corner Puller*): Penurunan frekuensi senyum.

* **`ANX` (Anxiety / Kecemasan)**:
  * **Definisi Klinis**: Mengukur respons otonom, kekhawatiran antisipatif, ketakutan situasional, dan hiper-kewaspadaan visual.
  * **Korelasi Otot FACS**:
    * **AU2** (*Outer Brow Raiser* / Otot *Frontalis pars lateralis*): Pengangkatan alis bagian luar saat mata membelalak waspada.
    * **AU5** (*Upper Lid Raiser*): Pembesaran celah kelopak mata.
    * **AU7** (*Lid Tightener*): Pengetatan kelopak mata bawah.
    * **AU45** (*Blink Frequency*): Peningkatan frekuensi kedipan mata.
    * **AU9** (*Nose Wrinkler*) & **AU20** (*Lip Stretcher*): Ketegangan area tengah wajah.

* **`STR` (Stress / Ketegangan Mental & Fisik)**:
  * **Definisi Klinis**: Mengukur ketegangan kognitif, kelelahan, kesulitan rileks, iritabilitas, dan reaksi terhadap beban tekanan.
  * **Korelasi Otot FACS**:
    * **AU1** (*Inner Brow Raiser* / Otot *Frontalis pars medialis*): Kerutan vertikal di tengah dahi.
    * **AU4** (*Brow Lowerer* / Otot *Corrugator supercilii*): Penurunan dan penyatuan kedua alis (alis berkerut).
    * **AU24** (*Lip Pressor* / Otot *Orbicularis oris*): Penekanan bibir atas dan bawah secara rapat.

#### Tabel 5 Tingkat Keparahan Klinis DASS-3:
| Rentang Skor | Level DASS-3 | Indikasi Klinis | Warna Display |
| :---: | :---: | :--- | :---: |
| **$0.00 - 0.15$** | **Normal** | Kondisi emosional stabil, rileks, bebas tekanan patologis. | Hijau |
| **$0.15 - 0.30$** | **Mild** | Ketegangan ringan wajar (misal: adaptasi di depan kamera). | Teal / Cyan |
| **$0.30 - 0.60$** | **Moderate** | Ketegangan sedang, teramati kontraksi otot wajah berulang. | Oranye / Amber |
| **$0.60 - 0.80$** | **Severe** | Ketegangan berat, kontraksi otot signifikan berkelanjutan. | Oranye Tua |
| **$\ge 0.80$** | **Extremely Severe** | Indikasi distres akut / depresi berat (*clinical override*). | Merah Crimson |

---

### 2.4. Panel Rincian FACS Action Units (Bagian Bawah Layar)
Menampilkan kontraksi otot wajah mikro berdasarkan standar ilmiah **Facial Action Coding System (FACS)** yang dikembangkan oleh Paul Ekman dan Wallace V. Friesen.

#### Sistem Skala Intensitas Diskrit FACS (6 Tingkatan):
* **`[0]` (Absence)**: Otot wajah berada dalam posisi istirahat sempurna (netral).
* **`[A]` (Trace)**: Jejak kontraksi sangat halus, nyaris tidak kasat mata oleh mata telanjang namun terukur oleh Face Mesh 3D.
* **`[B]` (Slight)**: Kontraksi ringan yang mulai terlihat jelas.
* **`[C]` (Marked)**: Kontraksi sedang dengan deformasi kontur wajah yang tegas.
* **`[D]` (Severe)**: Kontraksi otot kuat dan nyata.
* **`[E]` (Maximum)**: Kontraksi otot maksimal (pergerakan batas anatomis ekstrem).

#### Rincian Action Units Utama yang Ditampilkan:

| Kode AU | Nama Aksi FACS | Otot Utama (*Musculus*) | Arti & Fungsi Klinis |
| :--- | :--- | :--- | :--- |
| **AU1** | *Inner Brow Raiser* | *Frontalis, pars medialis* | Alis bagian dalam terangkat (ekspresi sedih, rasa sakit, duka). |
| **AU2** | *Outer Brow Raiser* | *Frontalis, pars lateralis* | Alis bagian luar terangkat (atensi visual, waspada, cemas). |
| **AU4** | *Brow Lowerer* | *Corrugator supercilii, Depressor supercilii* | Alis ditarik turun dan menyatu (konsentrasi, stres, nyeri, marah). |
| **AU5** | *Upper Lid Raiser* | *Levator palpebrae superioris* | Kelopak mata atas membesar (terkejut, waspada, takut). |
| **AU6** | *Cheek Raiser* | *Orbicularis oculi, pars orbitalis* | Pipi terangkat, mata menyempit (senyum tulus *Duchenne*). |
| **AU7** | *Lid Tightener* | *Orbicularis oculi, pars palpebralis* | Kelopak mata menyempit tegang (menahan nyeri, silau, fokus). |
| **AU45** | *Blink* | *Orbicularis oculi* | Kedipan mata (meningkat saat cemas atau lelah). |
| **AU9** | *Nose Wrinkler* | *Levator labii superioris alaeque nasi* | Pangkal hidung berkerut (nyeri tajam, tidak suka, mual). |
| **AU12** | *Lip Corner Puller* | *Zygomaticus major* | Sudut bibir ditarik ke atas lateral (senyum, emosi positif). |
| **AU15** | *Lip Corner Depressor*| *Depressor anguli oris* | Sudut bibir turun ke bawah (kecewa, murung, sedih, depresi). |
| **AU20** | *Lip Stretcher* | *Risorius, Platysma* | Sudut bibir ditarik mendatar ke samping (panik, ketakutan). |
| **AU24** | *Lip Pressor* | *Orbicularis oris* | Kedua bibir ditekan rapat mengeras (menahan rasa sakit/stres). |
| **AU25** | *Lips Part* | *Depressor labii inferioris, Orbicularis oris*| Pemisahan bibir atas dan bawah tanpa rahang terbuka. |
| **AU26** | *Jaw Drop* | *Masseter rileks, Digastricus* | Rahang bawah turun pasif (kelelahan mental, mulut mengendur). |

---

## 3. Relevansi pada Pasien Kanker & Onkologi (Studi Binz et al., 2023)

Berdasarkan penelitian di ruang tunggu klinik onkologi rawat jalan *Johanniter Hospital Bonn* (Binz et al., 2023: *"Machine-based emotion-assessment in waiting rooms – a feasibility and acceptance study"*):

1. **Mayoritas Berstatus Netral / Tenang**:
   * Sebanyak **78% pasien onkologi adalah kelompok usia lanjut** (lansia).
   * Pada saat menunggu pemeriksaan atau kemoterapi, lebih dari **50% pasien melaporkan kondisi pikiran "normal", "netral", atau "lelah/tenang"**, bukan emosi bahagia atau marah ekstrem.
   * Hal ini menjelaskan mengapa panel AI-FACE secara konsisten menampilkan skor **Neutral tinggi ($70\% - 90\%$)** dan distres **LOW** pada subjek yang sedang beristirahat santai.
2. **Pengaruh Kerutan Statis Wajah pada Lansia**:
   * Pasien lanjut usia memiliki kerutan alami permanen di sekitar dahi (*AU4*) atau sudut mata (*AU6*/*AU7*).
   * Algoritma AI-FACE mengombinasikan Action Units dengan perhitungan *Valence* afektif dan baseline netral agar kerutan statis usia tidak disalahartikan sebagai kemarahan atau distres akut palsu (*false positive*).

---

## 4. Cara Penggunaan Praktis

### Menjalankan Mode Klinis Murni (Rekomendasi Riset Medis)
```powershell
ai-face --camera-index 0
```
Tampilan akan langsung berada pada mode klinis dengan rincian DASS-3 dan FACS Action Units.

### Mengaktifkan Mode Ekspresi
* Tekan tombol **`'E'`** pada keyboard saat preview aktif, atau
* Klik kotak **`[ EKSPRESI: NONAKTIF (E) ]`** pada layar menggunakan mouse.
* Anda juga dapat memulai langsung dalam mode ekspresi melalui parameter:
  ```powershell
  ai-face --camera-index 0 --show-emotions
  ```

### Menganalisis Foto Pasien & Rekap CSV
```powershell
# Analisis satu foto pasien
ai-face --image path/to/foto_pasien.jpg --output-dir output/hasil_pasien

# Analisis satu folder foto pasien (menghasilkan tabel CSV)
ai-face --image-dir path/to/folder_foto/ --output-dir output/rekap_batch
```
File `batch_dass_summary.csv` yang dihasilkan di folder output dapat langsung diimpor ke **Microsoft Excel**, **SPSS**, atau **Google Sheets** untuk keperluan tabulasi data penelitian medis.
