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
