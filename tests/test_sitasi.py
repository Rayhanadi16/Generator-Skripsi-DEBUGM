import pytest

import sitasi


def _satu(teks):
    hasil = sitasi.cari_kutipan(teks)
    assert len(hasil) == 1, hasil
    return hasil[0]["nama"], hasil[0]["tahun"]


@pytest.mark.parametrize("teks, nama, tahun", [
    ("Literasi keuangan penting (Santoso, 2021).", "Santoso", "2021"),
    ("Hal ini sejalan (Santoso & Putri, 2021).", "Santoso", "2021"),
    ("Santoso dan Putri (2021) menemukan hal serupa.", "Santoso", "2021"),
    ("Temuan lain (Santoso et al., 2021) berbeda.", "Santoso", "2021"),
    ("Santoso dkk. (2021) menyatakan sebaliknya.", "Santoso", "2021"),
    ("Dikutip langsung (Santoso, 2021, hlm. 5).", "Santoso", "2021"),
    ("Dua terbitan setahun (Santoso, 2021a).", "Santoso", "2021a"),
    ("Menurut bank sentral (Bank Indonesia, 2023).", "Bank Indonesia", "2023"),
    ("Data kependudukan (BPS, 2023).", "BPS", "2023"),
    ("Sumber tanpa tahun (Santoso, t.t.).", "Santoso", "t.t."),
    ("Sumber tanpa tahun (Santoso, n.d.).", "Santoso", "n.d."),
    ("Bank Indonesia (2023) menaikkan suku bunga.", "Bank Indonesia", "2023"),
])
def test_bentuk_kutipan(teks, nama, tahun):
    assert _satu(teks) == (nama, tahun)


def test_kutipan_ganda():
    hasil = sitasi.cari_kutipan("Didukung banyak studi (Santoso, 2021; Putri, 2020).")
    assert [(k["nama"], k["tahun"]) for k in hasil] == [("Santoso", "2021"), ("Putri", "2020")]


@pytest.mark.parametrize("teks", [
    "Terjadi pada tahun itu (2021).",
    "Lihat persamaan (1) di atas.",
    "Naik cukup tinggi (25%).",
    "Pada Tahun (2021) terjadi kenaikan.",
    "Seperti pada Tabel 4.1 (2021).",
])
def test_bukan_kutipan(teks):
    assert sitasi.cari_kutipan(teks) == []


@pytest.mark.parametrize("entri, kunci", [
    ("Santoso, B., & Putri, A. (2021). Judul artikel. *Jurnal*, 1(2), 3–4.", ("Santoso", "2021")),
    ("Bank Indonesia. (2023). *Laporan perekonomian*. Bank Indonesia.", ("Bank Indonesia", "2023")),
    ("Badan Pusat Statistik (BPS). (2023). *Statistik Indonesia*.", ("Badan Pusat Statistik", "2023")),
    ("Suharto. (2019). *Judul buku*. Penerbit.", ("Suharto", "2019")),
    ("Müller, K. (2020a). Judul.", ("Müller", "2020a")),
    ("Santoso, B. (n.d.). Judul.", ("Santoso", "n.d.")),
])
def test_kunci_pustaka(entri, kunci):
    assert sitasi.kunci_pustaka(entri) == kunci


def _data(isi, pustaka):
    return {"bab": [{"judul": "Pendahuluan", "subbab": [{"judul": "Latar Belakang", "isi": ""}]},
                    {"judul": "Tinjauan Pustaka", "subbab": [{"judul": "Landasan Teori", "isi": isi}]}],
            "daftar_pustaka": pustaka}


def test_periksa_cocok_tanpa_dan_tidak_dikutip():
    isi = ("Menurut Santoso dan Putri (2021), literasi itu penting (Müller, 2020). "
           "Pendapat lain (Nugroho, 2019) berbeda. Data dari BPS (2023) mendukung.")
    pustaka = ("Santoso, B., & Putri, A. (2021). Judul.\n"
               "Muller, K. (2020). Judul.\n"
               "Badan Pusat Statistik. (2023). *Statistik Indonesia*.\n"
               "Wijaya, C. (2018). Judul yang tidak dikutip.")
    hasil = sitasi.periksa(_data(isi, pustaka))
    assert [k["kutipan"] for k in hasil["tanpa_pustaka"]] == ["(Nugroho, 2019)"]
    assert hasil["tanpa_pustaka"][0]["lokasi"] == "Bab II, subbab 2.1"
    assert [t["entri"] for t in hasil["tidak_dikutip"]] == ["Wijaya (2018)"]
    assert (hasil["cocok"], hasil["jumlah"]) == (3, 4)


def test_sumber_gambar_dan_tabel_ikut_diperiksa():
    isi = ("[[TABEL: Jumlah Investor | KSEI, 2025]]\nTahun | Jumlah\n2024 | Santoso (2021)\n[[/TABEL]]\n"
           "[[GAMBAR: grafik.png | Sebaran Responden | Data primer diolah, 2026 | 11]]\n"
           "[[GAMBAR: peta.png | Peta Lokasi | Bank Indonesia (2023)]]")
    hasil = sitasi.periksa(_data(isi, "Kustodian Sentral Efek Indonesia. (2025). *Statistik pasar modal*."))
    assert [k["kutipan"] for k in hasil["tanpa_pustaka"]] == ["Bank Indonesia (2023)"]   # isi sel tabel tidak dihitung
    assert hasil["tidak_dikutip"] == []   # KSEI cocok lewat huruf awal nama lembaga


def test_isi_kosong_tidak_melapor():
    hasil = sitasi.periksa(_data("", "Santoso, B. (2021). Judul."))
    assert not hasil["ada_isi"] and hasil["tidak_dikutip"] == [] and hasil["tanpa_pustaka"] == []


def test_data_contoh_tanpa_laporan_palsu(data_contoh):
    hasil = sitasi.periksa(data_contoh)
    assert hasil["tanpa_pustaka"] == [] and hasil["tidak_dikutip"] == []
    assert hasil["jumlah"] >= 4


def test_kalimat_cek_meringkas_bila_banyak():
    hasil = {"tanpa_pustaka": [], "tidak_dikutip": [{"entri": f"Penulis{i} (2020)", "baris": ""} for i in range(8)]}
    assert sitasi.kalimat_cek(hasil) == ["8 entri daftar pustaka tidak pernah dikutip di isi bab. "
                                        "Rinciannya ada di tab Pustaka & lampiran."]


def test_tampil_di_aplikasi(aplikasi):
    from conftest import ke_tahap, tombol
    at = ke_tahap(tombol(aplikasi, "Isi dengan data contoh").click().run(), "bahan")
    assert not at.exception
    assert any("Cek sitasi: 4 kutipan cocok, 0 tanpa pustaka, 0 entri tidak dikutip." in c.value for c in at.caption)

    at.session_state["bab0_s0_isi"] += "\nPendapat lain berbeda (Nugroho, 2019)."
    at.run()
    assert not at.exception
    assert any("1 tanpa pustaka" in e.label for e in at.expander)
