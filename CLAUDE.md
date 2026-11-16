# Generator Laporan Tugas Akhir

Aplikasi Streamlit yang menyusun laporan TA menjadi file Word (.docx) sesuai Panduan Penulisan Tugas Akhir 2025, DEB Sekolah Vokasi UGM.

## Arsitektur

| File | Peran |
|---|---|
| `app.py` | Antarmuka. Semua isian hidup di `st.session_state` dengan kunci datar (`id_*`, `pg_*`, `bab{i}_s{j}_isi`, `mg_*`). |
| `generator.py` | Mesin pembuat .docx (`PembangunTA`) dan semua angka format (`FORMAT_DEB_SV_UGM`). |
| `preview.py` | `kerangka()` untuk ringkasan dan daftar cek, `halaman_html()` untuk tiruan lembar A4. |
| `importer.py` | Membaca draft .docx mentah dan menebak tujuan tiap paragraf. |
| `pustaka.py` | Mencari DOI di PDF, mengambil data Crossref, menyusun entri APA 7. |
| `tampilan.py` | CSS (mode terang dan gelap) dan potongan HTML kecil. |
| `simpan_browser.py` | Simpan otomatis mode web lewat IndexedDB di browser pengunjung. |
| `autosave.py` | Simpan otomatis dan riwayat versi mode lokal (folder `autosave/`). |
| `pengaturan.py` | `MODE_WEB`, dari variabel lingkungan `GENERATOR_MODE`. |

Alur data: `kumpulkan_data()` di `app.py` mengubah isian menjadi satu dict, yang dibaca `generator.buat_dokumen()` dan `preview.kerangka()`. `muat_data()` adalah kebalikannya.

## Navigasi dan jaga_isian()

Antarmuka dibagi empat tahap (`TAHAP` dan `TAB_TAHAP` di `app.py`): Isi laporan, Bahan pendukung, Periksa, Buat file. Tiap tab adalah satu fungsi `tampil_*()`, dan hanya fungsi milik tahap aktif yang dipanggil. Tahap aktif ada di `ss["tahap"]` (kunci `"isi"`, `"bahan"`, `"periksa"`, `"buat"`) dan ikut tersimpan di alamat halaman.

Streamlit menghapus nilai widget yang tidak dirender dalam satu putaran. Karena itu `jaga_isian()` dipanggil di awal setiap putaran, sebelum widget apa pun dibuat, untuk menyalin setiap kunci isian ke dirinya sendiri. Widget baru yang nilainya harus bertahan antartahap wajib punya kunci berawalan yang dikenali `jaga_isian()`, atau didaftarkan di sana. Nilai `file_uploader` tidak bisa dijaga dengan cara itu, jadi `jaga_unggahan()` menyalin gambar dan logo ke `ss["_gambar_simpan"]` dan `ss["_logo_simpan"]`. Uji di `tests/test_navigasi.py` gagal bila salah satunya dilepas.

Di uji AppTest, pindah tahap dengan `ke_tahap(at, "bahan")` dari `tests/conftest.py`.

Isi subbab adalah teks biasa dengan penanda: `### Judul`, `[[GAMBAR: file | Judul | Sumber | lebar_cm]]`, `[[TABEL: Judul | Sumber]] ... [[/TABEL]]`, `[[RUMUS: ...]]`. Penanda diurai di dua tempat yang harus selalu sama: `generator._isi_subbab()` dan `preview.uraikan_isi()`.

## Aturan

- Format mengikuti Panduan TA 2025 DEB SV UGM. Angkanya hanya ada di `FORMAT_DEB_SV_UGM`.
- Semua teks antarmuka berbahasa Indonesia yang santai tapi rapi, tanpa em dash dan tanpa emoji.
- Nama fungsi dan variabel berbahasa Indonesia, mengikuti kode yang sudah ada.
- Mode web tidak boleh menyimpan apa pun di server. File sementara harus dihapus setelah dipakai.
- Kunci widget tidak boleh diubah setelah widgetnya dibuat dalam satu putaran. Ubah lewat callback `on_click`, atau sebelum widget dibuat.
- Pesan singkat ke pengguna lewat `ss["_pesan"] = (jenis, teks)`, yang ditampilkan sebagai toast.

## Menjalankan

```bash
streamlit run app.py
```

Mode lokal dengan autosave ke disk:

```bash
GENERATOR_MODE=lokal streamlit run app.py --server.address localhost
```

`tampilan.py` dan modul lain yang diimpor tidak selalu dimuat ulang oleh Streamlit yang sedang berjalan. Mulai ulang server setelah mengubahnya.

## Uji

```bash
pytest
```

Logika diuji dengan pytest biasa. Antarmuka diuji tanpa browser memakai `streamlit.testing.v1.AppTest` (lihat `tests/test_dasar.py`).

## Setiap fitur baru

Wajib menambah satu entri di paling atas `PEMBARUAN` dalam `pembaruan.py` (versi dinaikkan, `VERSI` ikut otomatis), dengan poin dalam bahasa pengunjung. Tambahkan juga baris file barunya ke tabel di README.md.

## Penanda dan rujukan silang

`rujukan.siapkan()` dipanggil sebelum isi subbab diurai, di `generator.bab()`, `preview.kerangka()`, dan `PreviewHTML.bab()`. Fungsi itu mengganti `[[REF: #label]]` dan melepas label dari penanda, jadi pengurai penanda tidak perlu tahu soal label. Penomoran di `rujukan.peta_label()` harus tetap sama dengan penghitung di `generator.bab()`; `tests/test_rujukan.py` menjaganya, termasuk uji bahwa data contoh menghasilkan teks dokumen yang sama dengan `tests/data/dokumen_contoh_sebelum_rujukan.txt`.

## Periksa tulisan

`periksa_tulisan.py` mencari kata tidak baku dari `data/kata_tidak_baku.csv`. Baris bercatatan `ragu` sengaja tidak dimuat. `kata_diperiksa()` adalah satu-satunya tempat yang menentukan bagian teks mana yang dilewati (penanda, kutipan, teks miring), dan dipakai baik untuk mencari maupun untuk mengganti, supaya keduanya selalu sepakat. Daftar abaikan ada di `ss["abaikan_kata"]` dan ikut `kumpulkan_data()`/`muat_data()`; file progres lama tanpa kunci itu harus tetap termuat.

`periksa_ejaan()` mencari kemungkinan typo dan istilah asing dengan kamus Hunspell di `kamus/` (dibaca `spylls`, dimuat sekali per proses). Pencocokan di-cache per kata (`dikenal_id`, `dikenal_en`), jadi cepat; yang lambat hanya `saran_ejaan()`, maka saran hanya dihitung untuk temuan yang sedang ditampilkan dan typo ditampilkan bertahap. Risiko utamanya salah tunjuk: sebelum melonggarkan atau mengetatkan aturan di `dikenal_id()`, jalankan `tests/test_cek_ejaan.py`, yang memuat daftar kata benar yang tidak boleh ditandai dan daftar typo umum yang tidak boleh lolos. File di `kamus/` tidak diubah; istilah tambahan masuk ke `data/istilah_dikenal.txt`.
