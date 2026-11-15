from pathlib import Path

import pytest

import impor_pustaka as ip
import pustaka

DATA = Path(__file__).parent / "data"


@pytest.fixture
def bib():
    return ip.baca_berkas("contoh.bib", (DATA / "contoh.bib").read_bytes())


@pytest.fixture
def ris():
    return ip.baca_berkas("contoh.ris", (DATA / "contoh.ris").read_bytes())


def test_bib_artikel_dengan_aksen_dan_latex(bib):
    daftar, _ = bib
    a = daftar[0]
    assert a["jenis"] == "Artikel jurnal"
    assert a["penulis"].splitlines() == ["García, María", "Müller, Jürgen", "van der Berg, Anna"]
    assert a["judul"] == "Financial Literacy & Saving Behaviour"
    assert (a["wadah"], a["tahun"], a["volume"], a["nomor"], a["halaman"]) == ("Jurnal Uji Keuangan", "2020", "12", "3", "101-118")
    assert a["tautan"] == "https://doi.org/10.1234/juk.2020.12.3.101"
    assert pustaka.format_apa(a) == ("García, M., Müller, J., & van der Berg, A. (2020). Financial Literacy & Saving "
                                     "Behaviour. *Jurnal Uji Keuangan, 12*(3), 101–118. "
                                     "https://doi.org/10.1234/juk.2020.12.3.101")


def test_bib_buku_dan_laporan_lembaga(bib):
    daftar, _ = bib
    buku, laporan = daftar[1], daftar[2]
    assert (buku["jenis"], buku["wadah"], buku["tahun"]) == ("Buku", "Penerbit Uji", "2019")
    assert laporan["jenis"] == "Halaman web atau laporan"
    assert laporan["penulis"] == "Bank Indonesia" and laporan["lembaga"] is True
    assert pustaka.format_apa(laporan).startswith("Bank Indonesia. (2023). *Laporan Perekonomian Indonesia 2023*.")


def test_bib_lebih_dari_20_penulis(bib):
    daftar, _ = bib
    banyak = daftar[3]
    assert len(banyak["penulis"].splitlines()) == 22
    assert ". . . A22, P." in pustaka.format_apa(banyak)


def test_bib_entri_rusak_dilewati(bib):
    daftar, peringatan = bib
    assert len(daftar) == 4
    assert any("tanpajudul" in p and "tidak ada judul" in p for p in peringatan)
    assert any("tidak ditutup" in p for p in peringatan)


def test_ris(ris):
    daftar, peringatan = ris
    assert [d["jenis"] for d in daftar] == ["Artikel jurnal", "Buku", "Halaman web atau laporan"]
    a = daftar[0]
    assert a["penulis"].splitlines() == ["García, María", "Müller, Jürgen"]
    assert (a["tahun"], a["halaman"], a["tautan"]) == ("2020", "101-118", "https://doi.org/10.1234/juk.2020.12.3.101")
    assert daftar[2]["lembaga"] is True and daftar[2]["tautan"] == "https://contoh.test/laporan-2023"
    assert peringatan == ["Entri ke-4 dilewati: tidak ada judul."]


def test_bib_dan_ris_menghasilkan_entri_yang_sama(bib, ris):
    assert pustaka.format_apa(bib[0][1]) == pustaka.format_apa(ris[0][1])


def test_utf8_dengan_bom():
    daftar, _ = ip.baca_berkas("a.ris", "﻿TY  - BOOK\nTI  - Judul\nER  - \n".encode("utf-8"))
    assert daftar[0]["judul"] == "Judul"


def test_penulis_depan_belakang_dibalik():
    daftar, _ = ip.baca_bib("@book{x, author = {Annamaria Lusardi and Olivia S. Mitchell}, title = {T}, year = {2014}}")
    assert daftar[0]["penulis"].splitlines() == ["Lusardi, Annamaria", "Mitchell, Olivia S."]


def test_ekstensi_tidak_dikenal():
    with pytest.raises(ip.GagalImpor):
        ip.baca_berkas("daftar.txt", b"apa saja")


def test_file_kosong():
    with pytest.raises(ip.GagalImpor):
        ip.baca_berkas("kosong.bib", b"")


def test_impor_lewat_aplikasi(aplikasi):
    """Uploader tidak bisa diisi lewat AppTest, jadi hasil baca ditaruh langsung di session_state."""
    from conftest import tombol
    at = aplikasi
    daftar, peringatan = ip.baca_berkas("contoh.bib", (DATA / "contoh.bib").read_bytes())
    at.session_state["_impor_ref"], at.session_state["_impor_peringatan"] = daftar, peringatan
    at.session_state["_impor_nonce"] = 1
    at.session_state["daftar_pustaka"] = pustaka.format_apa(daftar[1])   # buku sudah ada lebih dulu
    at.run()
    assert not at.exception
    kotak = [c for c in at.checkbox if c.key and c.key.startswith("impor1_")]
    assert len(kotak) == 4 and kotak[1].disabled and not kotak[1].value

    kotak[3].uncheck()
    tombol(at, "Tambahkan yang dicentang").click().run()
    assert not at.exception
    baris = at.session_state["daftar_pustaka"].splitlines()
    assert len(baris) == 3 and len(set(baris)) == 3
    assert at.session_state["_impor_ref"] is None
