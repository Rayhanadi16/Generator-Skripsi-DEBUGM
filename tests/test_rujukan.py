from pathlib import Path

import pytest

import rujukan
from bantu_dokumen import teks_dokumen
from generator import buat_dokumen
from preview import halaman_html, kerangka

DATA = Path(__file__).parent / "data"


def _data(*isi_per_bab):
    return {"identitas": {}, "bab": [{"judul": f"Bab {i}", "subbab": [{"judul": "Sub", "isi": isi}]}
                                      for i, isi in enumerate(isi_per_bab, start=1)]}


def _teks(data, gambar=None):
    hasil, peringatan = buat_dokumen(data, gambar or {}, None)
    return teks_dokumen(hasil if isinstance(hasil, bytes) else hasil.getvalue()), peringatan


TABEL = "[[TABEL: Statistik Deskriptif | Data primer | #statistik]]\nA | B\n1 | 2\n[[/TABEL]]"


def test_peta_label_semua_jenis():
    data = _data("[[RUMUS: Y = a + bX | #regresi]]\n[[GAMBAR: grafik_penjualan.png | Penjualan | BPS, 2023]]",
                 "[[TABEL: Lain]]\nA\n[[/TABEL]]\n" + TABEL + "\n[[RUMUS: Z = |x| + 1 | #mutlak]]\n"
                 "[[GAMBAR: peta.png | Peta | | 10 | #lokasi]]")
    peta, ganda = rujukan.peta_label(data)
    assert peta == {"regresi": "Persamaan (1)", "grafik_penjualan": "Gambar 1.1", "statistik": "Tabel 2.2",
                    "mutlak": "Persamaan (2)", "lokasi": "Gambar 2.1", "peta": "Gambar 2.1"}
    assert ganda == []


def test_rujukan_ke_depan_dan_antarbab():
    data = _data("Hasil uji ada pada [[REF: #statistik]] dan [[REF:statistik]].", "Pengantar.\n" + TABEL)
    teks, peringatan = _teks(data)
    assert "Hasil uji ada pada Tabel 2.1 dan Tabel 2.1." in teks
    assert "Tabel 2.1. Statistik Deskriptif" in teks
    assert "#statistik" not in teks and "Sumber: Data primer" in teks      # label tidak ikut tercetak
    assert not any("ujukan" in p for p in peringatan)


def test_nomor_ikut_berubah_bila_urutan_berubah():
    sebelum = _data("Lihat [[REF: #statistik]].\n" + TABEL)
    sesudah = _data("Lihat [[REF: #statistik]].\n[[TABEL: Tabel Baru]]\nA\n[[/TABEL]]\n" + TABEL)
    assert "Lihat Tabel 1.1." in _teks(sebelum)[0]
    assert "Lihat Tabel 1.2." in _teks(sesudah)[0]


def test_label_tidak_dikenal():
    data = _data("Lihat [[REF: #salah_ketik]].")
    teks, peringatan = _teks(data)
    assert "Lihat [rujukan #salah_ketik tidak ditemukan]." in teks
    assert peringatan.count("Rujukan #salah_ketik di subbab 1.1 tidak ditemukan. Periksa labelnya.") == 1
    _, cek = kerangka(data, {})
    assert "Rujukan #salah_ketik di subbab 1.1 tidak ditemukan. Periksa labelnya." in cek
    assert '<span class="ph">[rujukan #salah_ketik tidak ditemukan]</span>' in halaman_html(data)


def test_label_ganda():
    data = _data(TABEL + "\n" + TABEL + "\nLihat [[REF: #statistik]].")
    teks, peringatan = _teks(data)
    assert "Lihat Tabel 1.1." in teks
    pesan = "Label #statistik dipakai lebih dari sekali. Rujukan memakai yang pertama."
    assert pesan in peringatan and pesan in kerangka(data, {})[1]


def test_rumus_dengan_garis_tegak_tidak_rusak():
    teks, _ = _teks(_data("[[RUMUS: Z = |x| + 1 | #mutlak]]\nLihat [[REF: #mutlak]]."))
    assert "\tZ = |x| + 1\t(1)" in teks and "Lihat Persamaan (1)." in teks


def test_preview_dan_word_memakai_nomor_yang_sama():
    data = _data("[[GAMBAR: a.png | Satu]]", "[[GAMBAR: b.png | Dua | | #dua]]\nSeperti [[REF: #dua]] dan [[REF: #a]].")
    assert "Seperti Gambar 2.1 dan Gambar 1.1." in _teks(data)[0]
    assert "Seperti Gambar 2.1 dan Gambar 1.1." in halaman_html(data)
    assert "Gambar 2.1. Dua" in kerangka(data, {})[0][1]["subbab"][0]["gambar"][0]


def test_isi_tanpa_fitur_ini_tidak_disentuh():
    isi = "Paragraf biasa.\n[[TABEL: Judul | Sumber]]\nA | B\n[[/TABEL]]\n[[RUMUS: Y = a + bX]]"
    assert rujukan.siapkan(isi, {}) is isi


def test_dokumen_lama_tetap_sama(data_contoh, gambar_contoh):
    """Data contoh (tanpa label dan tanpa REF) harus menghasilkan teks yang sama dengan sebelum fitur ini."""
    teks, _ = _teks(data_contoh, gambar_contoh)
    assert teks == (DATA / "dokumen_contoh_sebelum_rujukan.txt").read_text(encoding="utf-8")
