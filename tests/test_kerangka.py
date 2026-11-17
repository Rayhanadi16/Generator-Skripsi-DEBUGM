import io

import pytest

import rujukan
import susun_isi as si
from generator import judul_kapital
from conftest import ke_tahap, tombol


def isian():
    return {"bab0_n": 3,
            "bab0_s0_judul": "A", "bab0_s0_isi": "Isi A\n[[GAMBAR: a.png | Gambar A]]",
            "bab0_s1_judul": "B", "bab0_s1_isi": "Isi B\n[[GAMBAR: b.png | Gambar B]]\nLihat [[REF: #a]].",
            "bab0_s2_judul": "C", "bab0_s2_isi": "Isi C"}


def susunan(d, i=0):
    return [(d[f"bab{i}_s{j}_judul"], d[f"bab{i}_s{j}_isi"].splitlines()[0] if d[f"bab{i}_s{j}_isi"] else "")
            for j in range(d[f"bab{i}_n"])]


def test_tukar_subbab_memindah_judul_dan_isi():
    d = isian()
    assert si.tukar_subbab(d, 0, 0, 1)
    assert susunan(d) == [("B", "Isi B"), ("A", "Isi A"), ("C", "Isi C")] and d["bab0_n"] == 3
    assert not si.tukar_subbab(d, 0, 2, 3) and not si.tukar_subbab(d, 0, 0, -1)
    assert susunan(d) == [("B", "Isi B"), ("A", "Isi A"), ("C", "Isi C")]


def test_sisip_subbab_di_tengah_dan_akhir():
    d = isian()
    assert si.sisip_subbab(d, 0, 1) == 1
    assert susunan(d) == [("A", "Isi A"), ("", ""), ("B", "Isi B"), ("C", "Isi C")] and d["bab0_n"] == 4
    assert si.sisip_subbab(d, 0, 99) == 4 and d["bab0_n"] == 5 and d["bab0_s4_judul"] == ""


def test_hapus_subbab_menggeser_yang_di_bawahnya():
    d = isian()
    assert si.hapus_subbab(d, 0, 0)
    assert susunan(d) == [("B", "Isi B"), ("C", "Isi C")] and d["bab0_n"] == 2
    assert not si.hapus_subbab(d, 0, 5) and d["bab0_n"] == 2


def test_rujukan_tetap_benar_setelah_subbab_ditukar():
    d = isian()
    data = lambda: {"bab": [{"judul": "Bab", "subbab": [{"judul": d[f"bab0_s{j}_judul"], "isi": d[f"bab0_s{j}_isi"]}
                                                          for j in range(d["bab0_n"])]}]}
    assert rujukan.peta_label(data())[0] == {"a": "Gambar 1.1", "b": "Gambar 1.2"}
    si.tukar_subbab(d, 0, 0, 1)
    peta, _ = rujukan.peta_label(data())
    assert peta == {"b": "Gambar 1.1", "a": "Gambar 1.2"}
    assert "Lihat Gambar 1.2." in rujukan.siapkan(d["bab0_s0_isi"], peta)


def test_pindah_bagian_membawa_paragrafnya():
    teks = "Pembuka\n### A\nIsi A1\nIsi A2\n\n### B\nIsi B\n### C"
    turun = si.pindah_bagian(teks, 1, 1)
    assert [b for b in turun.splitlines() if b] == ["Pembuka", "### B", "Isi B", "### A", "Isi A1", "Isi A2", "### C"]
    assert si.pindah_bagian(turun, 3, -1) == teks
    assert si.pindah_bagian(teks, 1, -1) == teks and si.pindah_bagian(teks, 6, 1) == teks
    assert si.pindah_bagian(teks, 0, 1) == teks          # paragraf bukan sub-subbab
    assert si.bisa_pindah_bagian(teks, 4, 1) and not si.bisa_pindah_bagian(teks, 6, 1)


def test_ringkasan_isi():
    teks = "Satu\n1. butir\n[[GAMBAR: a.png | A]]\n[[TABEL: T]]\na | b\n[[/TABEL]]"
    assert si.ringkasan_isi(teks) == {"paragraf": 2, "gambar": 1, "tabel": 1}


@pytest.mark.parametrize("masuk, keluar", [
    ("pengaruh ROA terhadap harga saham", "Pengaruh ROA terhadap Harga Saham"),
    ("data BPS dan UMKM di yogyakarta", "Data BPS dan UMKM di Yogyakarta"),
    ("dari desa ke kota yang pada untuk dengan", "Dari Desa ke Kota yang pada untuk dengan"),
    ("penjualan e-Commerce dan iPhone", "Penjualan e-Commerce dan iPhone"),
    ("(studi kasus pada UMKM)", "(Studi Kasus pada UMKM)"),
    ("latar belakang", "Latar Belakang"),
    ("Dan Lain-Lain", "Dan Lain-Lain"),
])
def test_judul_kapital(masuk, keluar):
    assert judul_kapital(masuk) == keluar


