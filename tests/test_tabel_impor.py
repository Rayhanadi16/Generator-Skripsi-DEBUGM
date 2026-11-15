from datetime import date
from pathlib import Path

import pytest

import tabel_impor as t

DATA = Path(__file__).parent / "data"


@pytest.fixture
def xlsx():
    return t.baca_xlsx((DATA / "contoh.xlsx").read_bytes())


def test_xlsx_nilai_rumus_dan_sel_gabungan(xlsx):
    baris = t.rapikan(xlsx["Deskriptif"])
    assert baris[0] == ["Statistik Deskriptif"] * 4            # sel gabungan diisi nilai kiri atasnya
    assert baris[2] == ["Literasi keuangan", 120, 3.456, 414.72]   # 414.72 hasil rumus, bukan "=C4*D4"


def test_xlsx_format_angka_seragam_per_kolom(xlsx):
    teks = t.format_tabel(xlsx["Deskriptif"][2:])
    assert teks == [["Variabel", "N", "Rata-rata", "Total"],
                    ["Literasi keuangan", "120", "3,456", "414,72"],
                    ["Keputusan investasi", "120", "3,200", "384,00"],
                    ["Pendapatan", "1.250.000", "0,500", "625.000,00"]]


def test_xlsx_tanggal_dan_karakter_pemisah(xlsx):
    penanda = t.ke_penanda(xlsx["Jadwal"], "Jadwal | Penelitian", "Data primer")
    assert penanda.splitlines() == ["[[TABEL: Jadwal / Penelitian | Data primer]]",
                                    "Kegiatan | Tanggal | Catatan",
                                    "Pengambilan data | 12 Januari 2026 | Daring / luring",
                                    "[[/TABEL]]"]


def test_csv_koma():
    baris = t.baca_csv((DATA / "koma.csv").read_bytes())
    assert baris[1] == [2022, 1250000, 3.5, "007"]             # NIM berawalan nol tetap teks
    assert t.format_tabel(baris) == [["Tahun", "Jumlah", "Rasio", "NIM"],
                                     ["2022", "1.250.000", "3,50", "007"],     # tahun tanpa pemisah ribuan
                                     ["2023", "1.500.000", "4,25", "008"]]


def test_csv_titik_koma_dengan_bom():
    baris = t.baca_csv((DATA / "titik_koma.csv").read_bytes())
    assert baris == [["Nama", "Nilai", "Keterangan"], ["Santoso, B.", 3.75, "Lulus"], ["Putri", 4, "Lulus"]]


def test_csv_cp1252():
    assert t.baca_csv("Nama;Kota\nJosé;Málaga\n".encode("cp1252"))[1] == ["José", "Málaga"]


@pytest.mark.parametrize("nilai, kw, hasil", [
    (1250000, {}, "1.250.000"),
    (1250000, {"koma_desimal": False}, "1,250,000"),
    (-1500, {}, "-1.500"),
    (3.14159, {}, "3,1416"),
    (0.5, {"desimal": 2}, "0,50"),
    (2.0, {}, "2"),
    (date(2026, 1, 12), {}, "12 Januari 2026"),
    (None, {}, ""),
    ("  teks  ", {}, "teks"),
])
def test_format_angka(nilai, kw, hasil):
    assert t.format_angka(nilai, **kw) == hasil


def test_rapikan_membuang_tepi_kosong():
    assert t.rapikan([[None, None], [None, "a"], ["", "b", None], [None]]) == [["a"], ["b"]]
    assert t.rapikan([[None], [""]]) == []


def test_penanda_tanpa_sumber_dan_rentang_kosong():
    assert t.ke_penanda([["A", "B"], [1, 2]], "Judul").splitlines()[0] == "[[TABEL: Judul]]"
    with pytest.raises(t.GagalTabel):
        t.ke_penanda([[None]], "Judul")


def test_peringatan_ukuran():
    assert t.peringatan_ukuran([["x"] * 5] * 5) == []
    assert len(t.peringatan_ukuran([["x"] * 9] * 41)) == 2


def test_penanda_terbaca_oleh_preview_dan_generator(xlsx, data_contoh):
    """Tabel impor harus diperlakukan sama dengan tabel yang diketik tangan."""
    from generator import buat_dokumen
    from preview import kerangka
    data_contoh["bab"][3]["subbab"][0]["isi"] += "\n" + t.ke_penanda(xlsx["Deskriptif"][2:], "Statistik Deskriptif")
    struktur, cek = kerangka(data_contoh, {})
    tabel = [x for s in struktur[3]["subbab"] for x in s["tabel"]]
    assert any(x.startswith("Tabel 4.") and "Statistik Deskriptif" in x for x in tabel)
    assert not any("belum ditutup" in c for c in cek)
    hasil, _ = buat_dokumen(data_contoh, {}, None)
    assert (hasil if isinstance(hasil, bytes) else hasil.getvalue())[:2] == b"PK"


def test_sisipkan_lewat_aplikasi(aplikasi, xlsx):
    """Uploader tidak bisa diisi lewat AppTest, jadi hasil baca ditaruh langsung di session_state."""
    from conftest import tombol
    at = aplikasi
    at.session_state["_tabel_lembar"] = xlsx
    at.session_state["_tabel_nonce"] = 1
    at.run()
    assert not at.exception
    assert tombol(at, "Sisipkan ke subbab").disabled          # judul belum diisi

    next(n for n in at.number_input if n.label.startswith("Baris awal")).set_value(2)
    next(x for x in at.text_input if x.label == "Judul tabel").set_value("Statistik Deskriptif")
    next(s for s in at.selectbox if s.label == "Sisipkan ke subbab").select("4.1 Deskripsi Data")
    at.run()
    assert not at.exception
    tombol(at, "Sisipkan ke subbab").click().run()
    assert not at.exception
    isi = at.session_state["bab3_s0_isi"].splitlines()
    assert isi[-6:] == ["[[TABEL: Statistik Deskriptif]]",
                        "Variabel | N | Rata-rata | Total",
                        "Literasi keuangan | 120 | 3,456 | 414,72",
                        "Keputusan investasi | 120 | 3,200 | 384,00",
                        "Pendapatan | 1.250.000 | 0,500 | 625.000,00",
                        "[[/TABEL]]"]
