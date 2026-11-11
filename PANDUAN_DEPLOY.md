# Cara meng-online-kan Generator Laporan TA

Panduan ini memakai GitHub (tempat menaruh kode) dan Streamlit Community Cloud (hosting gratis).
Nama tombol di kedua situs bisa berubah sewaktu-waktu; kalau ada yang berbeda, ikuti yang tertera di layar.

## 1. Buat repository di GitHub

1. Login di https://github.com.
2. Klik tanda **+** di kanan atas, pilih **New repository**.
3. Isi nama, misalnya `generator-skripsi`. Pilih **Public** atau **Private** (dua-duanya bisa dipakai).
4. Klik **Create repository**.

## 2. Unggah file

1. Di Finder, **buka** folder `generator-skripsi` ini, lalu tekan **Cmd + Shift + titik** supaya folder
   tersembunyi `.streamlit` dan file `.gitignore` terlihat.
2. Di halaman repository yang baru, klik **uploading an existing file**.
3. Pilih **semua isi** folder (Cmd + A), lalu seret ke halaman GitHub. Yang diseret adalah isinya,
   bukan foldernya, supaya `app.py` dan `.streamlit` berada langsung di halaman depan repository.
4. Klik **Commit changes**.

Periksa hasilnya: di halaman depan repository harus langsung terlihat `app.py`, `requirements.txt`,
dan folder `.streamlit`. Jangan pernah mengunggah folder `autosave` (isinya pekerjaan pribadimu).

## 3. Deploy di Streamlit Community Cloud

1. Buka https://share.streamlit.io dan masuk dengan akun GitHub-mu. Setujui permintaan izinnya.
2. Klik **Create app**, pilih opsi memakai aplikasi dari repository GitHub yang sudah ada.
3. Isi:
   - Repository: `namamu/generator-skripsi`
   - Branch: `main`
   - Main file path: `app.py`
4. Bila mau, ganti alamatnya (App URL) menjadi sesuatu yang mudah diingat.
5. Klik **Deploy** dan tunggu beberapa menit. Setelah selesai kamu mendapat alamat berakhiran
   `.streamlit.app` yang bisa dibagikan.

## 4. Coba sebelum dibagikan

- Klik **Isi dengan data contoh**, cek tab **Preview**, lalu **Buat file Word** dan buka hasilnya di Word.
- Buka alamatnya di jendela penyamaran (incognito): form harus kosong, tidak berisi isian dari jendela pertama.
- Coba **Simpan progres (.json)**, tutup tab, buka lagi, lalu **Muat file progres**.

## 5. Memperbarui aplikasi

Unggah file yang berubah ke repository yang sama (tombol **Add file**, lalu **Upload files**), kemudian
**Commit changes**. Website-nya ikut diperbarui sendiri dalam beberapa menit.

## Yang perlu kamu tahu

- **Isian pengunjung tidak disimpan.** Semua hanya hidup di tab browser masing-masing. Kalau tab ditutup,
  dimuat ulang, atau lama tidak dipakai, isian hilang; karena itu ada pengingat untuk menyimpan progres
  dan browser bertanya dulu sebelum tab ditutup.
- **Aplikasi bisa "tidur"** kalau lama tidak dikunjungi. Pengunjung berikutnya perlu menunggu sebentar
  sampai aplikasi bangun lagi.
- **Kapasitas hosting gratis terbatas.** Kalau banyak orang memakai bersamaan dan mengunggah banyak gambar,
  aplikasi bisa lambat atau memulai ulang (isian yang belum disimpan hilang). Batas unggah diatur 20 MB
  per file di `.streamlit/config.toml`.
- **Server berada di luar negeri** dan draft yang diunggah diproses di sana selama sesi berjalan. Keterangan
  untuk pengunjung ada di sisi kiri aplikasi, bagian **Tentang data kamu**; teksnya bisa kamu ubah di
  `tampilan.py` (variabel `TENTANG_DATA`).