def judul_di_word(at, gaya):
    from docx import Document
    hasil = at.session_state["_hasil"]
    isi = hasil if isinstance(hasil, bytes) else hasil.getvalue()
    return [p.text for p in Document(io.BytesIO(isi)).paragraphs if p.style.name == gaya]


def test_kerangka_ubah_nama_pindah_dan_hapus(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    judul_awal = [at.session_state[f"bab1_s{j}_judul"] for j in range(at.session_state["bab1_n"])]
    isi_awal = at.session_state["bab1_s0_isi"]

    at = at.button(key="kr_ubah_1_0").click().run()
    n = at.session_state["_pn"]
    at.text_input(key=f"pn_judul{n}").set_value("pengaruh ROA terhadap harga saham")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert not at.exception
    assert at.session_state["bab1_s0_judul"] == "pengaruh ROA terhadap harga saham"

    at = at.button(key="kr_turun_1_0").click().run()
    assert at.session_state["bab1_s1_judul"] == "pengaruh ROA terhadap harga saham"
    assert at.session_state["bab1_s1_isi"] == isi_awal and at.session_state["bab1_s0_judul"] == judul_awal[1]

    at = at.button(key="kr_tambah_1_0").click().run()          # subbab baru di antara 2.1 dan 2.2
    assert at.session_state["bab1_n"] == len(judul_awal) + 1 and at.session_state["bab1_s1_judul"] == ""
    n = at.session_state["_pn"]
    at.text_input(key=f"pn_judul{n}").set_value("Sisipan")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert at.session_state["bab1_s1_judul"] == "Sisipan"
    assert at.session_state["bab1_s2_judul"] == "pengaruh ROA terhadap harga saham"

    at = tombol(ke_tahap(at, "buat"), "Buat file Word").click().run()
    assert not at.exception
    bab2 = [t for t in judul_di_word(at, "Heading 2") if t.startswith("2.")]
    assert bab2[:3] == [f"2.1 {judul_kapital(judul_awal[1])}", "2.2 Sisipan", "2.3 Pengaruh ROA terhadap Harga Saham"]

    at = ke_tahap(at, "isi")
    at = at.button(key="kr_hapus_1_1").click().run()
    assert at.session_state["bab1_n"] == len(judul_awal) + 1    # klik pertama baru konfirmasi
    at = at.button(key="kr_hapus_1_1").click().run()
    assert at.session_state["bab1_n"] == len(judul_awal)
    assert at.session_state["bab1_s1_judul"] == "pengaruh ROA terhadap harga saham"


def test_kerangka_subsubbab(aplikasi):
    at = aplikasi
    at.session_state["bab1_s0_isi"] = "### A\nIsi A\n### B\nIsi B"
    at = at.run()
    at = at.button(key="kr_ssturun_1_0_0").click().run()
    assert at.session_state["bab1_s0_isi"].splitlines() == ["### B", "Isi B", "### A", "Isi A"]
    at = at.button(key="kr_ssubah_1_0_2").click().run()
    n = at.session_state["_pn"]
    at.text_input(key=f"pn_judul{n}").set_value("A Baru")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert at.session_state["bab1_s0_isi"].splitlines()[2] == "### A Baru"
    at = at.button(key="kr_baruss_1_0").click().run()
    n = at.session_state["_pn"]
    at.text_input(key=f"pn_judul{n}").set_value("C")
    at = at.run()
    at = at.button(key=f"pn_simpan{n}").click().run()
    assert at.session_state["bab1_s0_isi"].splitlines()[-1] == "### C"
    at = at.button(key="kr_sshapus_1_0_0").click().run()
    at = at.button(key="kr_sshapus_1_0_0").click().run()
    assert at.session_state["bab1_s0_isi"].splitlines() == ["Isi B", "### A Baru", "Isi A", "### C"]
    assert not at.exception


def test_isian_bertahan_setelah_kerangka_dan_pindah_tahap(aplikasi):
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    at = at.button(key="kr_turun_3_0").click().run()
    isi = at.session_state["bab3_s1_isi"]
    assert "[[GAMBAR" in isi
    at = ke_tahap(ke_tahap(at, "periksa"), "isi")
    assert at.session_state["bab3_s1_isi"] == isi and not at.exception


def test_preview_menunjuk_ke_panel_kerangka(data_contoh, gambar_contoh):
    from preview import halaman_html
    html = halaman_html(data_contoh, gambar_contoh)
    assert html.count("Ubah nama atau urutan judul di tab Bab, panel Kerangka laporan.") == 1
