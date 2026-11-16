import io

import pytest

import ekspor_pdf as epdf
from generator import buat_dokumen

perlu_libreoffice = pytest.mark.skipif(not epdf.tersedia(), reason="LibreOffice tidak terpasang")


def test_tanpa_libreoffice_pesannya_jelas(monkeypatch):
    monkeypatch.setattr(epdf, "cari_soffice", lambda: None)
    with pytest.raises(epdf.GagalPdf, match="LibreOffice tidak ditemukan"):
        epdf.ke_pdf(b"apa saja")


def test_tombol_tidak_muncul_tanpa_libreoffice(aplikasi, monkeypatch):
    from conftest import ke_tahap, tombol
    monkeypatch.setattr(epdf, "tersedia", lambda: False)
    at = tombol(aplikasi, "Isi dengan data contoh").click().run()
    at = tombol(ke_tahap(at, "buat"), "Buat file Word").click().run()
    assert not at.exception
    assert not any(b.label == "Buat PDF pratinjau" for b in at.button)


@perlu_libreoffice
def test_pdf_dari_data_contoh(data_contoh, gambar_contoh):
    from pypdf import PdfReader
    hasil, _ = buat_dokumen(data_contoh, gambar_contoh, None)
    pdf = epdf.ke_pdf(hasil if isinstance(hasil, bytes) else hasil.getvalue(), batas_detik=180)
    assert pdf[:4] == b"%PDF"
    halaman = [h.extract_text() or "" for h in PdfReader(io.BytesIO(pdf)).pages]
    assert 12 <= len(halaman) <= 40
    daftar_isi = next(h for h in halaman if "DAFTAR ISI" in h)
    assert "PENDAHULUAN" in daftar_isi and "TINJAUAN PUSTAKA" in daftar_isi     # terisi, bukan teks penanda field
    assert "Update Field" not in daftar_isi


@perlu_libreoffice
def test_tidak_ada_file_tertinggal(data_contoh, tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    hasil, _ = buat_dokumen(data_contoh, {}, None)
    epdf.ke_pdf(hasil if isinstance(hasil, bytes) else hasil.getvalue(), batas_detik=180)
    assert list(tmp_path.iterdir()) == []
