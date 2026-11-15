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
