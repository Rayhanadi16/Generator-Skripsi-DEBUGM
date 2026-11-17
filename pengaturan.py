"""
Mode aplikasi.

- "web"   : dipakai banyak orang lewat internet. Tidak ada yang ditulis ke disk server;
            isian hanya hidup di tab browser masing-masing pengunjung dan dibawa pulang
            lewat tombol "Simpan progres (.json)".
- "lokal" : dipakai sendiri di komputer. Autosave dan riwayat versi aktif (folder autosave/).

Bawaan folder ini adalah "web". Untuk menjalankan di komputer sendiri dengan autosave:
    GENERATOR_MODE=lokal streamlit run app.py --server.address localhost
"""

import os

MODE = os.environ.get("GENERATOR_MODE", "web").strip().lower()
MODE_WEB = MODE != "lokal"

# Buku panduan penggunaan (PDF) di Google Drive, dibuka oleh tombol "Cara Pakai".
# Bila isi panduan diperbarui, ganti versinya di Drive (Kelola versi) supaya link ini tetap sama.
# Kosongkan untuk menyembunyikan tombolnya.
LINK_PANDUAN = "https://drive.google.com/file/d/1vsR16_N3ub67RuuH1B5p0CgC4WRKdONF/view?usp=sharing"
